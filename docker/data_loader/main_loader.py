# main.py
"""
🎛️ Main Orchestrator: тонкий слой координации.
Отвечает за: инициализацию компонентов, цикл загрузки, graceful shutdown.
ВСЯ бизнес-логика вынесена в компоненты и БД.
"""

import os
import sys
import asyncio
import signal
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from zoneinfo import ZoneInfo

from logger import setup_logger
from constants import (
    Timeframe, StrategyName, SignalType,
    DEFAULT_LOG_LEVEL, DEFAULT_TIMEZONE,
    TIMEFRAMES
)
from db_manager import DBManager
from T_con import TConnector
from strategy.strategy_runner import StrategyRunner

# Импорт стратегий (вынеси в отдельный модуль при росте)
#from strategy import run_strategy, get_price_type


class Orchestrator:
    """Главный оркестратор приложения."""

    def __init__(
            self,

            # 📡 Tinkoff
            tinkoff_token: str,

            # 🗄️ БД
            db_host: str,
            db_name: str,
            db_user: str,
            db_password: str,
            db_port: int = 5432,
            db_schema: str = "public",

            # 🪵 Логирование
            log_level: str = DEFAULT_LOG_LEVEL,
            log_file: str = "orchestrator.log",
            timezone_name: str = DEFAULT_TIMEZONE,

            # 📦 Telegram (опционально)
            telegram_token: str = None,
            telegram_chat_id: str = None,
            notify_on_signals: set = None,
    ):
        # 🔐 Валидация обязательных параметров
        if not tinkoff_token or tinkoff_token in ("YOUR_TOKEN_HERE", "xxx"):
            raise ValueError("❌ Tinkoff token не указан!")

        self.logger = setup_logger("Orchestrator", log_file, log_level)
        self.tz = ZoneInfo(timezone_name)
        self.running = True
        self.notify_on = notify_on_signals or {SignalType.BUY, SignalType.SELL}

        self.logger.info("🚀 Orchestrator инициализирован")
        self.logger.info(f"🌍 Timezone: {timezone_name}, PID: {os.getpid()}")

        # 🔗 Инициализация компонентов
        self.db = DBManager(
            db_host=db_host, db_name=db_name, db_user=db_user,
            db_password=db_password, db_port=db_port, db_schema=db_schema,
            log_level=log_level, timezone_name=timezone_name
        )

        self.broker = TConnector(
            token=tinkoff_token,
            log_level=log_level,
            log_file=log_file.replace("orchestrator", "tinkoff")
        )

        # 📡 Telegram notifier (опционально)
        self.tg = None
        if telegram_token and telegram_chat_id:
            try:
                from telegram_notifier import TelegramNotifier
                self.tg = TelegramNotifier(
                    token=telegram_token,
                    chat_id=telegram_chat_id,
                    timeout=10
                )
                self.logger.info("✅ TelegramNotifier подключен")
            except ImportError:
                self.logger.warning("⚠️ TelegramNotifier не установлен, уведомления отключены")

        # 🗄️ Инициализация таблиц
        self.db.init_instrument_config_table()
        self.db.init_metrics_table()

        # 🚀 Запуск Admin UI в фоне (если включено)
        self._start_admin_ui_thread(host="0.0.0.0", port=8000)

        # 📡 Сигналы завершения
        self._setup_signals()

        # 🔥 Синхронизация инструментов (теперь вызывается из async main())

    def _setup_signals(self):
        """Настройка обработчиков SIGINT/SIGTERM."""

        def handler(signum, frame):
            self.logger.info(f"📡 Сигнал {signum}: запуск graceful shutdown...")
            self.running = False
            # Запускаем close() в отдельном потоке, чтобы не блокировать сигнал
            import threading
            import asyncio
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass  # Нет активного цикла

            if loop and loop.is_running():
                # Если цикл запущен, создаём новый цикл в потоке
                t = threading.Thread(target=self._run_close_in_thread, daemon=True)
            else:
                t = threading.Thread(target=self.close_sync, daemon=True)
            t.start()

        signal.signal(signal.SIGINT, handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, handler)  # docker stop / kill

    def _run_close_in_thread(self):
        """Запускает async close() в новом цикле внутри потока."""
        import asyncio
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            new_loop.run_until_complete(self.close())
        finally:
            new_loop.close()

    def close_sync(self):
        """Синхронная обёртка для close() для использования в сигналах."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                loop.run_until_complete(self.close())
                return
        except Exception:
            pass
        # Если цикл запущен (main thread), используем новый цикл
        new_loop = asyncio.new_event_loop()
        new_loop.run_until_complete(self.close())
        new_loop.close()

    async def _load_single_instrument(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Загрузка одного инструмента + запуск стратегии (новая архитектура)."""
        ticker = config['ticker']
        timeframe = config['timeframe']
        strategy_name = config.get('strategy_name', 'none')

        # 🔥 Читаем флаги и параметры
        strategy_params = config.get('strategy_params', {}) or {}
        direction = strategy_params.get('direction', 'ALL')  # Из JSON
        live_enabled = config.get('live_trading_enabled', False)

        result = {
            "ticker": ticker, "timeframe": timeframe, "strategy": strategy_name,
            "load_ok": False, "strategy_ok": False, "signal": None,
            "execution_mode": "watchdog", "orders_executed": 0
        }

        try:
            # 🕯️ 1. Загрузка цен (без изменений)
            from price_loader import PriceLoader
            loader = PriceLoader(ticker=ticker, timeframe=timeframe, broker=self.broker, db=self.db, logger=self.logger)
            load_result = await loader.load_incremental(history_depth_days=config.get('history_depth_days'))
            result["load_ok"] = load_result.get("success", False)
            result["candles_saved"] = load_result.get("candles_saved", 0)

            # 📊 1.5. Расчёт метрик (без изменений)
            if result["load_ok"]:
                from metrics.engine import MetricsEngine
                engine = MetricsEngine(db=self.db, metric_names=None)
                candles_for_metrics = self.db.get_recent_candles(ticker, timeframe,
                                                                 limit=engine.recommended_fetch_limit)
                candles_for_metrics = list(reversed(candles_for_metrics))
                if len(candles_for_metrics) >= engine.min_candles_required:
                    engine.calculate_for_candles(ticker, timeframe, candles_for_metrics)

            # 🧠 2. Запуск стратегии (НОВАЯ ЛОГИКА)
            if result["load_ok"] and StrategyName.is_active(strategy_name):
                account_id = None
                if live_enabled:
                    try:
                        account_id = await self.broker.get_account_id()
                    except Exception as e:
                        self.logger.warning(f"⚠️ Не удалось получить account_id: {e}. Фоллбэк в watchdog.")
                        live_enabled = False

                runner = StrategyRunner(
                    ticker=ticker, timeframe=timeframe, strategy_name=strategy_name,
                    db=self.db, broker=self.broker,  # 🔥 Брокер нужен для LiveExecutor
                    live_trading_enabled=live_enabled,
                    telegram_notifier=self.tg, logger=self.logger,
                    account_id=account_id, strategy_class=None
                )
                # 🔥 Передаём strategy_params целиком (direction уже внутри)
                runner.configure(window=config.get('strategy_window'), params=strategy_params)

                strat_result = await runner.run(notify_signals=self.notify_on if self.tg else None)

                result["strategy_ok"] = strat_result.get("success", False)
                result["signal"] = strat_result.get("signal")
                result["execution_mode"] = strat_result.get("execution_mode", "watchdog")
                result["orders_executed"] = strat_result.get("orders_executed", 0)

            return result
        except Exception as e:
            self.logger.error(f"❌ Ошибка {ticker}/{timeframe}: {e}", exc_info=True)
            result["error"] = str(e)
            return result

    async def run_cycle(self) -> List[Dict[str, Any]]:
        """Один цикл обработки всех активных инструментов."""
        # 📋 1. Загружаем ВСЕ инструменты из БД (не только из instrument_config)
        all_instruments = self.db.get_all_instruments()
        if not all_instruments:
            self.logger.warning("⚠️ Нет инструментов в таблице instruments")
            return []

        # 🔥 2. Загружаем дневные свечи (1d) для ВСЕХ инструментов
        self.logger.info(f"📊 Загрузка 1d свечей для {len(all_instruments)} инструментов...")
        for inst in all_instruments:
            if not self.running:
                break
            ticker = inst['ticker']
            try:
                from price_loader import PriceLoader
                loader = PriceLoader(
                    ticker=ticker, timeframe="1d",
                    broker=self.broker, db=self.db, logger=self.logger
                )
                await loader.load_incremental(history_depth_days=365)
                await asyncio.sleep(0.05)  # Пауза чтобы не перегружать API
            except Exception as e:
                self.logger.error(f"❌ Ошибка загрузки 1d для {ticker}: {e}")

        # 📋 3. Получаем конфигурации из БД для остальных таймфреймов и стратегий
        configs = self.db.get_enabled_instrument_configs()
        if not configs:
            self.logger.info("ℹ️ Нет активных инструментов в instrument_config (только 1d)")
            return []

        self.logger.info(f"📋 Обработка {len(configs)} инструментов из instrument_config...")
        results = []

        # Последовательная обработка (для 2GB VPS)
        # Для прода можно добавить asyncio.Semaphore(MAX_CONCURRENT_LOADS)
        for cfg in configs:
            if not self.running:
                break
            result = await self._load_single_instrument(cfg)
            results.append(result)

            # Лёгкая пауза, чтобы не перегружать API
            await asyncio.sleep(0.1)

        # Краткий отчёт
        success_count = sum(1 for r in results if r.get("load_ok"))
        self.logger.info(f"✅ Цикл завершён: {success_count}/{len(results)} успешно")
        return results

    async def run_continuous(self, check_interval_sec: int = 60):
        """Непрерывный режим с двойным триггером: таймер + расписание + защита от дублей."""
        self.logger.info("🔄 Запуск в непрерывном режиме (двойной триггер + anti-spam)")

        last_load_times: Dict[str, datetime] = {}  # Для таймера
        last_schedule_run: Dict[str, Any] = {}  # 🔥 НОВОЕ: для расписания
        last_1d_load_time: Optional[datetime] = None  # Для загрузки 1d свечей

        while self.running:
            try:
                # 📊 1. Загружаем 1d свечи для ВСЕХ инструментов каждые 60 минут
                now = datetime.now(self.tz)
                if last_1d_load_time is None or now >= last_1d_load_time + timedelta(minutes=60):
                    all_instruments = self.db.get_all_instruments()
                    if all_instruments:
                        self.logger.info(f"📊 Загрузка 1d свечей для {len(all_instruments)} инструментов...")
                        for inst in all_instruments:
                            if not self.running:
                                break
                            ticker = inst['ticker']
                            try:
                                from price_loader import PriceLoader
                                loader = PriceLoader(
                                    ticker=ticker, timeframe="1d",
                                    broker=self.broker, db=self.db, logger=self.logger
                                )
                                await loader.load_incremental(history_depth_days=365)
                                await asyncio.sleep(0.05)
                            except Exception as e:
                                self.logger.error(f"❌ Ошибка загрузки 1d для {ticker}: {e}")
                        last_1d_load_time = now

                # 📋 2. Получаем конфигурации из БД для остальных таймфреймов и стратегий
                configs = self.db.get_enabled_instrument_configs()
                
                to_load = []
                for cfg in configs:
                    key = f"{cfg['ticker']}_{cfg['timeframe']}"
                    timeframe = cfg['timeframe']
                    interval = cfg.get('update_interval_minutes', 60)

                    # 🔹 Условие 1: таймер истёк
                    last = last_load_times.get(key)
                    timer_expired = last is None or now >= last + timedelta(minutes=interval)

                    # 🔹 Условие 2: расписание совпадает
                    schedule_match = self._should_run_by_schedule(timeframe, now)

                    # 🔥 НОВОЕ: проверка, не срабатывало ли расписание уже в этом окне
                    schedule_allowed = True
                    if schedule_match:
                        last_sched = last_schedule_run.get(key)
                        tf_config = TIMEFRAMES.get(timeframe, {})

                        # Определяем "ключ окна" расписания: что должно измениться, чтобы разрешить повтор
                        if tf_config.get("schedule_weekday") is not None:
                            # Для недельных: ключ = (год, неделя, час)
                            window_key = (now.isocalendar()[0], now.isocalendar()[1], now.hour)
                        elif tf_config.get("schedule_hour") is not None:
                            # Для дневных: ключ = (год, месяц, день, час)
                            window_key = (now.year, now.month, now.day, now.hour)
                        elif tf_config.get("schedule_minute") is not None:
                            # Для часовых/минутных: ключ = (год, месяц, день, час, минута)
                            window_key = (now.year, now.month, now.day, now.hour, now.minute)
                        else:
                            window_key = None  # Нет расписания → всегда разрешено

                        # Если окно не сменилось → расписание уже отработало, пропускаем
                        if window_key and last_sched == window_key:
                            schedule_allowed = False
                            schedule_match = False  # Сбрасываем, чтобы не путать логику ниже
                        else:
                            # Запоминаем, что отработали это окно
                            last_schedule_run[key] = window_key

                    # ✅ Запускаем если: таймер ИЛИ (расписание и ещё не срабатывало в этом окне)
                    if timer_expired or (schedule_match and schedule_allowed):
                        to_load.append(cfg)

                        # 🔥 Логирование причины
                        if schedule_match and schedule_allowed and not timer_expired:
                            self.logger.info(f"📅 Schedule trigger: {key} @ {now.strftime('%Y-%m-%d %H:%M')}")
                        elif timer_expired:
                            self.logger.debug(f"⏱️ Timer trigger: {key} (last: {last})")

                if to_load:
                    self.logger.info(f"⏰ Запуск обновления {len(to_load)} инструментов")

                    results = await asyncio.gather(
                        *(self._load_single_instrument(cfg) for cfg in to_load),
                        return_exceptions=True
                    )

                    # 🔥 Сбрасываем таймер для всех обработанных
                    for cfg in to_load:
                        key = f"{cfg['ticker']}_{cfg['timeframe']}"
                        last_load_times[key] = now

                    # Отчёт
                    for r in results:
                        if isinstance(r, Exception):
                            self.logger.error(f"❌ Ошибка в задаче: {r}")
                        elif r:
                            status = "✅" if r.get("load_ok") else "❌"
                            self.logger.info(
                                f"   {status} {r['ticker']}/{r['timeframe']}: "
                                f"{r.get('candles_saved', 0)} свечей, сигнал: {r.get('signal', '-')}"
                            )
                else:
                    # Тихий лог раз в 10 минут
                    if int(now.timestamp()) % 600 < check_interval_sec:
                        self.logger.debug(f"⏳ Нет инструментов для обновления @ {now.strftime('%H:%M')}")

                await asyncio.sleep(check_interval_sec)

            except Exception as e:
                self.logger.error(f"💥 Ошибка в цикле: {e}", exc_info=True)
                if self.running:
                    await asyncio.sleep(check_interval_sec)

        self.logger.info("🛑 Непрерывный режим завершён")

    def _should_run_by_schedule(self, timeframe: str, now: datetime) -> bool:
        """
        Проверяет, попадает ли текущее время в расписание обновления для таймфрейма.

        :param timeframe: ключ из TIMEFRAMES ("1h", "1d" и т.д.)
        :param now: текущее время в часовом поясе оркестратора (self.tz)
        :return: True если пора запускать обновление по расписанию
        """
        tf_config = TIMEFRAMES.get(timeframe, {})

        # 🔹 Проверка минуты (для 1h, 5m, 15m...)
        schedule_minute = tf_config.get("schedule_minute")
        if schedule_minute is not None and now.minute != schedule_minute:
            return False

        # 🔹 Проверка часа (для 1d, 1w...)
        schedule_hour = tf_config.get("schedule_hour")
        if schedule_hour is not None and now.hour != schedule_hour:
            return False

        # 🔹 Проверка дня недели (для 1w)
        schedule_weekday = tf_config.get("schedule_weekday")
        if schedule_weekday is not None and now.weekday() != schedule_weekday:
            return False

        # ✅ Все условия расписания выполнены (или не заданы)
        return True

    async def sync_instruments(self):
        """Синхронизация справочника инструментов из Tinkoff в БД."""
        self.logger.info("🔄 Синхронизация инструментов...")
        try:
            await self.broker.refresh_instruments_cache()
            instruments = list(self.broker._instruments_cache.values())
            saved = self.db.upsert_instruments_batch(instruments)
            self.logger.info(f"✅ Синхронизировано {saved} инструментов")
        except Exception as e:
            self.logger.error(f"❌ Ошибка синхронизации: {e}", exc_info=True)

    def add_instrument_to_config(
            self,
            ticker: str,
            timeframe: str,
            enabled: bool = True,
            strategy: str = "none",
            **kwargs
    ) -> bool:
        """
        Удобный метод для добавления инструмента в БД (через CLI или код).
        Пример:
            orchestrator.add_instrument_to_config(
                "SBER", "1h",
                strategy="sma_cross",
                history_depth_days=90,
                priority=10
            )
        """
        return self.db.upsert_instrument_config(
            ticker=ticker, timeframe=timeframe, enabled=enabled,
            strategy_name=strategy, **kwargs
        )

    def _start_admin_ui_thread(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Запускает Admin UI в фоновом потоке с правильным управлением жизненным циклом.
        """
        if not os.getenv("ENABLE_ADMIN", "0") == "1":
            return

        try:
            from admin_ui.main import app  # Импортируем FastAPI app, НЕ start_admin_ui

            import uvicorn
            from threading import Thread

            # Конфигурация uvicorn для программного запуска
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_level=os.getenv("UI_LOG_LEVEL", "info").lower(),
                access_log=False,  # Чтобы не спамить в логи оркестратора
                loop="asyncio",  # Используем тот же asyncio
                lifespan="on",  # Включаем lifespan-события
            )
            server = uvicorn.Server(config)

            # Флаг для отслеживания состояния
            self._ui_thread = Thread(
                target=server.run,
                daemon=True,  # Поток умрёт вместе с основным процессом
                name="AdminUI-Thread"
            )
            self._ui_server = server  # Сохраняем ссылку для возможного shutdown

            self._ui_thread.start()
            self.logger.info(f"✅ Admin UI запущен в фоне: http://{host}:{port}")

            # Даём серверу 2 секунды на старт перед продолжением
            import time
            time.sleep(2)

            # Проверяем, не упал ли сервер сразу
            if not server.started:
                self.logger.warning("⚠️ Admin UI не смог запуститься (возможно, порт занят)")

        except ImportError as e:
            self.logger.warning(f"⚠️ Admin UI не доступен (зависимости?): {e}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска Admin UI: {e}", exc_info=True)

    async def close(self):
        """Корректное завершение всех компонентов."""
        self.logger.info("🔌 Завершение работы...")
        self.running = False  # Сигнал циклу остановки

        # 1. Останавливаем Admin UI (если запущен)
        if hasattr(self, '_ui_server') and self._ui_server:
            try:
                self.logger.info("⏹️ Остановка Admin UI...")
                self._ui_server.should_exit = True  # Сигнал uvicorn на остановку
                if hasattr(self, '_ui_thread') and self._ui_thread.is_alive():
                    self._ui_thread.join(timeout=5)  # Ждём до 5 сек
                self.logger.info("✅ Admin UI остановлен")
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка остановки UI: {e}")

        # 2. Закрываем соединения с БД
        if self.db:
            self.db.close()

        # 3. Закрываем Telegram (если есть)
        if self.tg and hasattr(self.tg, 'close'):
            try:
                await self.tg.close()
            except:
                pass

        # 4. Закрываем брокер (если есть метод close)
        if self.broker and hasattr(self.broker, 'close'):
            try:
                await self.broker.close()
            except:
                pass

        self.logger.info("✅ Orchestrator остановлен")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.close()


# ===== ENTRY POINT =====

async def main():
    parser = argparse.ArgumentParser(description='Algo Trading Orchestrator')
    parser.add_argument('--once', action='store_true', help='Однократный запуск')
    parser.add_argument('--sync', action='store_true', help='Только синхронизация инструментов')
    parser.add_argument('--add', nargs=3, metavar=('TICKER', 'TF', 'STRATEGY'),
                        help='Добавить инструмент: --add SBER 1h sma_cross')

    # Параметры из env (в продакшене лучше использовать pydantic-settings)
    args = parser.parse_args()

    try:
        orchestrator = Orchestrator(
            # 🗄️ БД — из env
            db_host=os.getenv("DB_HOST", "postgres"),
            db_name=os.getenv("DB_NAME", "trading"),
            db_user=os.getenv("DB_USER", "trader"),
            db_password=os.getenv("DB_PASSWORD"),
            db_port=int(os.getenv("DB_PORT", "5432")),
            db_schema=os.getenv("DB_SCHEMA", "public"),

            # 📡 Tinkoff — из env
            tinkoff_token=os.getenv("TINKOFF_TOKEN"),

            # 🪵 Логирование
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            timezone_name=os.getenv("TIMEZONE", "Europe/Moscow"),

            # 📦 Telegram — опционально
            telegram_token=os.getenv("TELEGRAM_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        )
    except ValueError as e:
        print(f"❌ Ошибка инициализации: {e}", file=sys.stderr)
        print("💡 Проверь переменные окружения: DB_*, TINKOFF_TOKEN", file=sys.stderr)
        sys.exit(1)

    try:
        if args.add:
            # Режим добавления инструмента
            ticker, tf, strategy = args.add
            if not Timeframe.is_valid(tf):
                print(f"❌ Неверный таймфрейм: {tf}. Доступные: {Timeframe.all()}")
                sys.exit(1)
            success = orchestrator.add_instrument_to_config(
                ticker=ticker, timeframe=tf, strategy_name=strategy
            )
            print(f"{'✅' if success else '❌'} Инструмент {ticker}/{tf} добавлен")
            sys.exit(0 if success else 1)

        elif args.sync:
            await orchestrator.sync_instruments()

        elif args.once:
            await orchestrator.sync_instruments()
            await orchestrator.run_cycle()

        else:
            await orchestrator.sync_instruments()
            await orchestrator.run_continuous()

    finally:
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
import os
from zoneinfo import ZoneInfo
import asyncio
import signal
from datetime import datetime, timedelta
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

from logger import setup_logger
from config_manager import get_config_manager
from T_con import T_connector
from db_manager import DBManager

from strategy import run_strategy, get_price_type, _decimal_digits

TF_DEFAULTS = {
    "1m": {"history_depth_days": 7, "update_interval_minutes": 5},
    "5m": {"history_depth_days": 30, "update_interval_minutes": 15},
    "15m": {"history_depth_days": 60, "update_interval_minutes": 30},
    "1h": {"history_depth_days": 180, "update_interval_minutes": 60},
    "1d": {"history_depth_days": 365, "update_interval_minutes": 1440},
}

class MainLoader:
    """
    Главный оркестратор с поддержкой:
    - Нескольких таймфреймов на тикер
    - Hot config reload (авто-детект + SIGHUP)
    - Graceful shutdown
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.logger = None
        self.broker = None
        self.db = None
        self.config_manager = None
        self.running = True
        self._executor = ThreadPoolExecutor(max_workers=3)

        # Инициализация компонентов
        self._init_components()

        # Настройка сигналов
        self._setup_signals()

    def _init_components(self):
        """Инициализация всех компонентов."""
        try:
            # Config Manager (с hot reload)
            self.config_manager = get_config_manager(self.config_path)
            config = self.config_manager.get_config()

            # Логгер
            self.logger = setup_logger(
                name="MainLoader",
                log_file=config['settings']['log_file'],
                level=config['settings']['log_level']
            )
            self.logger.info("=" * 60)
            self.logger.info("ЗАГРУЗЧИК ДАННЫХ ЗАПУЩЕН")
            self.logger.info("=" * 60)
            self.logger.info(f"Конфиг: {self.config_path}")
            self.logger.info(f"PID: {os.getpid()}")

            self.tz = ZoneInfo(config.get('settings', {}).get('timezone', 'UTC'))
            self.logger.info(f"🌍 Часовой пояс: {self.tz}")


            # Брокер
            self.logger.info("Инициализация брокера...")
            self.broker = T_connector(self.config_path)

            # База данных
            self.logger.info("Инициализация базы данных...")
            self.db = DBManager(self.config_path)

            # Подписка на изменения конфига
            self.config_manager.register_reload_callback(self._on_config_reload)
            self.config_manager.register_reload_callback(lambda new, old: self.broker.reload_config())
            self.config_manager.register_reload_callback(lambda new, old: self.db.reload_config())


            # Запуск watcher конфига
            self.config_manager.start_watcher()
            self.config_manager.setup_signal_handler()

            # 🔥 Telegram Notifier
            telegram_cfg = config.get('telegram', {})
            if telegram_cfg.get('enabled', False):
                from telegram_notifier import TelegramNotifier
                self.tg = TelegramNotifier(
                    token=telegram_cfg.get('token', ''),
                    chat_id=telegram_cfg.get('chat_id', ''),
                    timeout=10
                )
                self.notify_on = set(telegram_cfg.get('notify_on', ['BUY', 'SELL']))
                self.disable_notification = telegram_cfg.get('disable_notification', False)
                self.logger.info("✅ TelegramNotifier подключен")

            else:
                self.tg = None
                self.notify_on = set()
                self.logger.info("ℹ️ Telegram уведомления отключены")

            self.logger.info("✅ Все компоненты инициализированы")

        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации: {e}", exc_info=True)
            raise

        if os.getenv("ENABLE_ADMIN", "0") == "1":
            import threading
            from admin_ui.main import start_admin_ui  # импортируй функцию из admin_ui.py

            thread = threading.Thread(target=start_admin_ui, daemon=True)
            thread.start()
            self.logger.info("✅ Admin UI запущен на порту 8000 (фон)")


    def _setup_signals(self):
        """Настройка обработчиков сигналов."""

        def sigint_handler(signum, frame):
            self.logger.info(f"\n📡 Получен SIGINT. Завершение работы...")
            self.running = False

        def sigterm_handler(signum, frame):
            self.logger.info(f"\n📡 Получен SIGTERM. Завершение работы...")
            self.running = False

        signal.signal(signal.SIGINT, sigint_handler)
        signal.signal(signal.SIGTERM, sigterm_handler)

    def _on_config_reload(self, new_config: Dict, old_config: Dict):
        """Callback при изменении конфига."""
        self.logger.info("🔄 Конфиг изменен — применяем обновления...")

        # Можно добавить логику для применения изменений на лету
        # Например, обновить интервалы загрузки без перезапуска

        old_instruments = len(old_config.get('instruments', []))
        new_instruments = len(new_config.get('instruments', []))

        if old_instruments != new_instruments:
            self.logger.info(f"Изменено количество инструментов: {old_instruments} → {new_instruments}")

    def _get_enabled_instruments(self) -> List[Dict]:
        """Получение актуального списка инструментов из конфига."""
        return self.config_manager.get_instruments(enabled_only=True)

    async def _load_instrument(self, ticker: str, timeframe: str,
                               history_depth: int,
                               strategy_name: str = None,
                               strategy_window: int = None) -> Dict:
        """
        Загрузка данных + запуск стратегии (если задана).
        strategy_window: сколько свечей нужно стратегии для расчета (опционально)
        """
        stats = {
            'ticker': ticker, 'timeframe': timeframe,
            'candles_loaded': 0, 'candles_saved': 0,
            'signal': None, 'strategy': strategy_name,
            'success': False, 'error': None
        }

        try:
            self.logger.info(f"📈 Загрузка: {ticker} ({timeframe})")

            # 1. Получаем UID
            uid = self.db.get_uid_by_ticker(ticker)
            if not uid:
                self.logger.warning(f"UID не найден в БД, запрашиваем у брокера...")
                uid = await self.broker.get_instrument_uid(ticker)

                if uid:
                    inst_info = self.broker._instruments_cache.get(ticker, {})
                    if inst_info:
                        self.db.upsert_instruments_batch([inst_info])

            if not uid:
                raise Exception(f"Не удалось получить UID для {ticker}")

            # 2. Последняя дата свечи
            last_date = self.db.get_last_candle_date(ticker, timeframe)

            # 3. Загрузка от брокера (инкремент)
            candles = await self.broker.load_historical_data(
                ticker=ticker,
                uid=uid,
                timeframe=timeframe,
                last_known_date=last_date,
                history_depth_days=history_depth
            )
            stats['candles_loaded'] = len(candles)

            # 4. Сохранение в БД
            if candles:
                saved = self.db.save_candles(
                    candles_list=candles, ticker=ticker, timeframe=timeframe
                )
                stats['candles_saved'] = saved

            self.logger.debug(
                f"🔍 Strategy check: ticker={ticker}, tf={timeframe}, "
                f"strategy_name='{strategy_name}', strategy_window={strategy_window}"
            )

            # 🔥 5. ЗАПУСК СТРАТЕГИИ (если задана)
            if strategy_name and strategy_name != "none":
                # Определяем окно: если не задано явно — берем дефолты
                window = strategy_window or self._get_default_window(strategy_name)
                # Запрашиваем из БД достаточно данных для расчета
                recent = self.db.get_recent_candles(ticker, timeframe, limit=window + 5)
                if len(recent) >= window:


                    if recent and len(recent) >= 2:
                        # Если первая свеча новее последней — значит, порядок обратный (DESC)
                        if recent[0]['time'] > recent[-1]['time']:
                            self.logger.debug(f"🔄 Данные в порядке DESC (новые→старые), разворачиваем в ASC (старые→новые)")
                            recent = list(reversed(recent))  # или recent[::-1]


                    prices = get_price_type(recent, price_type='LHCO_Avg')

                    # Запускаем стратегию
                    signal, extra_info = run_strategy(strategy_name, prices)
                    stats['signal'] = signal

                    # Если есть торговый сигнал — сохраняем
                    if signal in ["BUY", "SELL"]:
                        last_candle = recent[-1]
                        self.db.save_signal(
                            ticker=ticker,
                            timeframe=timeframe,
                            strategy=strategy_name,
                            signal=signal,
                            price=last_candle['close'],
                            candle_time=last_candle['time'],
                            metadata={'closes_count': len(prices)}
                        )

                        self.logger.info(
                            f"⚡ СИГНАЛ: {ticker}/{timeframe} [{strategy_name}] "
                            f"→ {signal} @ {last_candle['close']}"
                        )

                        # Отправляем уведомление в телеграм если нужно
                        if self.tg and signal in self.notify_on:
                            extra_data = {
                                'Свечей в расчёте': len(prices),
                                'Стратегия': strategy_name,
                                'Комментарий': extra_info
                            }
                            # Можно добавить больше метрик: RSI значение, SMA значения и т.д.

                            asyncio.create_task(
                                self.tg.send_signal(
                                    ticker=ticker,
                                    timeframe=timeframe,
                                    strategy=strategy_name,
                                    signal=signal,
                                    price=last_candle['close'],
                                    candle_time=last_candle['time'],
                                    extra=extra_data
                                )
                            )

                else:
                    self.logger.debug(
                        f"⏳ {ticker}/{timeframe}: недостаточно данных для {strategy_name} "
                        f"(нужно {window}, есть {len(recent)})"
                    )

            stats['success'] = True
            stats['total_in_db'] = self.db.get_candles_count(ticker, timeframe)

        except Exception as e:
            stats['error'] = str(e)
            self.logger.error(f"❌ Ошибка {ticker} ({timeframe}): {e}", exc_info=True)

        return stats

    def _get_default_window(self, strategy_name: str) -> int:
        """Дефолтные окна для стратегий (можно вынести в конфиг)."""
        windows = {
            "sma_cross": 50,  # нужно для SMA(21) + запас
            "rsi_oversold": 30,  # RSI(14) + запас
            "momentum": 10,  # lookback=3 + запас
            "bollinger": 40,  # BB(20) + запас
        }
        return windows.get(strategy_name, 20)  # дефолт 20 свечей

    async def _run_load_cycle(self) -> List[Dict]:
        """Один цикл загрузки всех инструментов."""
        instruments = self._get_enabled_instruments()
        self.logger.info(f"\n📋 Загрузка {len(instruments)} (ticker, timeframe) пар...")

        results = []
        for inst in instruments:
            if not self.running:
                break

            result = await self._load_instrument(
                ticker=inst['ticker'],
                timeframe=inst['timeframe'],
                history_depth=inst['history_depth_days'],
                strategy_name=inst.get('strategy', 'none'),
                strategy_window=inst.get('strategy_window')
            )
            results.append(result)

        return results

    def _should_load_instrument(self, inst: Dict, last_load_times: Dict) -> bool:
        """Проверка, пора ли загружать инструмент."""
        key = f"{inst['ticker']}_{inst['timeframe']}"
        last_load = last_load_times.get(key)

        if last_load is None:
            return True  # Ещё не загружали → грузим

        # 🔥 БЕЗОПАСНОЕ ПОЛУЧЕНИЕ + ДЕФОЛТ ИЗ НАШИХ ТАБЛИЦ
        interval = inst.get('update_interval_minutes')

        self.logger.debug(
            f"🔍 Проверка {inst['ticker']}/{inst['timeframe']}: "
            f"last_load={last_load}, interval={interval}, now={datetime.now()}"
        )

        if interval is None:
            # Берем дефолт из TF_DEFAULTS (которые у нас уже есть!)
            timeframe = inst.get('timeframe', '1d')
            interval = TF_DEFAULTS.get(timeframe, {}).get('update_interval_minutes', 60)
            self.logger.warning(
                f"⚠️ update_interval_minutes не указан для {inst['ticker']}/{timeframe}, "
                f"использую дефолт: {interval} мин"
            )

        next_load = last_load + timedelta(minutes=interval)
        return datetime.now() >= next_load

    async def run_continuous(self):
        """
        Непрерывный режим с индивидуальными интервалами для каждого (ticker, timeframe).
        """
        self.logger.info("🚀 Запуск в непрерывном режиме")
        self.logger.info("💡 Для перезагрузки конфига: kill -HUP {} или измените config.yaml".format(os.getpid()))

        last_load_times = {}  # Ключ: "ticker_timeframe", Значение: datetime последнего запуска

        while self.running:
            try:
                # Получаем актуальный список инструментов (из возможно обновленного конфига)
                instruments = self._get_enabled_instruments()

                # Фильтруем только те, что пора обновлять
                to_load = []
                for inst in instruments:
                    if self._should_load_instrument(inst, last_load_times):
                        to_load.append(inst)

                if to_load:
                    self.logger.info(f"\n⏰ Время обновлять {len(to_load)} инструментов:")
                    for inst in to_load:
                        self.logger.info(f"   - {inst['ticker']} ({inst['timeframe']})")

                    # Загружаем только те, что пора
                    results = []
                    for inst in to_load:
                        if not self.running:
                            break

                        # 🔥 Извлекаем параметры стратегии из конфига
                        strategy = inst.get("strategy", "none")

                        # Опционально: если в конфиге есть strategy_window — используем его
                        strategy_window = inst.get("strategy_window")  # можно добавить в конфиг

                        result = await self._load_instrument(
                            ticker=inst['ticker'],
                            timeframe=inst['timeframe'],
                            history_depth=inst['history_depth_days'],  # ← из конфига!
                            strategy_name=inst.get('strategy', 'none'),
                            strategy_window=inst.get('strategy_window')
                        )
                        results.append(result)

                        # Обновляем время последней загрузки
                        key = f"{inst['ticker']}_{inst['timeframe']}"
                        last_load_times[key] = datetime.now()

                    # Отчет
                    self.logger.info("\n📊 Отчет:")
                    for r in results:
                        status = "✅" if r['success'] else "❌"
                        self.logger.info(f"   {status} {r['ticker']} ({r['timeframe']}): {r['candles_saved']} свечей")
                else:
                    self.logger.debug("⏳ Все инструменты актуальны, ждем...")

                # Пауза 1 минута перед следующей проверкой
                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"Критическая ошибка в цикле: {e}", exc_info=True)
                if self.running:
                    await asyncio.sleep(60)

        self.logger.info("Непрерывный режим завершен")

    def sync_instruments(self):
        """Синхронизация справочника инструментов."""
        self.logger.info("\n📋 Синхронизация справочника инструментов...")

        try:
            asyncio.run(self.broker.refresh_instruments_cache())
            instruments_list = list(self.broker._instruments_cache.values())
            saved = self.db.upsert_instruments_batch(instruments_list)
            self.logger.info(f"✅ Синхронизировано {saved} инструментов")
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации: {e}", exc_info=True)

    def close(self):
        """Корректное завершение."""
        self.logger.info("🛑 Завершение работы...")

        if self.config_manager:
            self.config_manager.stop_watcher()

        if self.db:
            self.db.close()

        if self._executor:
            self._executor.shutdown(wait=False)

        # 🔥 Закрываем Telegram сессию
        if hasattr(self, 'tg') and self.tg:
            try:
                # Создаём временный event loop если нет активного
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.tg.close())
                except RuntimeError:
                    # Нет активного loop — создаём новый
                    asyncio.run(self.tg.close())
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка закрытия TelegramNotifier: {e}")

        self.logger.info("=" * 60)
        self.logger.info("ЗАГРУЗЧИК ОСТАНОВЛЕН")
        self.logger.info("=" * 60)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Загрузчик данных Tinkoff Invest')
    parser.add_argument('--once', action='store_true', help='Однократный запуск')
    parser.add_argument('--config', type=str, default='config.yaml', help='Путь к конфигу')
    parser.add_argument('--sync', action='store_true', help='Только синхронизация инструментов')

    args = parser.parse_args()

    loader = MainLoader(config_path=args.config)

    try:
        if args.sync:
            loader.sync_instruments()
        elif args.once:
            await loader._run_load_cycle()
        else:
            await loader.run_continuous()
    finally:
        loader.close()


if __name__ == "__main__":
    asyncio.run(main())
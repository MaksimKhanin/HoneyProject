# components/strategy_runner.py
"""
🧠 StrategyRunner: компонент для применения стратегий.
Отвечает за: получение данных → расчёт сигнала (BaseStrategy) → исполнение (LiveExecutor).

Архитектура:
• Pure Python (no pandas in production)
• Stateful стратегии (BaseStrategy)
• Безопасное исполнение (Watchdog vs Live)
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Type

from constants import (
    TIMEFRAMES, STRATEGY_DEFAULTS, StrategyName, SignalType,
    SIGNAL_META_KEYS, ValidationError
)
from logger import setup_logger

# 🔥 Новые импорты для новой архитектуры
from strategy.strategy_core import BaseStrategy, Bar, Signal as CoreSignal
from strategy.metrics_joiner import MetricsJoiner
from strategy.adapters.live_executor import LiveExecutor, ExecutionMode

# 🔗 Маппинг сигналов: старый формат (БД) ↔ новый формат (Enum)
# Нужно, чтобы сохранять сигналы в БД строками, как раньше
SIGNAL_MAP = {
    CoreSignal.BUY: "BUY",
    CoreSignal.SELL: "SELL",
    CoreSignal.HOLD: "HOLD",
    CoreSignal.PASS: "PASS",
    CoreSignal.ERROR: "ERROR",
    CoreSignal.CLOSE_BUY: "CLOSE_BUY",
    CoreSignal.CLOSE_SELL: "CLOSE_SELL",
    CoreSignal.CLOSE_ALL: "CLOSE_ALL",
}

# Обратный маппинг (если вдруг придёт строка)
REVERSE_SIGNAL_MAP = {v: k for k, v in SIGNAL_MAP.items()}


class StrategyRunner:
    """
    Исполнитель стратегии для одного (ticker, timeframe).
    Работает с наследниками BaseStrategy.
    """

    def __init__(
            self,
            ticker: str,
            timeframe: str,
            strategy_name: str,
            db,  # DBManager instance
            broker,  # TConnector instance (для проверки позиций)
            live_trading_enabled: bool = False,  # 🔥 Флаг из БД
            telegram_notifier=None,
            logger=None,
            account_id: Optional[str] = None,
            strategy_class: Optional[Type[BaseStrategy]] = None,  # 🔥 Класс стратегии (не функция!)
    ):
        self.ticker = ticker
        self.timeframe = timeframe
        self.strategy_name = strategy_name
        self.db = db
        self.broker = broker
        self.live_trading_enabled = live_trading_enabled
        self.tg = telegram_notifier
        self.account_id = account_id
        self.logger = logger or setup_logger(f"StrategyRunner.{ticker}.{timeframe}.{strategy_name}")

        # Параметры стратегии
        self.strategy_window: int = 20
        self.strategy_params: Dict = {}
        self.direction: str = "ALL"  # BUY_ONLY | SHORT_ONLY | ALL

        # 🔥 Инициализация ядра стратегии (экземпляр класса)
        self._strategy_instance: Optional[BaseStrategy] = None
        if strategy_class:
            self._strategy_class = strategy_class
        else:
            self._strategy_class = self._resolve_strategy_class()

        # 🔥 Инициализация исполнителя (ордера + уведомления)
        self.executor = LiveExecutor(
            broker=self.broker,
            telegram_notifier=telegram_notifier,
            live_trading_enabled=self.live_trading_enabled,
            logger=self.logger,
            account_id=self.account_id
        )

        # Статистика
        self.stats = {
            "signals_generated": 0,
            "signals_saved": 0,
            "notifications_sent": 0,
            "orders_executed": 0,  # 🔥 Новое поле
            "execution_mode": self.executor.mode.value,
            "last_run_time": None,
            "errors": []
        }

    def _resolve_strategy_class(self) -> Type[BaseStrategy]:
        """Фабрика: возвращает класс стратегии по имени."""
        # 🔥 Здесь регистрируешь новые стратегии
        from strategy.strategies.trailing_trend import TrailingTrendStrategy
        from strategy.strategies.trend_hunter import TrendHunterStrategy

        registry = {
            "TrailingTrend": TrailingTrendStrategy,
            "TrendHunter": TrendHunterStrategy,
            # Добавляй новые: "MyStrat": MyStratClass,
        }

        cls = registry.get(self.strategy_name)
        if not cls:
            self.logger.warning(f"⚠️ Стратегия '{self.strategy_name}' не найдена, используем заглушку")

            # Заглушка, которая всегда держит
            class HoldStrategy(BaseStrategy):
                name = "Hold"

                def on_bar(self, bar): return CoreSignal.HOLD

            return HoldStrategy
        return cls

    def configure(self, window: int = None, params: dict = None):
        """
        Настройка параметров стратегии.

        🔥 direction читается ИЗ params (из JSON), а не отдельным аргументом.
        Пример params: {"period": 20, "direction": "BUY_ONLY", "TSL": 0.05}
        """
        from constants import STRATEGY_DEFAULTS

        defaults = STRATEGY_DEFAULTS.get(self.strategy_name, {})
        self.strategy_window = window or defaults.get("default_window", 20)

        # 🔥 Объединяем дефолты и переданные параметры
        self.strategy_params = {**(defaults.get("params", {})), **(params or {})}

        # 🔥 Извлекаем direction из параметров (с дефолтом)
        self.direction = self.strategy_params.get('direction', 'ALL')
        if self.direction not in ("BUY_ONLY", "SHORT_ONLY", "ALL"):
            self.logger.warning(f"⚠️ Неверное direction '{self.direction}', установлено 'ALL'")
            self.direction = 'ALL'

        # Пересоздаём экземпляр стратегии с обновлёнными параметрами
        if self._strategy_class:
            self._strategy_instance = self._strategy_class(
                params=self.strategy_params,
                direction=self.direction
            )

        self.logger.debug(
            f"⚙️ Стратегия настроена: {self.strategy_name}, "
            f"window={self.strategy_window}, direction={self.direction}, "
            f"params={self.strategy_params}"
        )

    async def run(
            self,
            prices: Optional[List[float]] = None,  # Оставлен для совместимости, но игнорируется
            notify_signals: set = None
    ) -> Dict[str, Any]:
        """
        Запуск стратегии.
        1. Загружает бары + метрики из БД.
        2. Устанавливает историю баров в стратегию для онлайн-расчёта метрик.
        3. Прогоняет последний бар через стратегию.
        4. Исполняет сигнал через LiveExecutor.
        5. Сохраняет результат в БД.
        """
        self.logger.info(f"🧠 Запуск стратегии: {self.strategy_name} (mode={self.executor.mode.value})")

        try:
            # 🔥 1. Получаем бары с метриками (вместо голых цен)
            bars = MetricsJoiner.fetch_and_join(
                self.db, self.ticker, self.timeframe,
                limit=self.strategy_window + 20  # Буфер для расчётов
            )
            if len(bars) < self.strategy_window:
                self.logger.debug(f"⏳ Недостаточно данных: {len(bars)} < {self.strategy_window}")
                return {**self.stats, "success": True, "skipped": "insufficient_data"}

            # 🔥 2. Создаём экземпляр стратегии, если ещё не создан
            if not self._strategy_instance:
                self.configure()  # Вызовет _resolve_strategy_class и создаст экземпляр

            # 🔥 2.1 Устанавливаем историю баров для онлайн-расчёта метрик
            self._strategy_instance.set_bar_history(bars)

            # 🔥 3. Прогоняем ПОСЛЕДНИЙ бар через стратегию
            last_bar = bars[-1]


            # 🔥 1. СИНХРОНИЗАЦИЯ С БРОКЕРОМ (обязательно перед расчётом сигнала)
            self.logger.info(f"🔍 Запрос позиции у брокера для {self.ticker}...")
            real_pos = await self._fetch_real_position()
            self.logger.debug(f"📥 Ответ брокера: {real_pos}")
            self._strategy_instance.sync_with_broker(real_pos)
            self.logger.info(
                f"🧠 Стратегия синхронизирована: "
                f"in_position={self._strategy_instance.in_position}, "
                f"entry_price={self._strategy_instance.entry_price}, "
                f"current_sl={self._strategy_instance.current_sl}"
            )


            core_signal = self._strategy_instance.on_bar(last_bar)
            self.logger.info(f"📡 Сигнал стратегии: {core_signal.value} | Bar close: {last_bar.close}")

            # Конвертируем сигнал в строку для БД/лога
            signal_str = SIGNAL_MAP.get(core_signal, str(core_signal))

            # 🔥 4. Исполнение (ордера + уведомления)
            # extra_meta = {
            #     "Свечей в расчёте": len(bars),
            #     "Direction": self.direction,
            # }

            # 🔥 Стратегия сама собирает данные для уведомления (метрики + P&L)
            notification_context = self._strategy_instance.get_notification_context(last_bar)


            self.logger.debug(f"notification_context = {notification_context}")

            # 🔥 Исполнение
            exec_result = await self.executor.execute(
                ticker=self.ticker,
                timeframe=self.timeframe,
                strategy=self.strategy_name,
                signal=core_signal,
                price=last_bar.close,
                candle_time=last_bar.time,
                db=self.db,
                extra={"Direction": self.direction},  # Только общие мета-данные
                quantity=1.0,
                notification_context=notification_context  # 🔥 Передаём готовый контекст
            )

            # 🔥 Обновляем статистику из результата исполнения
            if exec_result.get("executed"):
                self.stats["orders_executed"] += 1
                self.logger.info(f"✅ Ордер исполнен: {exec_result.get('message')}")

            # 🔥 5. Сохранение сигнала в БД (ВСЕ сигналы: BUY, SELL, HOLD, PASS, CLOSE_*)
            # is_tradable проверяет только торговые сигналы, но мы сохраняем ВСЕ для логирования
            # 🔥 Формируем metadata из релевантных метрик стратегии + системных данных
            strategy_metrics = notification_context or {}

            # 🔥 5.1 Обновляем метрики в БД актуальными значениями из стратегии
            # Это гарантирует, что в tink.metrics всегда свежие данные, которые использовала стратегия
            if strategy_metrics:
                self._update_metrics_in_db(last_bar, strategy_metrics)

            saved = self.db.save_signal(
                ticker=self.ticker,
                timeframe=self.timeframe,
                strategy=self.strategy_name,
                signal=signal_str,  # Строка для БД
                price=last_bar.close,
                candle_time=last_bar.time,
                metadata={
                    **strategy_metrics,  # 🔥 Данные из _get_relevant_metrics()
                    "execution_mode": self.executor.mode.value,
                    "order_id": exec_result.get("order", {}).get("order_id"),
                }
            )

            if saved:
                self.stats["signals_saved"] += 1
                self.logger.info(
                    f"⚡ СИГНАЛ: {self.ticker}/{self.timeframe} "
                    f"[{self.strategy_name}] → {signal_str} @ {last_bar.close}"
                )

            self.stats["signals_generated"] += 1
            self.stats["last_run_time"] = datetime.now()

            return {**self.stats, "success": True, "signal": signal_str, "exec_result": exec_result}

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.stats["errors"].append(error_msg)
            self.logger.error(f"❌ Ошибка стратегии: {error_msg}", exc_info=True)
            return {**self.stats, "success": False, "error": error_msg}

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику выполнения."""
        return {
            "ticker": self.ticker,
            "timeframe": self.timeframe,
            "strategy": self.strategy_name,
            "mode": self.executor.mode.value,
            **self.stats
        }

    def configure_trading(
            self, ticker: str, timeframe: str, strategy: str = None,
            live_enabled: bool = None, strategy_params: dict = None, **kwargs
    ) -> bool:
        """
        Удобный метод для настройки. direction передаётся ВНУТРИ strategy_params.
        """
        current = self.db.get_instrument_config(ticker, timeframe) or {}
        current_params = current.get("strategy_params", {}) or {}
        merged_params = {**current_params, **(strategy_params or {})}

        # Валидация direction
        direction = merged_params.get('direction', 'ALL')
        if direction not in ("BUY_ONLY", "SHORT_ONLY", "ALL"):
            merged_params['direction'] = 'ALL'

        return self.db.upsert_instrument_config(
            ticker=ticker, timeframe=timeframe, enabled=current.get("enabled", True),
            strategy_name=strategy or current.get("strategy_name", "none"),
            history_depth_days=kwargs.get("history_depth_days"),
            update_interval_minutes=kwargs.get("update_interval_minutes"),
            strategy_window=kwargs.get("strategy_window"),
            strategy_params=merged_params,
            live_trading_enabled=live_enabled if live_enabled is not None else current.get("live_trading_enabled",
                                                                                           False),
        )

    async def _fetch_real_position(self) -> Optional[Dict]:
        if not self.broker:
            self.logger.warning("⚠️ Broker не инициализирован, синхронизация невозможна")
            return None

        try:
            # 🔥 Запрашиваем ВСЕ позиции. TConnector сам разрешит account_id внутри.
            all_positions = await self.broker.get_positions()
            self.logger.debug(
                f"📥 Брокер вернул {len(all_positions)} позиций: {[p.get('ticker') for p in all_positions]}")

            if not all_positions:
                return None

            ticker_upper = self.ticker.upper()
            for pos in all_positions:
                pos_ticker = (pos.get("ticker") or "").upper()
                # Точное совпадение тикера
                if pos_ticker == ticker_upper:
                    self.logger.info(
                        f"✅ Найдена позиция у брокера: {pos_ticker} | Qty: {pos.get('quantity')} | Avg: {pos.get('average_position_price')}")
                    return pos

            self.logger.debug(f"⚠️ Позиция по {self.ticker} не найдена в ответе брокера")
            return None

        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка запроса позиций у брокера {self.ticker}: {e}", exc_info=True)
            return None

    def _update_metrics_in_db(self, bar: Bar, strategy_metrics: Dict[str, Any]):
        """
        Обновляет метрики в таблице tink.metrics актуальными значениями из стратегии.

        Проблема: MetricsEngine рассчитывает метрики на основе свечей, но не знает о внутренних
        метриках стратегии (например, Cooldown, Pullback и т.д.), которые вычисляются в on_bar().

        Решение: После расчёта сигнала берём релевантные метрики из стратегии и обновляем
        запись в tink.metrics за эту же candle_time, сливая с существующими данными.

        :param bar: текущий бар
        :param strategy_metrics: dict с метриками из get_notification_context()
        """

        self.logger.debug(
            f"_update_metrics_in_db -> strategy_metrics = {strategy_metrics}")

        # Фильтруем только числовые метрики (PnL, Entry, SL и т.д. - строки, их не сохраняем в metrics)
        numeric_metrics = {
            k: v for k, v in strategy_metrics.items()
            if isinstance(v, (int, float))
        }



        if not numeric_metrics:
            self.logger.debug(f"⚠️ Нет числовых метрик для обновления в БД: {list(strategy_metrics.keys())}")
            return

        try:
            # Получаем текущие метрики из БД (если есть)
            existing_metrics_list = self.db.get_latest_metrics(self.ticker, self.timeframe, limit=1)
            existing_metrics = {}
            if existing_metrics_list:
                existing_metrics = existing_metrics_list[0].get('metrics', {}) or {}

            # Сливаем: существующие + новые метрики стратегии (новые перезаписывают старые)
            merged_metrics = {**existing_metrics, **numeric_metrics}

            # Сохраняем обратно в БД
            self.db.save_metrics(
                ticker=self.ticker,
                timeframe=self.timeframe,
                candle_time=bar.time,
                metrics=merged_metrics
            )

            self.logger.info(
                f"✅ Метрики обновлены в БД для {self.ticker}/{self.timeframe}@{bar.time}: "
                f"{len(numeric_metrics)} полей ({list(numeric_metrics.keys())})"
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления метрик в БД: {e}", exc_info=True)
# adapters/live_executor.py
"""
Исполнитель сигналов в live-режиме.
Реальные позиции проверяются ТОЛЬКО через брокера (TConnector).
Поддерживает режимы: WATCHDOG (уведомления) и LIVE (исполнение).
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
from strategy.strategy_core import Signal
from logger import setup_logger
import logging


class ExecutionMode(str, Enum):
    WATCHDOG = "watchdog"  # Только уведомления в TG
    LIVE = "live"  # Реальное исполнение ордеров


class LiveExecutor:
    """
    Исполнитель сигналов.

    :param broker: Экземпляр TConnector
    :param telegram_notifier: Экземпляр TelegramNotifier
    :param live_trading_enabled: Флаг из БД (False по умолчанию = безопасный режим)
    :param account_id: ID счета брокера (нужен для LIVE)
    """

    def __init__(
            self,
            broker,
            telegram_notifier=None,
            live_trading_enabled: bool = False,
            logger=None,
            account_id: Optional[str] = None
    ):
        self.broker = broker
        self.tg = telegram_notifier
        self.mode = ExecutionMode.LIVE if live_trading_enabled else ExecutionMode.WATCHDOG
        self.account_id = account_id
        self.logger = logger or setup_logger("LiveExecutor", level="INFO")

        # Кэш позиций (только для снижения нагрузки на API, не для принятия решений!)
        self._pos_cache: List[Dict] = []
        self._last_pos_fetch_ts: float = 0
        self._pos_cache_ttl_sec: int = 30

        self.logger.info(f"🚀 LiveExecutor инициализирован: режим={self.mode.value}")

    async def _fetch_real_positions(self, force: bool = False) -> List[Dict]:
        """Запрос реальных позиций у брокера. Кэширует на 30 сек для защиты от rate-limit."""
        now = datetime.now().timestamp()
        if not force and (now - self._last_pos_fetch_ts < self._pos_cache_ttl_sec):
            return self._pos_cache

        try:
            positions = await self.broker.get_positions(account_id=self.account_id)
            self._pos_cache = positions
            self._last_pos_fetch_ts = now
            self.logger.debug(f"📦 Загружено {len(positions)} позиций от брокера")
            return positions
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения позиций: {e}", exc_info=True)
            return self._pos_cache  # Фоллбэк на старый кэш

    async def _has_open_position(self, ticker: str, desired_type: str) -> bool:
        """Проверка: есть ли уже открытая позиция у брокера."""
        positions = await self._fetch_real_positions()
        t_upper = ticker.upper()

        for pos in positions:
            p_ticker = (pos.get("ticker") or "").upper()
            qty = pos.get("quantity", 0)
            p_type = "long" if qty > 0 else ("short" if qty < 0 else None)

            if p_ticker == t_upper and p_type == desired_type:
                return True
        return False

    async def _check_trading_conflicts(self, db, ticker: str, strategy: str, timeframe: str) -> bool:
        """
        Проверяет, нет ли других стратегий с live_trading_enabled=True для этого тикера.
        Возвращает True, если конфликтов НЕТ (можно торговать).
        """
        if not db:
            return True
        try:
            configs = db.get_enabled_instrument_configs()
            for cfg in configs:
                if cfg.get("ticker", "").upper() == ticker.upper() and cfg.get("live_trading_enabled", False):
                    # Исключаем текущую пару (ticker+timeframe+strategy)
                    is_same = (
                            cfg.get("strategy_name") == strategy and
                            cfg.get("timeframe") == timeframe
                    )
                    if not is_same:
                        self.logger.warning(
                            f"⚠️ Конфликт: {cfg['strategy_name']}/{cfg['timeframe']} уже торгует {ticker}")
                        return False
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки конфликтов: {e}")
            return False  # В случае ошибки → безопасный режим (не торгуем)

    async def _send_order_stub(self, ticker: str, signal: Signal, price: float, qty: float) -> Dict:
        """
        Заглушка отправки ордера.
        В будущем здесь будет вызов broker.post_order() или аналог.
        """
        self.logger.info(f"📤 [ORDER STUB] {signal.value} {ticker} @ {price} x{qty}")
        return {"order_id": f"stub_{datetime.now().timestamp()}", "status": "simulated"}

    async def execute(
            self,
            ticker: str, timeframe: str, strategy: str, signal: Signal,
            price: float, candle_time: datetime, db=None,
            extra: Optional[Dict] = None, quantity: float = 1.0,
            notification_context: Optional[Dict[str, Any]] = None  # 🔥 Теперь принимаем готовый контекст
    ) -> Dict:
        result = {
            "ticker": ticker, "timeframe": timeframe, "strategy": strategy,
            "signal": signal.value if isinstance(signal, Signal) else signal,
            "price": price, "mode": self.mode.value, "executed": False, "message": ""
        }

        # 🔕 Подавление HOLD и PASS: если нет позиции и не DEBUG-режим
        if signal in (Signal.HOLD, Signal.PASS):
            has_position = "PnL" in (notification_context or {})
            if not has_position and not self.logger.isEnabledFor(logging.DEBUG):
                result["message"] = f"⚪ {signal.value} suppressed (no position, non-debug)"
                return result  # ТГ НЕ шлём

        # 🔔 Формируем payload для ТГ: берём СТРАТЕГИЧЕСКИЙ контекст как базу
        tg_extra = {"Mode": self.mode.value}
        if notification_context:
            tg_extra.update(notification_context)
        if extra:
            for k, v in extra.items():
                if k not in tg_extra:  # Контекст стратегии имеет приоритет
                    tg_extra[k] = v

        # 🔔 Отправка в Телеграм
        if self.tg:
            try:
                await self.tg.send_signal(
                    ticker=ticker, timeframe=timeframe, strategy=strategy,
                    signal=signal.value if isinstance(signal, Signal) else signal,
                    price=price, candle_time=candle_time, extra=tg_extra
                )
                result["message"] = "✅ TG sent"
            except Exception as e:
                result["message"] = f"⚠️ TG error: {e}"

        # ... (остальная логика WATCHDOG / LIVE без изменений) ...
        if self.mode == ExecutionMode.WATCHDOG:
            result["message"] += " | 🐕 Watchdog: no execution"
            return result

        sig_val = signal.value if isinstance(signal, Signal) else signal
        if sig_val in ("BUY", "SELL"):
            pos_type = "long" if sig_val == "BUY" else "short"
            if await self._has_open_position(ticker, pos_type):
                result["message"] += f" | ⚠️ {pos_type} already open"
                return result
            order = await self._send_order_stub(ticker, signal, price, quantity)
            result["executed"] = True
            result["order"] = order
            result["message"] += f" | 🟢 Order {sig_val} sent"
        elif sig_val in ("CLOSE_BUY", "CLOSE_SELL", "CLOSE_ALL"):
            self.logger.info(f"📤 [CLOSE STUB] Closing {sig_val} for {ticker}")
            result["executed"] = True
            result["message"] += " | 🔴 Close order sent"

        return result
# FZ`strategy.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any
import logging


class Signal(str, Enum):
    """
    Торговые сигналы. Строки для совместимости с БД и логгерами.
    """
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"        # 🔒 Позиция открыта, ждём условий выхода или трейлим
    PASS = "PASS"        # 🕊️ Позиции нет, сигнал на вход не сработал
    ERROR = "ERROR"
    CLOSE_BUY = "CLOSE_BUY"  # Закрыть лонг
    CLOSE_SELL = "CLOSE_SELL"  # Закрыть шорт
    CLOSE_ALL = "CLOSE_ALL"  # Аварийный выход


@dataclass(frozen=True)
class Bar:
    """
    Универсальный бар для стратегий.
    Pure Python, никаких pandas/numpy.
    """
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    metrics: Dict[str, float] = field(default_factory=dict)

    @property
    def timestamp(self) -> float:
        """Unix timestamp для кулдаунов и сравнений."""
        return self.time.timestamp()

    def pct_change(self, prev_close: float) -> float:
        """Процентное изменение от предыдущего закрытия."""
        if prev_close == 0:
            return 0.0
        return (self.close - prev_close) / prev_close


class BaseStrategy(ABC):
    """
    Базовый класс для ВСЕХ стратегий.

    Правила:
    1. Состояние хранится ВНУТРИ стратегии (никаких глобалов)
    2. Метрики читаются из bar.metrics (подгружаются из БД)
    3. Сигналы возвращаются как Signal enum
    4. Pure Python, no pandas/numpy в production

    🔹 Конвенция для авто-генерации UI:
    Стратегия может объявить классовый атрибут _params_schema для подсказок в админке:

        _params_schema = {
            "min_pullback": {
                "type": "float",
                "default": 0.03,
                "min": 0.01,
                "max": 0.5,
                "desc": "Минимальный откат для входа (3%)"
            },
            "direction": {
                "type": "select",
                "default": "ALL",
                "options": ["BUY_ONLY", "SHORT_ONLY", "ALL"],
                "desc": "Направление торговли"
            },
        }

    Если _params_schema не объявлен — в админке будет просто JSON-поле без подсказок.
    """
    name: str = "BaseStrategy"
    _params_schema: Dict[str, Dict] = {}  # 🔥 Опциональный атрибут для UI

    def __init__(self, params: Optional[Dict] = None, direction: str = "ALL"):
        """
        :param params: Словарь параметров стратегии
        :param direction: "BUY_ONLY" | "SHORT_ONLY" | "ALL"
        """
        self.params = params or {}
        self.direction = direction

        if self.direction not in ("BUY_ONLY", "SHORT_ONLY", "ALL"):
            raise ValueError(f"Invalid direction: {self.direction}")

        self.logger = logging.getLogger(f"Strategy.{self.name}")
        self._reset_state()

    def _reset_state(self):
        """Сброс состояния после закрытия позиции."""
        self.in_position = False
        self.position_type: Optional[str] = None  # "long" | "short"
        self.entry_price = 0.0
        self.current_sl = 0.0
        self.last_exit_ts = 0.0  # timestamp последнего выхода
        self._bar_count = 0

    @abstractmethod
    def on_bar(self, bar: Bar) -> Signal:
        """
        Главный метод. Вызывается на каждом новом баре.

        :param bar: Бар с ценами и метриками
        :return: Сигнал для исполнения
        """
        ...

    # ===== Утилиты =====

    def _get_metric(self, bar: Bar, key: str, default: float = 0.0) -> float:
        """Безопасное чтение метрики из bar.metrics."""
        if not bar.metrics:
            return default
        val = bar.metrics.get(key)
        return val if val is not None else default

    def _can_enter_long(self) -> bool:
        """Проверка: разрешён ли вход в лонг."""
        return self.direction in ("BUY_ONLY", "ALL") and not self.in_position

    def _can_enter_short(self) -> bool:
        """Проверка: разрешён ли вход в шорт."""
        return self.direction in ("SHORT_ONLY", "ALL") and not self.in_position

    def _close_position(self, bar: Bar):
        """Внутренний метод закрытия позиции (сброс стейта)."""
        self.in_position = False
        self.position_type = None
        self.last_exit_ts = bar.timestamp
        self.entry_price = 0.0
        self.current_sl = 0.0

    def _calc_pnl_pct(self, current_price: float) -> float:
        """P&L в процентах от входа."""
        if self.entry_price == 0:
            return 0.0
        if self.position_type == "short":
            return (self.entry_price - current_price) / self.entry_price * 100.0
        return (current_price - self.entry_price) / self.entry_price * 100.0

    def get_notification_context(self, bar: Bar) -> Dict[str, Any]:
        """
        Генерирует контекст для уведомлений (ТГ, логи, БД).
        Включает P&L (если есть позиция) и метрики, которые переопределяет наследник.
        """
        ctx = {}

        # 🔥 Авто-P&L для открытой позиции
        if self.in_position and self.entry_price > 0:
            pnl_pct = self._calc_pnl_pct(bar.close)
            ctx["PnL"] = f"{pnl_pct:+.2f}%"
            ctx["Entry"] = f"{self.entry_price:.2f}"
            ctx["SL"] = f"{self.current_sl:.2f}"
            ctx["Pos"] = self.position_type.upper()

        # 🔥 Вызываем шаблонную функцию наследника
        ctx.update(self._get_relevant_metrics(bar))
        return ctx

    def _get_relevant_metrics(self, bar: Bar) -> Dict[str, Any]:
        """
        ШАБЛОН: Переопредели в стратегии, чтобы вернуть только нужные метрики.
        По умолчанию возвращает всё, что есть в баре.
        """
        return bar.metrics or {}

    def sync_with_broker(self, broker_pos: Optional[Dict[str, Any]] = None):
        """Синхронизирует стейт с брокером. Логирует изменения."""
        prev = f"in_pos={self.in_position}, type={self.position_type}, entry={self.entry_price}"

        if broker_pos and broker_pos.get("quantity", 0) != 0:
            qty = broker_pos["quantity"]
            self.in_position = True
            self.position_type = "long" if qty > 0 else "short"
            self.entry_price = float(broker_pos.get("average_position_price", 0))
            self.logger.info(f"🔄 Sync Broker -> Strategy: {prev} => {self.position_type.upper()} @ {self.entry_price}")
        else:
            if self.in_position:
                self.logger.info(f"🔄 Sync Broker Empty -> Reset: {prev} => CLOSED")
            self._reset_state()
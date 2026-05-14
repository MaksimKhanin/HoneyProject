# core/constants.py
"""
🎯 ЕДИНЫЙ РЕЕСТР КОНСТАНТ ПРОЕКТА
Версия 2.0: + настройки загрузки и стратегий
"""

from datetime import timedelta
from enum import StrEnum
from typing import Final


# =============================================================================
# 📊 ТАЙМФРЕЙМЫ — единый источник для загрузки, БД, стратегий
# =============================================================================

class Timeframe(StrEnum):
    """Типизированные таймфреймы."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"
    W1 = "1w"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._value2member_map_

    @classmethod
    def all(cls) -> list[str]:
        return [tf.value for tf in cls]


# 🎯 TIMEFRAMES: параметры загрузки + дефолты для стратегий
# Используется: TConnector, DBManager, PriceLoader, StrategyRunner
TIMEFRAMES: Final[dict[str, dict]] = {
    Timeframe.M1: {
        "interval_code": 1,  # Tinkoff CandleInterval
        "max_days_per_request": 1,  # Лимит API за один запрос
        "overlap_window": timedelta(minutes=30),  # Для инкрементальной загрузки
        "default_history_depth_days": 7,  # Если не указано в БД
        "default_update_interval_min": 5,  # Как часто обновлять
        "default_strategy_window": 100,  # Свечей для расчёта стратегий
        # 🔥 Расписание: запускать каждую минуту (по умолчанию)
        "schedule_minute": None,  # None = разрешено каждую минуту
    },
    Timeframe.M5: {
        "interval_code": 2,
        "max_days_per_request": 7,
        "overlap_window": timedelta(hours=1),
        "default_history_depth_days": 30,
        "default_update_interval_min": 15,
        "default_strategy_window": 100,
        "schedule_minute": 0,  # 🔥 Запускать на 0-й минуте каждого 5-минутного интервала
    },
    Timeframe.M15: {
        "interval_code": 3,
        "max_days_per_request": 28,
        "overlap_window": timedelta(hours=3),
        "default_history_depth_days": 60,
        "default_update_interval_min": 30,
        "default_strategy_window": 80,
        "schedule_minute": 0,
    },
    Timeframe.H1: {
        "interval_code": 4,
        "max_days_per_request": 60,
        "overlap_window": timedelta(hours=12),
        "default_history_depth_days": 180,
        "default_update_interval_min": 60,
        "default_strategy_window": 50,
        "schedule_minute": 0,  # 🔥 Запускать на 0-й минуте каждого часа (например, 14:00, 15:00...)
    },
    Timeframe.D1: {
        "interval_code": 5,
        "max_days_per_request": 365,
        "overlap_window": timedelta(days=3),
        "default_history_depth_days": 365,
        "default_update_interval_min": 1440,  # 24 часа
        "default_strategy_window": 30,
        "schedule_hour": 2,   # 🔥 Запускать в 10:00 по московскому времени
    },
    Timeframe.W1: {
        "interval_code": 6,
        "max_days_per_request": 365,
        "overlap_window": timedelta(weeks=1),
        "default_history_depth_days": 365,
        "default_update_interval_min": 10080,  # 7 дней
        "default_strategy_window": 20,
        "schedule_weekday": 0,  # 🔥 Понедельник (0 = понедельник, 6 = воскресенье)
        "schedule_hour": 10,  # 🔥 В 10:00
    },
}


# =============================================================================
# 🧠 СТРАТЕГИИ — дефолтные параметры
# =============================================================================

class StrategyName(StrEnum):
    """Названия стратегий (для валидации)."""
    SMA_CROSS = "sma_cross"
    RSI_OVERSOLD = "rsi_oversold"
    MOMENTUM = "momentum"
    BOLLINGER = "bollinger"
    NONE = "none"

    @classmethod
    def is_active(cls, value: str) -> bool:
        return value != cls.NONE


# Дефолтные окна для стратегий (если не указано в БД)
STRATEGY_DEFAULTS: Final[dict[str, dict]] = {
    StrategyName.SMA_CROSS: {
        "default_window": 50,
        "params": {"fast": 21, "slow": 50}
    },
    StrategyName.RSI_OVERSOLD: {
        "default_window": 30,
        "params": {"period": 14}
    },
    StrategyName.MOMENTUM: {
        "default_window": 10,
        "params": {"lookback": 3}
    },
    StrategyName.BOLLINGER: {
        "default_window": 40,
        "params": {"period": 20, "std_mult": 2}
    },
}


# =============================================================================
# 🚦 СИГНАЛЫ
# =============================================================================

class SignalType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    PASS = "PASS"
    ERROR = "ERROR"
    CLOSE_BUY = "CLOSE_BUY"
    CLOSE_SELL = "CLOSE_SELL"

    @classmethod
    def is_tradable(cls, value: str) -> bool:
        return value in (cls.BUY, cls.SELL, cls.CLOSE_BUY, cls.CLOSE_SELL)


SIGNAL_TYPES: Final[set[str]] = {s.value for s in SignalType}

# Метаданные для сигналов — стандартные ключи
SIGNAL_META_KEYS: Final[dict[str, str]] = {
    "strategy": "strategy_name",      # Название стратегии
    "rsi": "rsi_value",               # RSI индикатор
    "sma_fast": "sma_fast_period",    # Быстрая скользящая
    "sma_slow": "sma_slow_period",    # Медленная скользящая
    "volume_ratio": "volume_ratio",   # Отношение объёма к среднему
    "confidence": "confidence_score", # Уверенность сигнала (0-1)
}

# =============================================================================
# 🗄️ БАЗА ДАННЫХ
# =============================================================================

# Таблицы
TABLE_INSTRUMENTS: Final[str] = "instruments"
TABLE_CANDLES: Final[str] = "candles"
TABLE_SIGNALS: Final[str] = "signals"
TABLE_INSTRUMENT_CONFIG: Final[str] = "instrument_config"  # ← НОВАЯ!

# Поля таблицы instrument_config
INSTRUMENT_CONFIG_FIELDS: Final[list[str]] = [
    "id", "ticker", "timeframe", "enabled",
    "history_depth_days", "update_interval_minutes",
    "strategy_name", "strategy_window", "strategy_params",
    "priority", "created_at", "updated_at"
]

# Дефолты БД
DEFAULT_DB_SCHEMA: Final[str] = "public"
DEFAULT_DB_PORT: Final[int] = 5432
DB_POOL_MIN_CONN: Final[int] = 1
DB_POOL_MAX_CONN: Final[int] = 3  # Важно для 2GB VPS!

# =============================================================================
# 📡 TINKOFF API
# =============================================================================

INSTRUMENT_CATEGORIES: Final[tuple[str, ...]] = (
    "shares", "bonds", "etfs", "currencies", "futures"
)
INDICATIVES_CATEGORY: Final[str] = "indicative"

API_RATE_LIMIT_DELAY: Final[float] = 0.2
DEFAULT_TIMEOUT_SEC: Final[int] = 30
DEFAULT_RETRIES: Final[int] = 3
RETRY_DELAY_SEC: Final[float] = 1.5

# =============================================================================
# 🪵 ОБЩИЕ НАСТРОЙКИ
# =============================================================================

DEFAULT_LOG_LEVEL: Final[str] = "DEBUG"
DEFAULT_LOG_FILE: Final[str] = "logs/app.log"
DEFAULT_TIMEZONE: Final[str] = "Europe/Moscow"
DEFAULT_CACHE_TTL_SEC: Final[int] = 3600
DEFAULT_HISTORY_DEPTH_DAYS: Final[int] = 365

# 🚨 ЛИМИТЫ ДЛЯ 2GB VPS
MAX_CANDLES_IN_MEMORY: Final[int] = 10000
MAX_CONCURRENT_LOADS: Final[int] = 2
BATCH_SAVE_SIZE: Final[int] = 500


"""
Единые исключения проекта.
Лови и обрабатывай централизованно, логируй единообразно.
"""

class TradingBotError(Exception):
    """Базовое исключение проекта."""
    def __init__(self, message: str, context: dict = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)


class APIError(TradingBotError):
    """Ошибка при работе с внешним API (Tinkoff, etc.)."""
    pass


class DatabaseError(TradingBotError):
    """Ошибка при работе с базой данных."""
    pass


class ValidationError(TradingBotError):
    """Ошибка валидации входных данных."""
    pass


class RateLimitError(APIError):
    """Превышен лимит запросов к API."""
    pass


class InstrumentNotFoundError(ValidationError):
    """Инструмент не найден в кэше или БД."""
    pass
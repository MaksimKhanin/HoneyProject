# tests/fixtures.py
"""
Фикстуры и тестовые данные.
Минимум магии — только явные значения.
"""

from typing import Final, Dict, List

# 🎯 Тестовый инструмент (должен существовать и быть ликвидным)
TEST_INSTRUMENT: Final[Dict] = {
    "ticker": "SBER",
    "expected_name_contains": "Сбербанк",  # Для валидации ответа API
    "expected_currency": "RUB",
    "expected_exchange": "MOEX",
}

# 📊 Ожидаемые параметры свечей
CANDLE_VALIDATION: Final[Dict] = {
    "required_fields": ["time", "open", "high", "low", "close", "volume"],
    "price_positive": True,  # Цены должны быть > 0
    "volume_non_negative": True,
    "ohlc_consistency": True,  # low <= open,close <= high
}

# 🧠 Параметры тестовой стратегии
STRATEGY_TEST_PARAMS: Final[Dict] = {
    "sma_cross": {
        "window": 20,
        "expected_signal_types": ["BUY", "SELL", "HOLD"],
        "min_data_points": 21,  # SMA(20) требует минимум 21 точку
    },
    "rsi_oversold": {
        "window": 30,
        "expected_signal_types": ["BUY", "SELL", "HOLD"],
        "min_data_points": 15,
    },
}

# ⏱ Ожидаемые тайминги (для детекта проблем с производительностью)
PERFORMANCE_THRESHOLDS: Final[Dict] = {
    "api_auth_max_sec": 5,
    "instrument_fetch_max_sec": 30,
    "candles_load_100_max_sec": 15,
    "db_save_100_max_sec": 5,
    "strategy_run_max_sec": 2,
}

# 🗄️ Тестовые данные для БД (для проверки записи/чтения)
DB_VALIDATION: Final[Dict] = {
    "instrument_fields": ["uid", "ticker", "name", "type", "currency"],
    "candle_fields": ["ticker", "timeframe", "time", "open", "high", "low", "close", "volume"],
    "signal_fields": ["ticker", "timeframe", "strategy", "signal", "price", "candle_time"],
}
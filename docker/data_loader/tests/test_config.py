# tests/test_config.py
"""
Конфигурация для интеграционных тестов.
Использует отдельную схему в БД и тестовый токен.
"""

import os
from datetime import datetime
from typing import Final

# 🎯 Тестовые параметры
TEST_SCHEMA: Final[str] = "test_trading"  # Отдельная схема, не трогает prod
TEST_TICKER: Final[str] = os.getenv("TEST_TICKER", "SBER")  # Тикер для теста
TEST_TIMEFRAME: Final[str] = os.getenv("TEST_TIMEFRAME", "1h")
TEST_STRATEGY: Final[str] = os.getenv("TEST_STRATEGY", "sma_cross")

# 🔑 API токен для тестов (можно тот же, что prod, но лучше отдельный)
TEST_TINKOFF_TOKEN: Final[str] = os.getenv("TINKOFF_TOKEN_TEST",
                                           os.getenv("TINKOFF_TOKEN",
                                           't.YS2uyKoFJ_BjA2Jz2CLNsRrpEWL5e7ad4Mq48OKNUySiNbs2QrGhIcW4gkj4-MTl62oO1quiZK8GPLkd6OM7Dw'))

# 🗄️ БД для тестов
TEST_DB_CONFIG: Final[dict] = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "name": os.getenv("DB_NAME", "trade_db"),
    "user": os.getenv("DB_USER", "khanin"),
    "password": os.getenv("DB_PASSWORD", "qaZXsw21Aa!"),
    "schema": TEST_SCHEMA,  # ← Ключевое: тесты в отдельной схеме!
}

# ⏱ Таймауты для тестов (короче, чем в prod)
TEST_TIMEOUT_SEC: Final[int] = 60
TEST_API_TIMEOUT_SEC: Final[int] = 30

# 📊 Параметры теста
TEST_HISTORY_DEPTH_DAYS: Final[int] = 3  # Не грузим год истории в тесте
TEST_CANDLES_MIN_EXPECTED: Final[int] = 10  # Минимум свечей для валидации
TEST_STRATEGY_WINDOW: Final[int] = 20  # Окно для стратегии в тесте

# 🪵 Логирование тестов
TEST_LOG_FILE: Final[str] = "./test_integration.log"
TEST_LOG_LEVEL: Final[str] = "DEBUG"

# 📦 Отчёт
REPORT_DIR: Final[str] = "test_reports"
REPORT_FILENAME: Final[str] = f"integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def validate_test_config() -> list[str]:
    """Валидирует наличие обязательных переменных. Возвращает список ошибок."""
    errors = []

    if not TEST_TINKOFF_TOKEN or TEST_TINKOFF_TOKEN in ("YOUR_TOKEN_HERE", "xxx", ""):
        errors.append("❌ TINKOFF_TOKEN или TINKOFF_TOKEN_TEST не установлен")

    if not TEST_DB_CONFIG["password"]:
        errors.append("❌ DB_PASSWORD не установлен")

    if not os.access(os.path.dirname(TEST_LOG_FILE), os.W_OK):
        errors.append(f"⚠️ Нет прав на запись в лог-файл: {TEST_LOG_FILE}")

    if not os.access(REPORT_DIR, os.W_OK):
        os.makedirs(REPORT_DIR, exist_ok=True)
        if not os.access(REPORT_DIR, os.W_OK):
            errors.append(f"❌ Нет прав на запись отчётов в: {REPORT_DIR}")

    return errors
# tests/cleanup.py
"""
Очистка тестовых данных после запуска тестов.
Работает в отдельной схеме, чтобы не трогать prod.
"""

import psycopg2
from logger import setup_logger
from test_config import TEST_DB_CONFIG, TEST_SCHEMA

logger = setup_logger("TestCleanup", "/var/log/trading/test_cleanup.log")


def cleanup_test_schema(config: dict = None, schema: str = None) -> bool:
    """Полная очистка тестовых данных (без удаления таблиц)."""
    cfg = config or TEST_DB_CONFIG
    test_schema = schema or TEST_SCHEMA

    logger.info(f"🧹 Очистка тестовой схемы: {test_schema}")

    try:
        conn = psycopg2.connect(
            host=cfg["host"], port=cfg["port"], database=cfg["name"],
            user=cfg["user"], password=cfg["password"]
        )
        cur = conn.cursor()

        # Очищаем данные. IF EXISTS не нужен, просто ловим ошибку, если таблицы ещё нет
        tables = ["instrument_config", "signals", "candles", "instruments"]
        for table in tables:
            try:
                cur.execute(f"DELETE FROM {test_schema}.{table}")
                logger.debug(f"🗑️ Очищено: {test_schema}.{table}")
            except psycopg2.errors.UndefinedTable:
                logger.debug(f"ℹ️ Таблица {test_schema}.{table} ещё не существует, пропускаем")

        # Сбрасываем последовательности (если таблицы есть)
        for table in ["instrument_config", "signals"]:
            try:
                seq_name = f"{test_schema}.{table}_id_seq"
                cur.execute(f"SELECT setval('{seq_name}', 1, false)")
            except psycopg2.errors.UndefinedTable:
                pass

        conn.commit()
        logger.info(f"✅ Тестовая схема {test_schema} очищена")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Ошибка очистки: {e}", exc_info=True)
        return False
    finally:
        cur.close()
        conn.close()


def drop_test_schema(config: dict = None, schema: str = None) -> bool:
    """Полное удаление тестовой схемы (радикальная очистка)."""
    cfg = config or TEST_DB_CONFIG
    test_schema = schema or TEST_SCHEMA

    logger.warning(f"🔥 УДАЛЕНИЕ тестовой схемы: {test_schema}")

    try:
        conn = psycopg2.connect(
            host=cfg["host"], port=cfg["port"], database=cfg["name"],
            user=cfg["user"], password=cfg["password"]
        )
        cur = conn.cursor()

        # DROP CASCADE удалит все объекты в схеме
        cur.execute(f"DROP SCHEMA IF EXISTS {test_schema} CASCADE")
        conn.commit()

        logger.info(f"✅ Схема {test_schema} удалена")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Ошибка удаления схемы: {e}", exc_info=True)
        return False
    finally:
        cur.close()
        conn.close()
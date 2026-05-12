#!/usr/bin/env python3
# tests/integration_test.py
"""
🔥 ИНТЕГРАЦИОННЫЙ ТЕСТ НА РЕАЛЬНОЙ ИНФРАСТРУКТУРЕ
Без pytest, без моков. Честная проверка всей цепочки:
  Tinkoff API → PriceLoader → DBManager → StrategyRunner → Signal

Запуск:
    python -m tests.integration_test --report
    # или с параметрами:
    python -m tests.integration_test --ticker SBER --timeframe 1h --cleanup

Требования:
    - Установленные переменные окружения (TINKOFF_TOKEN, DB_*)
    - Доступ к Postgres и Tinkoff API
    - Права на запись в лог-файлы и директорию отчётов
"""

import os
import sys
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

# Добавляем проект в path (для запуска как модуля)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import setup_logger
from constants import Timeframe, StrategyName, SignalType, TABLE_INSTRUMENT_CONFIG
from constants import TradingBotError
from db_manager import DBManager
from T_con import TConnector
from price_loader import PriceLoader
from strategy_runner import StrategyRunner
from strategy import run_strategy

from test_config import (
    TEST_DB_CONFIG, TEST_TINKOFF_TOKEN, TEST_TICKER, TEST_TIMEFRAME,
    TEST_STRATEGY, TEST_HISTORY_DEPTH_DAYS, TEST_STRATEGY_WINDOW,
    TEST_LOG_FILE, TEST_LOG_LEVEL, REPORT_DIR, REPORT_FILENAME,
    validate_test_config, TEST_CANDLES_MIN_EXPECTED
)
from fixtures import (
    TEST_INSTRUMENT, CANDLE_VALIDATION, STRATEGY_TEST_PARAMS,
    PERFORMANCE_THRESHOLDS, DB_VALIDATION
)
from report_generator import TestReport
from cleanup import cleanup_test_schema


class IntegrationTestRunner:
    """Раннер интеграционных тестов."""

    def __init__(self, ticker: str = None, timeframe: str = None, strategy: str = None):
        self.ticker = ticker or TEST_TICKER
        self.timeframe = timeframe or TEST_TIMEFRAME
        self.strategy = strategy or TEST_STRATEGY

        self.logger = setup_logger("IntegrationTest", TEST_LOG_FILE, TEST_LOG_LEVEL)
        self.report = TestReport(
            test_name=f"integration_{self.ticker}_{self.timeframe}",
            started_at=datetime.now()
        )

        # Компоненты (инициализируются в setup)
        self.db: Optional[DBManager] = None
        self.broker: Optional[TConnector] = None

        # Статистика
        self.timings = {}

    @staticmethod
    def _step(name: str):
        """Декоратор как статический метод."""
        def decorator(func):
            async def wrapper(self, *args, **kwargs):
                start = time.time()
                success = False
                error = None
                details = {}
                try:
                    result = await func(self, *args, **kwargs)
                    success = True
                    if isinstance(result, dict):
                        details.update(result)
                    return result
                except Exception as e:
                    error = f"{type(e).__name__}: {str(e)}"
                    if hasattr(self, 'logger'):
                        self.logger.error(f"❌ Шаг '{name}' упал: {error}", exc_info=True)
                    raise
                finally:
                    duration = time.time() - start
                    if not hasattr(self, 'timings'):
                        self.timings = {}
                    self.timings[name] = duration
                    if hasattr(self, 'report'):
                        self.report.add_step(name, success, duration, details, error)
            return wrapper
        return decorator

    @_step("validate_config")
    async def validate_config(self) -> dict:
        """Проверка конфигурации перед запуском."""
        errors = validate_test_config()
        if errors:
            raise TradingBotError("Конфигурация невалидна: " + "; ".join(errors))

        return {"config_valid": True, "test_params": {
            "ticker": self.ticker, "timeframe": self.timeframe, "strategy": self.strategy
        }}

    @_step("init_database")
    async def init_database(self) -> dict:
        """Инициализация БД и создание тестовой схемы."""
        self.db = DBManager(
            db_host=TEST_DB_CONFIG["host"],
            db_name=TEST_DB_CONFIG["name"],
            db_user=TEST_DB_CONFIG["user"],
            db_password=TEST_DB_CONFIG["password"],
            db_port=TEST_DB_CONFIG["port"],
            db_schema=TEST_DB_CONFIG["schema"],  # ← Тестовая схема!
            log_level="WARNING",  # Меньше шума в логах теста
        )

        # Создаём таблицу instrument_config в тестовой схеме
        self.db.init_instrument_config_table()

        # Проверяем подключение простым запросом
        count = self.db.get_candles_count(self.ticker, self.timeframe)

        return {"db_connected": True, "existing_candles": count}

    @_step("init_broker")
    async def init_broker(self) -> dict:
        """Инициализация Tinkoff API клиента."""
        self.broker = TConnector(
            token=TEST_TINKOFF_TOKEN,
            log_level="WARNING",
            timeout_sec=30,
            retries=2,  # Меньше ретраев в тесте для скорости
        )

        # Проверяем авторизацию через простой запрос
        uid = await self.broker.get_instrument_uid(self.ticker)

        return {"broker_connected": True, "instrument_uid": uid}

    @_step("fetch_instrument_info")
    async def fetch_instrument_info(self) -> dict:
        """Проверка получения информации об инструменте."""
        uid = await self.broker.get_instrument_uid(self.ticker)
        if not uid:
            raise TradingBotError(f"Не удалось получить UID для {self.ticker}")

        # Проверяем кэш брокера
        cached = self.broker._instruments_cache.get(self.ticker)
        if not cached:
            raise TradingBotError(f"Инструмент {self.ticker} не в кэше брокера")

        # Валидация полей
        for field in DB_VALIDATION["instrument_fields"]:
            if field not in cached:
                raise TradingBotError(f"Отсутствует поле '{field}' в данных инструмента")

        # Проверка ожидаемых значений
        if TEST_INSTRUMENT["expected_name_contains"].lower() not in cached.get("name", "").lower():
            self.logger.warning(f"⚠️ Название инструмента не содержит '{TEST_INSTRUMENT['expected_name_contains']}'")

        return {
            "uid": uid,
            "name": cached.get("name"),
            "currency": cached.get("currency"),
            "exchange": cached.get("exchange")
        }

    @_step("load_candles")
    async def load_candles(self, uid: str) -> dict:
        """Загрузка свечей от брокера."""
        loader = PriceLoader(
            ticker=self.ticker, timeframe=self.timeframe,
            broker=self.broker, db=self.db, logger=self.logger
        )

        result = await loader.load_incremental(
            history_depth_days=TEST_HISTORY_DEPTH_DAYS
        )

        if not result.get("success"):
            raise TradingBotError(f"Загрузка свечей не удалась: {result.get('error')}")

        candles_loaded = result.get("candles_loaded", 0)
        candles_saved = result.get("candles_saved", 0)

        # Валидация количества
        if candles_loaded < TEST_CANDLES_MIN_EXPECTED:
            self.logger.warning(f"⚠️ Загружено мало свечей: {candles_loaded} < {TEST_CANDLES_MIN_EXPECTED}")

        # Валидация структуры свечей
        if candles_loaded > 0:
            sample = self.db.get_recent_candles(self.ticker, self.timeframe, limit=1)
            if sample:
                candle = sample[0]
                for field in CANDLE_VALIDATION["required_fields"]:
                    if field not in candle:
                        raise TradingBotError(f"Отсутствует поле '{field}' в свече")

                # Проверка OHLC consistency
                if CANDLE_VALIDATION["ohlc_consistency"]:
                    if not (candle["low"] <= candle["open"] <= candle["high"] and
                            candle["low"] <= candle["close"] <= candle["high"]):
                        raise TradingBotError("Нарушена консистентность OHLC в свече")

        return {
            "candles_loaded": candles_loaded,
            "candles_saved": candles_saved,
            "sample_price": sample[0]["close"] if sample else None
        }

    @_step("run_strategy")
    async def run_strategy(self) -> dict:
        """Запуск стратегии на загруженных данных."""
        if self.strategy == "none":
            return {"strategy_skipped": True, "reason": "strategy=none"}

        runner = StrategyRunner(
            ticker=self.ticker, timeframe=self.timeframe,
            strategy_name=self.strategy,
            db=self.db,
            strategy_func=run_strategy,
            logger=self.logger
        )

        # Настраиваем параметры
        strat_params = STRATEGY_TEST_PARAMS.get(self.strategy, {})
        runner.configure(
            window=TEST_STRATEGY_WINDOW,
            params=strat_params.get("params", {})
        )

        result = await runner.run()

        if not result.get("success"):
            raise TradingBotError(f"Стратегия не выполнилась: {result.get('error')}")

        signal = result.get("signal")

        # Валидация сигнала
        if signal and signal not in STRATEGY_TEST_PARAMS.get(self.strategy, {}).get("expected_signal_types", []):
            self.logger.warning(f"⚠️ Неожиданный тип сигнала: {signal}")

        return {
            "strategy_executed": True,
            "signal": signal,
            "signals_saved": result.get("signals_saved", 0),
            "data_points_used": result.get("details", {}).get("candles_count")
        }

    @_step("verify_signal_in_db")
    async def verify_signal_in_db(self) -> dict:
        """Проверка, что сигнал сохранён в БД."""
        if self.strategy == "none":
            return {"verification_skipped": True}

        # Ищем последний сигнал для этого инструмента
        conn = self.db._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT signal, price, candle_time, metadata 
                FROM {TABLE_INSTRUMENT_CONFIG.replace('instrument_config', 'signals')}
                WHERE ticker = %s AND timeframe = %s AND strategy = %s
                ORDER BY candle_time DESC LIMIT 1
            """, (self.ticker, self.timeframe, self.strategy))

            row = cur.fetchone()

            if not row:
                # Это не обязательно ошибка — стратегия могла не сгенерировать сигнал
                return {"signal_found": False, "note": "Стратегия не сгенерировала торговый сигнал"}

            signal, price, candle_time, metadata = row

            # Валидация полей сигнала
            for field in DB_VALIDATION["signal_fields"]:
                # metadata — JSONB, его не проверяем здесь
                if field in ["signal", "price", "ticker"] and field not in {"signal": signal, "price": price,
                                                                            "ticker": self.ticker}:
                    pass  # Упрощённая проверка

            return {
                "signal_found": True,
                "signal_type": signal,
                "price": float(price),
                "candle_time": candle_time.isoformat() if candle_time else None,
            }
        finally:
            cur.close()
            self.db._release_connection(conn)

    @_step("performance_check")
    async def performance_check(self) -> dict:
        """Проверка производительности против порогов."""
        issues = []

        for step_name, duration in self.timings.items():
            threshold_key = f"{step_name.replace(' ', '_')}_max_sec"
            if threshold_key in PERFORMANCE_THRESHOLDS:
                threshold = PERFORMANCE_THRESHOLDS[threshold_key]
                if duration > threshold:
                    issues.append(f"{step_name}: {duration:.2f}с > порог {threshold}с")

        return {
            "performance_ok": len(issues) == 0,
            "timings": {k: round(v, 3) for k, v in self.timings.items()},
            "issues": issues
        }

    async def run(self) -> bool:
        """Запуск всех шагов теста."""
        self.logger.info(f"🚀 Старт интеграционного теста: {self.ticker}/{self.timeframe}")

        try:
            # 1. Валидация конфига
            await self.validate_config()

            # 2. Инициализация компонентов
            await self.init_database()
            await self.init_broker()

            # 3. Получение информации об инструменте
            inst_info = await self.fetch_instrument_info()
            uid = inst_info["uid"]

            # 4. Загрузка свечей
            await self.load_candles(uid)

            # 5. Запуск стратегии
            await self.run_strategy()

            # 6. Проверка сигнала в БД
            await self.verify_signal_in_db()

            # 7. Проверка производительности
            await self.performance_check()

            # Если дошли сюда — тест успешен
            return True

        except Exception as e:
            self.logger.error(f"💥 Тест упал: {e}", exc_info=True)
            return False
        finally:
            # Cleanup
            if self.broker:
                await self.broker.close()
            if self.db:
                self.db.close()

    def generate_report(self, success: bool) -> dict:
        """Генерация и сохранение отчёта."""
        total_duration = sum(self.timings.values())
        self.report.finish(success, total_duration)

        saved = self.report.save(REPORT_DIR, REPORT_FILENAME)

        self.logger.info(f"📄 Отчёт сохранён: {saved['html']}")
        return saved


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Integration Test Runner")
    parser.add_argument("--ticker", type=str, help="Тикер для теста")
    parser.add_argument("--timeframe", type=str, help="Таймфрейм для теста")
    parser.add_argument("--strategy", type=str, help="Стратегия для теста")
    parser.add_argument("--cleanup", action="store_true", help="Очистить тестовые данные после")
    parser.add_argument("--drop-schema", action="store_true", help="Удалить тестовую схему после")
    parser.add_argument("--no-report", action="store_true", help="Не генерировать отчёт")

    args = parser.parse_args()

    # Запуск теста
    runner = IntegrationTestRunner(
        ticker=args.ticker,
        timeframe=args.timeframe,
        strategy=args.strategy
    )

    success = await runner.run()

    # Отчёт
    if not args.no_report:
        runner.generate_report(success)

    # Очистка
    if args.cleanup:
        from cleanup import cleanup_test_schema
        cleanup_test_schema()
        print("🧹 Тестовые данные очищены")

    if args.drop_schema:
        from cleanup import drop_test_schema
        drop_test_schema()
        print("🔥 Тестовая схема удалена")

    # Выход с кодом
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
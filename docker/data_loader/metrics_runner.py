#!/usr/bin/env python3
# metrics_runner.py
"""
Скрипт для расчёта метрик по всем активным инструментам.
Запускай по cron или как отдельный сервис.

Запуск:
    python metrics_runner.py --ticker SBER --timeframe 1h
    python metrics_runner.py --all --timeframes 1h,1d
    python metrics_runner.py --daemon  # периодический режим
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# 🔥 Добавляем корень проекта и docker/data_loader в sys.path
project_root = Path(__file__).resolve().parent.parent  # honeyProject/
data_loader_dir = project_root / "docker" / "data_loader"

for path in [str(project_root), str(data_loader_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"✅ sys.path updated: {project_root}")  # Для дебага

try:
    from metrics.registry import list_metrics, METRIC_REGISTRY
    print(f"📋 Registered metrics: {list_metrics()}")
    if not list_metrics():
        print("⚠️ WARNING: Реестр метрик пуст! Проверь пути импорта в builtins/*.py")
except ImportError as e:
    print(f"❌ Не удалось импортировать registry: {e}")
    sys.exit(1)

# Дальше — обычные импорты
import asyncio
import argparse
from datetime import datetime, timedelta

from metrics.engine import MetricsEngine
from db_manager import DBManager
from T_con import TConnector
from price_loader import PriceLoader
from constants import TIMEFRAMES, DEFAULT_DB_PORT

AVAILABLE_TIMEFRAMES = TIMEFRAMES.keys()


async def run_metrics_for_instrument(ticker: str, timeframe: str, db, broker, metric_names=None, depth_days: int = 180):
    """Загружает инкремент из API + считает метрики по данным из БД."""
    print(f"\n🔄 Запуск: {ticker}/{timeframe}")

    # 1️⃣ Синхронизируем данные с брокером (загружаем только новые)
    loader = PriceLoader(ticker=ticker, timeframe=timeframe, broker=broker, db=db)
    await loader.load_incremental(history_depth_days=depth_days)

    # 2️⃣ 🚀 БЕРЁМ ДАННЫЕ ИЗ БД (источник истины для метрик)
    # get_recent_candles возвращает от НОВЫХ к СТАРЫМ (DESC)
    candles_desc = db.get_recent_candles(ticker, timeframe, limit=2000)

    # Переворачиваем в ASC (от СТАРЫХ к НОВЫМ) для корректного расчёта индикаторов
    candles = list(reversed(candles_desc))

    print(f"📊 Доступно свечей из БД для расчёта: {len(candles)}")

    if len(candles) < 15:
        print(f"⚠️ Недостаточно данных. Нужно минимум 15 свечей (для RSI), есть {len(candles)}")
        print("💡 Запусти сначала полную загрузку: python metrics_runner.py --ticker SBER --timeframe 1h --depth 365")
        return {"ticker": ticker, "timeframe": timeframe, "error": "Not enough data"}

    # 3️⃣ Считаем метрики
    from metrics.engine import MetricsEngine
    engine = MetricsEngine(db=db, metric_names=metric_names)

    # Передаём последние свечи (движок сам возьмёт нужное окно)
    metrics = engine.calculate_for_candles(ticker, timeframe, candles)

    print(f"✅ Рассчитано метрик: {len(metrics)} → {list(metrics.keys())}")
    return {"ticker": ticker, "timeframe": timeframe, "metrics": metrics}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str)
    parser.add_argument("--timeframe", type=str, default="1d")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--depth", type=int, default=180, help="Глубина истории в днях")
    parser.add_argument("--metrics", type=str, help="Метрики через запятую (по умолчанию все)")
    args = parser.parse_args()

    metric_names = args.metrics.split(",") if args.metrics else None

    # Инициализация
    db = DBManager(
        db_host=os.getenv("DB_HOST", "localhost"),
        db_name=os.getenv("DB_NAME", "trading"),
        db_user=os.getenv("DB_USER", "trader"),
        db_password=os.getenv("DB_PASSWORD"),
        db_port=int(os.getenv("DB_PORT", DEFAULT_DB_PORT)),
        db_schema=os.getenv("DB_SCHEMA", "public"),
        log_level="INFO"
    )

    broker = TConnector(token=os.getenv("TINKOFF_TOKEN"), log_level="WARNING")

    try:
        if args.all:
            configs = db.get_enabled_instrument_configs()
            for cfg in configs:
                await run_metrics_for_instrument(cfg["ticker"], cfg["timeframe"], db, broker, metric_names, args.depth)
        elif args.ticker:
            await run_metrics_for_instrument(args.ticker, args.timeframe, db, broker, metric_names, args.depth)
        else:
            print("❌ Укажи --ticker или --all")
    finally:
        db.close()
        await broker.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path

    # Авто-загрузка .env из корня проекта
    project_root = Path(__file__).parent.parent.parent
    print(project_root)

    load_dotenv(project_root / ".env")

    print(f"DB_HOST: {os.getenv('DB_HOST', 'НЕ ЗАГРУЖЕН')}")
    print(f"TINKOFF_TOKEN: {'***' if os.getenv('TINKOFF_TOKEN') else 'НЕ ЗАГРУЖЕН'}")

    asyncio.run(main())
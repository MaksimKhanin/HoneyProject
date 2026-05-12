# admin_ui/core.py
"""Ядро Admin UI: auth, DB-коннект, константы. Без YAML!"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from logger import setup_logger
from constants import (
    Timeframe, SignalType, StrategyName,
    TIMEFRAMES, STRATEGY_DEFAULTS, DEFAULT_DB_PORT, DEFAULT_DB_SCHEMA
)
from db_manager import DBManager
from T_con import TConnector

# === Auth ===
ADMIN_USER = os.getenv("UI_USER", "admin")
ADMIN_PASSWORD = os.getenv("UI_PASS", "admin")
security = HTTPBasic()


def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USER or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Access denied")
    return credentials.username


# === DB Manager (ленивая инициализация) ===
_db: Optional[DBManager] = None


def get_db() -> DBManager:
    """Возвращает singleton DBManager. Инициализируется при первом вызове."""
    global _db
    if _db is None:
        _db = DBManager(
            db_host=os.getenv("DB_HOST", "localhost"),
            db_name=os.getenv("DB_NAME", "trading"),
            db_user=os.getenv("DB_USER", "trader"),
            db_password=os.getenv("DB_PASSWORD"),
            db_port=int(os.getenv("DB_PORT", DEFAULT_DB_PORT)),
            db_schema=os.getenv("DB_SCHEMA", DEFAULT_DB_SCHEMA),
            log_level="WARNING",  # Меньше шума в логах UI
            log_file=os.getenv("UI_LOG_FILE", "admin_ui.log")
        )
        # Создаём таблицу, если нет (идемпотентно)
        _db.init_instrument_config_table()
    return _db


def close_db():
    """Закрытие соединения при завершении приложения."""
    global _db
    if _db:
        _db.close()
        _db = None


# === Константы (остаются без изменений) ===
AVAILABLE_TIMEFRAMES = [tf.value for tf in Timeframe]
TF_DEFAULTS = {
    tf: {
        "history_depth_days": cfg["default_history_depth_days"],
        "update_interval_minutes": cfg["default_update_interval_min"],
        "strategy_window": cfg["default_strategy_window"],
    }
    for tf, cfg in TIMEFRAMES.items()
}


# === DB-хелперы для UI ===


def get_all_instrument_configs(db: DBManager = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Получает ВСЕ конфигурации из БД (включая отключенные).
    Для UI: показываем серым то, что enabled=false.
    """
    conn = db._get_connection()
    try:
        cur = conn.cursor()
        # ✅ Убрали priority из SELECT и ORDER BY
        cur.execute("""
            SELECT 
                ticker, timeframe, enabled,
                history_depth_days, update_interval_minutes,
                strategy_name, strategy_window, strategy_params,
                created_at, updated_at
            FROM instrument_config
            ORDER BY ticker ASC, timeframe ASC
        """)

        columns = [desc[0] for desc in cur.description]
        results = []
        for row in cur.fetchall():
            config = dict(zip(columns, row))
            # Парсим JSONB поле strategy_params
            if isinstance(config.get('strategy_params'), str):
                import json
                config['strategy_params'] = json.loads(config['strategy_params'])
            results.append(config)
        return results
    except Exception as e:
        logger.error(f"❌ Ошибка получения конфигов: {e}", exc_info=True)
        return []  # Возвращаем пустой список при ошибке, а не падаем
    finally:
        cur.close()
        db._release_connection(conn)


def get_instrument_config(db: DBManager, ticker: str, timeframe: str) -> Optional[Dict]:
    """Получает конфиг по ключу."""
    return db.get_instrument_config(ticker, timeframe)


def upsert_instrument_config(
        db: DBManager,
        ticker: str,
        timeframe: str,
        enabled: bool = True,
        history_depth_days: int = None,
        update_interval_minutes: int = None,
        strategy_name: str = "none",
        strategy_window: int = None,
        strategy_params: dict = None,
        live_trading_enabled: bool = False
) -> bool:
    """Вставляет или обновляет конфиг в БД."""
    return db.upsert_instrument_config(
        ticker=ticker, timeframe=timeframe, enabled=enabled,
        history_depth_days=history_depth_days,
        update_interval_minutes=update_interval_minutes,
        strategy_name=strategy_name,
        strategy_window=strategy_window,
        strategy_params=strategy_params,
        live_trading_enabled=live_trading_enabled
    )


def toggle_instrument_enabled(db: DBManager, ticker: str, timeframe: str, enabled: bool) -> bool:
    """Включает/выключает инструмент."""
    return db.toggle_instrument_enabled(ticker, timeframe, enabled)

def delete_instrument_config(db: DBManager, ticker: str, timeframe: str) -> bool:
    """Удаляет конкретную конфигурацию."""
    return db.delete_instrument_config(ticker, timeframe)

def delete_instrument_configs_by_ticker(db: DBManager, ticker: str) -> int:
    """Удаляет все конфигурации по тикеру."""
    return db.delete_instrument_configs_by_ticker(ticker)


def get_portfolio_stats(db: DBManager, limit: int = 50) -> List[Dict]:
    """Получает статистику для страницы портфеля."""
    conn = db._get_connection()
    try:
        cur = conn.cursor()
        # Последние сигналы + метрики по свечам
        cur.execute("""
            WITH latest_candles AS (
                SELECT ticker, timeframe, close, time,
                       ROW_NUMBER() OVER (PARTITION BY ticker, timeframe ORDER BY time DESC) as rn
                FROM candles
            ),
            signal_stats AS (
                SELECT ticker, timeframe, strategy,
                       COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') as signals_24h,
                       MAX(signal) as last_signal,
                       MAX(candle_time) as last_signal_time
                FROM signals
                GROUP BY ticker, timeframe, strategy
            )
            SELECT 
                lc.ticker, lc.timeframe, lc.close as last_price,
                ss.strategy, ss.signals_24h, ss.last_signal, ss.last_signal_time
            FROM latest_candles lc
            LEFT JOIN signal_stats ss 
                ON lc.ticker = ss.ticker AND lc.timeframe = ss.timeframe
            LEFT JOIN instrument_config cfg 
                ON lc.ticker = cfg.ticker AND lc.timeframe = cfg.timeframe
            WHERE lc.rn = 1 AND cfg.enabled = TRUE
            ORDER BY lc.ticker ASC
            LIMIT %s
        """, (limit,))

        columns = [desc[0] for desc in cur.description]
        results = []
        for row in cur.fetchall():
            item = dict(zip(columns, row))
            # Форматируем время для UI
            if item.get("last_signal_time"):
                item["last_signal_time"] = item["last_signal_time"].strftime("%Y-%m-%d %H:%M")
            results.append(item)
        return results
    finally:
        cur.close()
        db._release_connection(conn)


def get_candle_stats(db: DBManager, ticker: str, timeframe: str, limit: int = 100) -> Dict:
    """Считает базовые метрики для графика/карточек."""
    candles = db.get_recent_candles(ticker, timeframe, limit=limit)
    if not candles:
        return {"avg": None, "std": None, "min": None, "max": None, "change_pct": None}

    prices = [c["close"] for c in candles]
    n = len(prices)
    avg = sum(prices) / n
    variance = sum((x - avg) ** 2 for x in prices) / n if n > 1 else 0
    std = variance ** 0.5

    # Изменение за период
    change_pct = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] != 0 else 0

    return {
        "avg": round(avg, 4),
        "std": round(std, 4),
        "min": min(prices),
        "max": max(prices),
        "change_pct": round(change_pct, 2),
        "count": n
    }

 #===== BROKER DEPENDENCY =====
_broker: Optional[TConnector] = None

def get_broker() -> TConnector:
    """Возвращает singleton TConnector для UI."""
    global _broker
    if _broker is None:
        _broker = TConnector(
            token=os.getenv("TINKOFF_TOKEN"),
            log_level=os.getenv("UI_LOG_LEVEL", "WARNING"),
            log_file=os.getenv("UI_LOG_FILE", "admin_ui.log").replace("admin_ui", "tinkoff_ui")
        )
    return _broker

def close_broker():
    """Закрытие брокера при завершении приложения."""
    global _broker
    if _broker:
        asyncio.run(_broker.close())
        _broker = None


# === Логгер ===
logger = setup_logger(
    name="AdminUI",
    log_file=os.getenv("UI_LOG_FILE", "admin_ui.log"),
    level=os.getenv("UI_LOG_LEVEL", "DEBUG")
)
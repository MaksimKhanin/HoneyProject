# db/queries.py
"""
SQL-запросы для DBManager.
Параметризованные запросы — чтобы нас не ебали хакеры и SQL-инъекции.
"""

# ===== INSTRUMENTS =====
UPSERT_INSTRUMENT = """
    INSERT INTO instruments 
       (uid, ticker, name, type, class_code, currency, 
        exchange, min_price_increment, lot, api_trade_available, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (uid) DO UPDATE SET
        ticker = EXCLUDED.ticker,
        name = EXCLUDED.name,
        type = EXCLUDED.type,
        class_code = EXCLUDED.class_code,
        currency = EXCLUDED.currency,
        exchange = EXCLUDED.exchange,
        min_price_increment = EXCLUDED.min_price_increment,
        lot = EXCLUDED.lot,
        api_trade_available = EXCLUDED.api_trade_available,
        updated_at = NOW()
"""

GET_INSTRUMENT_BY_TICKER = """
    SELECT uid, ticker, name, type, class_code, currency, exchange, lot, updated_at
    FROM instruments
    WHERE ticker = %s
"""

GET_UID_BY_TICKER = """
    SELECT uid FROM instruments WHERE ticker = %s
"""

GET_ALL_INSTRUMENTS = """
    SELECT uid, ticker, name, type, class_code, currency, 
           exchange, min_price_increment, lot, api_trade_available, updated_at
    FROM instruments
    ORDER BY ticker ASC
"""

# ===== CANDLES =====
UPSERT_CANDLES_BATCH = """
    INSERT INTO candles 
    (ticker, timeframe, time, open, high, low, close, volume)
    VALUES %s
    ON CONFLICT (ticker, timeframe, time) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume
"""

GET_LAST_CANDLE_DATE = """
    SELECT MAX(time) FROM candles
    WHERE ticker = %s AND timeframe = %s
"""

GET_CANDLES_COUNT = """
    SELECT COUNT(*) FROM candles
    WHERE ticker = %s AND timeframe = %s
"""

GET_DATE_RANGE = """
    SELECT MIN(time), MAX(time) FROM candles
    WHERE ticker = %s AND timeframe = %s
"""

GET_RECENT_CANDLES = """
    SELECT time, open, high, low, close, volume FROM candles
    WHERE ticker = %s AND timeframe = %s
    ORDER BY time DESC
    LIMIT %s
"""

# ===== SIGNALS =====
CREATE_SIGNALS_TABLE = """
    CREATE TABLE IF NOT EXISTS signals (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        timeframe VARCHAR(10) NOT NULL,
        strategy VARCHAR(50) NOT NULL,
        signal VARCHAR(10) NOT NULL,
        price NUMERIC(20, 8) NOT NULL,
        candle_time TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB DEFAULT '{}',
        UNIQUE(ticker, timeframe, strategy, candle_time)
    );
    CREATE INDEX IF NOT EXISTS idx_signals_ticker_tf 
        ON signals(ticker, timeframe);
    CREATE INDEX IF NOT EXISTS idx_signals_time 
        ON signals(candle_time DESC);
    CREATE INDEX IF NOT EXISTS idx_signals_active 
        ON signals(ticker, timeframe, strategy) WHERE signal IN ('BUY', 'SELL');
"""

UPSERT_SIGNAL = """
    INSERT INTO signals (ticker, timeframe, strategy, signal, price, candle_time, metadata)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (ticker, timeframe, strategy, candle_time) 
    DO UPDATE SET 
        signal = EXCLUDED.signal,
        price = EXCLUDED.price,
        created_at = CURRENT_TIMESTAMP
    RETURNING id
"""

GET_RECENT_SIGNALS = """
    SELECT ticker, timeframe, strategy, signal, price, candle_time, created_at, metadata
    FROM signals
    WHERE signal IN ('BUY', 'SELL', 'CLOSE_BUY', 'CLOSE_SELL', 'CLOSE_ALL')
    ORDER BY candle_time DESC
    LIMIT %s
"""

# ===== SCHEMA =====
CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS {schema}"
GRANT_SCHEMA = "GRANT ALL ON SCHEMA {schema} TO {user}"
SET_SEARCH_PATH = "ALTER USER {user} SET search_path TO {schema}, public"

# ===== INSTRUMENT_CONFIG =====

# Создание таблицы конфигурации инструментов
CREATE_INSTRUMENT_CONFIG_TABLE = """
CREATE TABLE IF NOT EXISTS instrument_config (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,

    -- Параметры загрузки
    history_depth_days INTEGER DEFAULT 365,
    update_interval_minutes INTEGER DEFAULT 60,

    -- Параметры стратегии
    strategy_name VARCHAR(50) DEFAULT 'none',
    strategy_window INTEGER DEFAULT 20,
    strategy_params JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_instrument_config_enabled 
    ON instrument_config(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_instrument_config_strategy 
    ON instrument_config(strategy_name) WHERE strategy_name != 'none';
"""

# Получить все активные конфигурации (сортировка по приоритету)
GET_ENABLED_INSTRUMENT_CONFIGS = """
SELECT 
    ticker, timeframe, enabled,
    history_depth_days, update_interval_minutes,
    strategy_name, strategy_window, strategy_params,
    created_at, updated_at
FROM instrument_config
WHERE enabled = TRUE
ORDER BY ticker ASC, timeframe ASC
"""

# Получить конфигурацию по тикеру и таймфрейму
GET_INSTRUMENT_CONFIG = """
SELECT 
    ticker, timeframe, enabled,
    history_depth_days, update_interval_minutes,
    strategy_name, strategy_window, strategy_params,
    created_at, updated_at
FROM instrument_config
WHERE enabled = TRUE 
AND ticker = %s 
AND timeframe = %s
ORDER BY ticker ASC, timeframe ASC
"""

# Вставить или обновить конфигурацию (UPSERT)
UPSERT_INSTRUMENT_CONFIG = """
INSERT INTO instrument_config (
    ticker, timeframe, enabled,
    history_depth_days, update_interval_minutes,
    strategy_name, strategy_window, strategy_params,
    live_trading_enabled, 
    updated_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
ON CONFLICT (ticker, timeframe) DO UPDATE SET
    enabled = EXCLUDED.enabled,
    history_depth_days = EXCLUDED.history_depth_days,
    update_interval_minutes = EXCLUDED.update_interval_minutes,
    strategy_name = EXCLUDED.strategy_name,
    strategy_window = EXCLUDED.strategy_window,
    strategy_params = EXCLUDED.strategy_params,
    live_trading_enabled = EXCLUDED.live_trading_enabled,
    updated_at = CURRENT_TIMESTAMP
"""

# Обновить только флаг enabled
UPDATE_INSTRUMENT_ENABLED = """
UPDATE instrument_config 
SET enabled = %s, updated_at = CURRENT_TIMESTAMP
WHERE ticker = %s AND timeframe = %s
"""

# Удалить конфигурацию
DELETE_INSTRUMENT_CONFIG = """
DELETE FROM instrument_config WHERE ticker = %s AND timeframe = %s
"""

# Получить статистику: сколько инструментов активно/неактивно
GET_INSTRUMENT_CONFIG_STATS = """
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE enabled = TRUE) as enabled_count,
    COUNT(*) FILTER (WHERE strategy_name != 'none') as with_strategy
FROM instrument_config
"""

# Удалить все конфиги по тикеру (для delete_ticker)
DELETE_INSTRUMENT_CONFIG_BY_TICKER = """
DELETE FROM instrument_config 
WHERE ticker = %s
"""

# Удалить связанные сигналы при удалении инструмента (опционально, каскад)
DELETE_SIGNALS_BY_TICKER_TF = """
DELETE FROM signals 
WHERE ticker = %s AND timeframe = %s
"""

CREATE_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    time TIMESTAMP NOT NULL,  -- FK к candles(time), но без внешнего ключа для гибкости
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metrics JSONB DEFAULT '{}',  -- nested метрики: {"rsi": 45.2, "sma_20": 315.5, ...}

    -- Уникальность: одна запись на свечу + инструмент
    UNIQUE(ticker, timeframe, time)
);

-- Индексы для быстрых выборок
CREATE INDEX IF NOT EXISTS idx_metrics_lookup 
    ON metrics(ticker, timeframe, time DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_updated 
    ON metrics(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_json 
    ON metrics USING GIN(metrics);  -- для поиска по ключам внутри JSON
"""

# ===== METRICS =====

UPSERT_METRICS = """
INSERT INTO metrics (ticker, timeframe, time, metrics)
VALUES (%s, %s, %s, %s)
ON CONFLICT (ticker, timeframe, time) DO UPDATE SET
    metrics = EXCLUDED.metrics,
    updated_at = CURRENT_TIMESTAMP
"""

GET_METRICS_BY_TICKER_TF = """
SELECT time, metrics, updated_at 
FROM metrics 
WHERE ticker = %s AND timeframe = %s 
ORDER BY time DESC LIMIT %s
"""

GET_LATEST_METRICS = """
SELECT DISTINCT ON (ticker, timeframe) 
    ticker, timeframe, time, metrics, updated_at
FROM metrics 
WHERE (%s = 'all' OR timeframe = %s)
ORDER BY ticker, timeframe, time DESC
LIMIT %s
"""
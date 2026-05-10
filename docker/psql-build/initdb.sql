
CREATE SCHEMA IF NOT EXISTS tink;


CREATE TABLE IF NOT EXISTS tink.candles (
    -- Составной PRIMARY KEY вместо id
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    time TIMESTAMP NOT NULL,
    -- Данные свечи
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,

    -- Ограничения
    PRIMARY KEY (ticker, timeframe, time)
);

-- Индексы для быстрых запросов
CREATE INDEX IF NOT EXISTS idx_candles_ticker_time ON tink.candles(ticker, time);
CREATE INDEX IF NOT EXISTS idx_candles_time_only ON tink.candles(time);


CREATE TABLE IF NOT EXISTS tink.instruments (
    uid TEXT PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT,
    type TEXT,
    class_code TEXT,
    currency TEXT,
    exchange TEXT,
    min_price_increment NUMERIC,
    lot NUMERIC,
    trading_status TEXT,
    api_trade_available TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_instruments_ticker ON tink.instruments(ticker);


CREATE TABLE IF NOT EXISTS tink.signals (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    strategy TEXT NOT NULL,
    signal TEXT NOT NULL,
    price NUMERIC NOT NULL,
    candle_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE(ticker, timeframe, strategy, candle_time)
);
CREATE INDEX IF NOT EXISTS idx_signals_ticker_tf
    ON tink.signals(ticker, timeframe);
CREATE INDEX IF NOT EXISTS idx_signals_time
    ON tink.signals(candle_time DESC);


 ALTER TABLE tink.instrument_config
ADD COLUMN IF NOT EXISTS live_trading_enabled BOOLEAN DEFAULT FALSE;

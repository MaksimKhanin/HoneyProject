
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
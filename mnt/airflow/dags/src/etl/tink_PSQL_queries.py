
INSERT_PORTFOLIO_JSON = """
    INSERT INTO tink.portfolio
        SELECT *
        FROM json_populate_recordset(NULL::tink.portfolio, %s)
    ON CONFLICT ("figi", "ticker") DO UPDATE SET
        (
            "isin",
            "instrumentType",
            "balance",
            "lots",
            "expectedYield",
            "averagePositionPrice",
            "name",
            "blocked"
        )
        =
        (
        EXCLUDED."isin",
        EXCLUDED."instrumentType",
        EXCLUDED."balance",
        EXCLUDED."lots",
        EXCLUDED."expectedYield",
        EXCLUDED."averagePositionPrice",
        EXCLUDED."name",
        EXCLUDED."blocked"
        );
"""

INSERT_SECURITY_JSON = """
    INSERT INTO tink.security
        SELECT * 
        FROM json_populate_recordset(NULL::tink.security, %s)
    ON CONFLICT ("figi", "ticker") DO UPDATE SET
        (
            "isin",
            "minPriceIncrement",
            "lot",
            "currency",
            "name",
            "type"
        )
        =
        (
        EXCLUDED."isin",
        EXCLUDED."minPriceIncrement",
        EXCLUDED."lot",
        EXCLUDED."currency",
        EXCLUDED."name",
        EXCLUDED."type"
        );
"""

INSERT_CANDLE_JSON = """
    INSERT INTO tink.candles_{tf}
        SELECT * 
        FROM json_populate_recordset(NULL::tink.candles_{tf}, %s)
    ON CONFLICT ("figi", "time") DO UPDATE SET
        (
            "o",
            "c",
            "h",
            "l",
            "v",
            "time",
            "figi"
        )
        =
        (
            EXCLUDED."o",
            EXCLUDED."c",
            EXCLUDED."h",
            EXCLUDED."l",
            EXCLUDED."v",
            EXCLUDED."time",
            EXCLUDED."figi"
        );
"""

GET_LAST_CANDLE_DT = """
    SELECT
        MAX(time)
    FROM tink.candles_{tf}
    WHERE figi = %s;         
"""

GET_FIGI_LIST = """
    SELECT 
        figi,
        ticker
    FROM tink.security;
"""

GET_LAST_CANDLE_UPDATE = """
    SELECT 
        MAX("last_update")
    FROM sys_upd.tink_candle
    WHERE 1=1
        AND "figi" = %s
        AND "ticker" = %s
        AND "interval" = %s;
"""

UPDATE_TINK_LAST_CANDLE_UPDATE = """
    INSERT INTO sys_upd.tink_candle VALUES
    (%s, %s, %s, %s)
    ON CONFLICT ("figi", "ticker", "interval") DO UPDATE SET
    "last_update" = EXCLUDED."last_update";
"""
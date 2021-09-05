GET_DAILY_RETURN = """
    SELECT 
        date, 
        ticker, 
        daily_return
    FROM anl.daily_return;
"""


QUERY_STATEMENTS = """
SELECT *
FROM anl.fund_statements
WHERE period = 'Quarter'
    AND date >= %s
    AND currency = %s;
"""

QUERY_INSERT_MODEL = """
    INSERT INTO ml.model_list VALUES
    (%s, %s)
    ON CONFLICT ("model_id") DO UPDATE SET
    "pickle" = EXCLUDED."pickle";
"""

QUERY_GET_MODEL = """
    SELECT
        pickle
    FROM ml.model_list
    WHERE model_id = %s;
"""

QUERY_TREND_LOCATOR_FEATURES = """
CREATE TEMPORARY TABLE IF NOT EXISTS source_feature_table AS (
  SELECT
    date,

    MAX_5_vol / NULLIF(LAG(MAX_5_vol, 5) OVER ticker_part, 0) - 1 AS MAX_5_l_1_vol,
    MIN_5_vol / NULLIF(LAG( MIN_5_vol, 10) OVER ticker_part, 0) - 1 AS  MIN_5_l_2_vol,
    
    MIN_12_vol / NULLIF(LAG( MIN_12_vol, 12) OVER ticker_part, 0) - 1 AS  MIN_12_l_1_vol,
    MAX_12_vol / NULLIF(LAG(MAX_12_vol, 24) OVER ticker_part, 0) - 1 AS MAX_12_l_2_vol,

    low / NULLIF(MIN_5_low,0) - 1 AS low_5_MIN_ratio,
    low / NULLIF(MIN_12_low,0) - 1 AS low_12_MIN_ratio,

    MIN_5_low / NULLIF(LAG(MIN_5_low, 5) OVER ticker_part, 0) - 1 AS MIN_5_l_1_low,
    MIN_5_low / NULLIF(LAG(MIN_5_low, 10) OVER ticker_part, 0) - 1 AS  MIN_5_l_2_low,
    
    MIN_12_low / NULLIF(LAG(MIN_12_low, 12) OVER ticker_part, 0) - 1 AS MIN_12_l_1_low,
    MIN_12_low / NULLIF(LAG(MIN_12_low, 24) OVER ticker_part, 0) - 1 AS  MIN_12_l_2_low,
		
    high / NULLIF(MAX_5_high,0) - 1 AS high_5_MAX_ratio,
    high / NULLIF(MAX_12_high,0) - 1 AS high_12_MAX_ratio,

    MAX_5_high / NULLIF(LAG(MAX_5_high, 5) OVER ticker_part, 0) - 1 AS MAX_5_l_1_high,
    MAX_5_high / NULLIF(LAG(MAX_5_high, 10) OVER ticker_part, 0) - 1 AS MAX_5_l_2_high,
    
    MAX_12_high / NULLIF(LAG(MAX_12_high, 12) OVER ticker_part, 0) - 1 AS MAX_12_l_1_high,
    MAX_12_high / NULLIF(LAG(MAX_12_high, 24) OVER ticker_part, 0) - 1 AS MAX_12_l_2_high,

    (close - ROLLING_MEAN_5_close) / NULLIF(STD_5_close, 0) AS z_5_close,
    (close - ROLLING_MEAN_12_close) /  NULLIF(STD_12_close,0) AS z_12_close,
    (close - ROLLING_MEAN_50_close) /  NULLIF(STD_50_close,0) AS z_50_close,

    (close - ROLLING_MEAN_5_close) / NULLIF(STD_5_close, 0) - LAG((close - ROLLING_MEAN_5_close) /  NULLIF(STD_5_close,0), 5) OVER ticker_part AS z_5_close_l_1,
    (close - ROLLING_MEAN_12_close) / NULLIF(STD_12_close, 0) - LAG((close - ROLLING_MEAN_12_close) /  NULLIF(STD_12_close,0), 5) OVER ticker_part AS z_12_close_l_1,
    (close - ROLLING_MEAN_50_close) / NULLIF(STD_50_close, 0) - LAG((close - ROLLING_MEAN_50_close) /  NULLIF(STD_50_close,0), 5) OVER ticker_part AS z_50_close_l_1,

    close / NULLIF(MAX_5_high,0) - 1 AS close_5_MAX_ratio,
    close / NULLIF(MAX_12_high,0) - 1 AS close_12_MAX_ratio,

    close / NULLIF(MIN_5_low,0) - 1 AS close_5_MIN_ratio,
    close / NULLIF(MIN_12_low,0) - 1 AS close_12_MIN_ratio,

    close / NULLIF(LAG(MAX_5_high, 5) OVER ticker_part, 0) - 1 AS MAX_5_l_1_close,
    close / NULLIF(LAG(MIN_5_low, 10) OVER ticker_part, 0) - 1 AS MIN_5_l_2_close,
    
    close / NULLIF(LAG(MAX_12_high, 12) OVER ticker_part, 0) - 1 AS MAX_12_l_1_close,
    close / NULLIF(LAG(MIN_12_low, 24) OVER ticker_part, 0) - 1 AS MIN_12_l_2_close,

    ROLLING_MEAN_5_close /NULLIF(LAG(ROLLING_MEAN_5_close,5) OVER ticker_part, 0) - 1 AS mean_5_l_5_ratio,
    ROLLING_MEAN_12_close /NULLIF(LAG(ROLLING_MEAN_12_close,12) OVER ticker_part ,0) - 1 AS mean_12_l_12_ratio,

    (LEAD(ROLLING_MEAN_5_close, 6) OVER ticker_part / ROLLING_MEAN_5_close) > 1 AS TARGET_5_class ,
    (LEAD(ROLLING_MEAN_5_close, 6) OVER ticker_part / ROLLING_MEAN_5_close) AS TARGET_5_reg ,
    (LEAD(ROLLING_MEAN_12_close, 13) OVER ticker_part / ROLLING_MEAN_12_close) > 1 AS TARGET_12_class ,
    (LEAD(ROLLING_MEAN_12_close, 13) OVER ticker_part / ROLLING_MEAN_12_close) AS TARGET_12_reg ,

    ROLLING_MEAN_5_close / ROLLING_MEAN_12_close AS mean_5_12_ratio,
    
    MAX_5_high / MAX_12_high AS high_5_12_ratio,
    MIN_5_low / MIN_12_low AS low_5_12_ratio,

    ticker
    FROM (
        SELECT
            DATE(cndl.time) AS date,
            cndl.c AS close,
            cndl.h AS high,
            cndl.l AS low,
            cndl.o AS open,
            cndl.v AS volume,

            MAX(cndl.v) OVER ticker_part_5 AS MAX_5_vol,
            MAX(cndl.v) OVER ticker_part_12 AS MAX_12_vol,

            MIN(cndl.v) OVER ticker_part_5 AS MIN_5_vol,
            MIN(cndl.v) OVER ticker_part_12 AS MIN_12_vol,

            MAX(cndl.h) OVER ticker_part_5 AS MAX_5_high,
            MAX(cndl.h) OVER ticker_part_12 AS MAX_12_high,

            MIN(cndl.l) OVER ticker_part_5 AS MIN_5_low,
            MIN(cndl.l) OVER ticker_part_12 AS MIN_12_low,

            AVG(cndl.c) OVER ticker_part_5 AS ROLLING_MEAN_5_close,
            AVG(cndl.c) OVER ticker_part_12 AS ROLLING_MEAN_12_close,
            AVG(cndl.c) OVER ticker_part_50 AS ROLLING_MEAN_50_close,

            STDDEV_SAMP(cndl.c) OVER ticker_part_5 AS STD_5_close,
            STDDEV_SAMP(cndl.c) OVER ticker_part_12 AS STD_12_close,
            STDDEV_SAMP(cndl.c) OVER ticker_part_50 AS STD_50_close,     

            sec.ticker
        FROM tink.candles_day AS cndl
            INNER JOIN tink.security AS sec 
                ON sec.figi = cndl.figi
        WHERE
           DATE(cndl.time) >= NOW() - INTERVAL '300 DAY'
        WINDOW 
          ticker_part_5 AS (PARTITION BY ticker ORDER BY cndl.time ROWS BETWEEN 5 PRECEDING AND CURRENT ROW),
		      ticker_part_12 AS (PARTITION BY ticker ORDER BY cndl.time ROWS BETWEEN 12 PRECEDING AND CURRENT ROW),
		      ticker_part_50 AS (PARTITION BY ticker ORDER BY cndl.time ROWS BETWEEN 50 PRECEDING AND CURRENT ROW),
		      ticker_part AS (PARTITION BY ticker ORDER BY cndl.time)
        ) AS src
	WINDOW ticker_part AS (PARTITION BY ticker ORDER BY date)
);

CREATE TEMPORARY TABLE IF NOT EXISTS mean_pos_stock_return AS
(
	SELECT
		ticker,
		AVG(TARGET_12_reg) AS mean_pos_return
	FROM source_feature_table
	WHERE TARGET_12_reg > 1
	GROUP BY ticker
);

CREATE TEMPORARY TABLE IF NOT EXISTS mean_neg_stock_return AS
(
	SELECT
		ticker,
		AVG(TARGET_12_reg) AS mean_neg_return
	FROM source_feature_table
	WHERE TARGET_12_reg < 1
	GROUP BY ticker
);

SELECT
	main.*,
	pos.mean_pos_return,
	neg.mean_neg_return
FROM source_feature_table as main
	LEFT JOIN mean_pos_stock_return AS pos ON main.ticker = pos.ticker
	LEFT JOIN mean_neg_stock_return AS neg ON main.ticker = neg.ticker
"""
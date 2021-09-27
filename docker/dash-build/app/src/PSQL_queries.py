# GET_RAW_DAILY_PRICES = """
#     SELECT
#         EXTRACT(EPOCH FROM date) AS timestamp,
#         DATE(date) AS date,
#         ticker,
#         open,
#         high,
#         low,
#         close,
#         currency,
#         sector,
#         industry,
#         name,
#         ROUND((close /LAG(close, 1) OVER (
#                         PARTITION BY ticker
#                         ORDER BY date
#                         ) - 1) * 100, 4) AS daily_return
#     FROM anl.daily_return
#     WHERE date BETWEEN %s AND %s
#     ORDER BY date ASC;
# """
#
# GET_RAW_CANDLES_2 = """
#     SELECT
#         EXTRACT(EPOCH FROM date) AS timestamp,
#         DATE(date) AS date,
#         ticker,
#         open,
#         high,
#         low,
#         close,
#         currency,
#         sector,
#         industry,
#         name,
#         ROUND((close /LAG(close, 1) OVER (
#                         PARTITION BY ticker
#                         ORDER BY date
#                         ) - 1) * 100, 4) AS daily_return
#     FROM anl.daily_return
#     WHERE date >= NOW() - INTERVAL '{} DAY'
#     ORDER BY date ASC;
# """

GET_RAW_CANDLES = """
    SELECT 
        timestamp, 
        date, 
        ticker, 
        open, 
        high, 
        low,
        close,
        sector,
        industry,
        z_50_close,
        return_pred,
        prob_pred,
        cluster
    FROM anl.dash_main;"""

GET_RAW_DAILY_RETURN = """
    SELECT 
        timestamp, 
        date, 
        ticker, 
        daily_return,               
        currency,
        sector,
        industry,
        name,
        cluster
    FROM anl.dash_main;"""

GET_PCA = """
    SELECT
        DISTINCT
            pca_loading_0,
            pca_loading_1,
            pca_loading_2,
            ticker,
            currency,
            sector,
            industry,
            cluster
    FROM anl.dash_main;"""

GET_CLOSE_PRICES = """
    SELECT
        date,
        timestamp,
        ticker,
        close
    FROM anl.dash_main;"""

GET_EARNINGS_CALENDAR = """
    SELECT 
        *
    FROM anl.earnings_calendar;
"""

GET_COMPANY_STTMNTS = """
    SELECT *
    FROM anl.fund_statements
    WHERE date >= NOW() - INTERVAL '1500 DAY'
    ORDER BY date ASC;
"""

GET_STTMNTS_SCORES = """
    SELECT *
    FROM ml.stmnt_scores
    ORDER BY date ASC;
"""

GET_STTMNTS_SECTOR_SCORES = """
	SELECT
		sector,
		ROUND(AVG(statement_score), 4) AS avg_score
	FROM ml.stmnt_scores
	WHERE date >= NOW() - INTERVAL '90 DAY'
	GROUP BY sector;
"""

GET_ML_SCORES_FOR_TODAY = """
DROP TABLE IF EXISTS last_stmnt_score;
CREATE TEMPORARY TABLE IF NOT EXISTS last_stmnt_score AS (
	SELECT
	  main.symbol,
	  main.statement_score
	 FROM ml.stmnt_scores AS main
		INNER JOIN (
		 SELECT
			 symbol,
			 MAX(date) AS date
		 FROM ml.stmnt_scores
		 GROUP BY symbol
		 ) AS src ON src.symbol = main.symbol 
			AND src.date = main.date
);

	SELECT
		dr.date, 
		dr.ticker,
		dr.name,					
		dr.sector,
		dr.industry,
		dr.z_50_close,
		
		cl.cluster,
		
		trend.return_pred - 1 AS return_pred,
		trend.prob_pred,
		ROUND(dr.close * trend.return_pred, 5) AS target_price,
		stmnt.statement_score
		
	FROM anl.daily_return AS dr
		INNER JOIN (
		SELECT
			ticker,
			MAX(date) as date
		FROM anl.daily_return
		GROUP BY ticker 
		) AS maxdt 
			ON dr.date=maxdt.date AND dr.ticker=maxdt.ticker
		LEFT JOIN anl.ml_ticker_clustering AS cl
			ON dr.ticker = cl.ticker
		LEFT JOIN ml.trend_locator AS trend
			ON dr.ticker = trend.ticker AND dr.date = trend.date
		LEFT JOIN last_stmnt_score AS stmnt ON dr.ticker = stmnt.symbol;
"""

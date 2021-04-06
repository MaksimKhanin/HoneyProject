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
        close
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

#
# GET_COMPANY_BALANCESHEET = """
#     SELECT
#         *
#     FROM anl.balance_sheet
#     WHERE date >= NOW() - INTERVAL '7300 DAY'
#     ORDER BY date ASC;"""
#
# GET_COMPANY_CASHFLOW = """
#     SELECT
#         *
#     FROM anl.cash_flows
#     WHERE date >= NOW() - INTERVAL '7300 DAY'
#     ORDER BY date ASC;"""
#
# GET_COMPANY_INCOMESTATEMENT = """
#     SELECT
#         *
#     FROM anl.income_statement
#     WHERE date >= NOW() - INTERVAL '7300 DAY'
#     ORDER BY date ASC;"""
#
# GET_COMPANY_KEYMETRICS = """
#     SELECT
#         *
#     FROM anl.key_metrics
#     WHERE date >= NOW() - INTERVAL '7300 DAY'
#     ORDER BY date ASC;"""

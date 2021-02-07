GET_RAW_DAILY_PRICES = """
    SELECT *
    FROM anl.daily_return
    WHERE date >= NOW() - INTERVAL '730 DAY'
    ORDER BY date ASC;
"""

GET_RAW_CANDLES = """
    SELECT 
        EXTRACT(EPOCH FROM date) AS timestamp, 
        DATE(date) AS date, 
        ticker, 
        open, 
        high, 
        low,
        close
    FROM anl.daily_return
    WHERE date >= NOW() - INTERVAL '730 DAY'
    ORDER BY date ASC;"""

GET_RAW_DAILY_RETURN = """
    SELECT 
        EXTRACT(EPOCH FROM date) AS timestamp, 
        DATE(date) AS date, 
        ticker, 
        ROUND((close /LAG(close, 1) OVER (
                            PARTITION BY ticker
                            ORDER BY date
                            ) - 1) * 100, 4) AS daily_return,               
        currency,
        sector,
        industry,
        name
    FROM anl.daily_return
    WHERE date >= NOW() - INTERVAL '730 DAY'
    ORDER BY date ASC;"""

GET_COMPANY_BALANCESHEET = """
    SELECT 
        *
    FROM anl.balance_sheet
    WHERE date >= NOW() - INTERVAL '7300 DAY'
    AND symbol = %s
    ORDER BY date ASC;"""

GET_COMPANY_CASHFLOW = """
    SELECT 
        *
    FROM anl.cash_flows
    WHERE date >= NOW() - INTERVAL '7300 DAY'
    AND symbol = %s
    ORDER BY date ASC;"""

GET_COMPANY_INCOMESTATEMENT = """
    SELECT 
        *
    FROM anl.income_statement
    WHERE date >= NOW() - INTERVAL '7300 DAY'
    AND symbol = %s
    ORDER BY date ASC;"""

GET_COMPANY_KEYMETRICS = """
    SELECT 
        *
    FROM anl.key_metrics
    WHERE date >= NOW() - INTERVAL '7300 DAY'
    AND symbol = %s
    ORDER BY date ASC;"""

GET_DAILY_RETURN = """
    SELECT 
        date, 
        ticker, 
        daily_return
    FROM anl.daily_return;
"""

# QUERY_PROFILES = """
# SELECT symbol,
#        sector
#     FROM fmp.company_profile
#     WHERE currency = %s
# """



QUERY_STATEMENTS = """
SELECT *
FROM anl.fund_statements
WHERE period = 'Quarter'
AND date >= %s
AND currency = %s;
"""
# QUERY_BL = """
# SELECT *
#     FROM anl.balance_sheet
#     WHERE period = 'Quarter'
#     AND date >= %s
# """
# QUERY_CF = """
# SELECT *
#     FROM anl.cash_flows
#     WHERE period = 'Quarter'
#     AND date >= %s
# """
#
# QUERY_INC = """
# SELECT *
#     FROM anl.income_statement
#     WHERE period = 'Quarter'
#     AND date >= %s
# """
#
# QUERY_KM = """
# SELECT *
#     FROM anl.key_metrics
#     WHERE period = 'Quarter'
#     AND date >= %s
# """
#
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

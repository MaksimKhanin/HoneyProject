from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from src.ml import priceClustering
from src.ml import stmnt_analyzer
from src.etl import fmp_etl

SLACK_CONN_ID = 'slack-honeyTradingTech'

slack_channel = BaseHook.get_connection(SLACK_CONN_ID).login
slack_token = BaseHook.get_connection(SLACK_CONN_ID).password

default_args = {
            "owner": "airflow",
            "start_date": datetime(2020, 1, 1),
            "depends_on_past": False,
            "email_on_failure": False,
            "email_on_retry": False,
            "email": "youremail@host.com",
            "retries": 5,
            "retry_delay": timedelta(minutes=10)
        }

def update_ticker_clusters():
    priceClustering.upload_clustering_df()

def update_stmnt_scores():
    stmnt_analyzer.upload_stmnt_scores_df("stmnt_binary_class")

def update_earnings_calendar():
    fmp_etl.etl_earnings_calendar()

with DAG(dag_id="anl_update_daily", schedule_interval=None, default_args=default_args, catchup=False) as dag:

    create_dash_main_table = PostgresOperator(
        task_id="create_dash_main_table",
        sql="""
            CREATE TABLE IF NOT EXISTS anl.dash_main AS (
            SELECT
                    dr.timestamp, 
                    dr.date, 
                    dr.ticker, 
                    dr.open, 
                    dr.high, 
                    dr.low,
                    dr.close,
                    dr.daily_return,               
                    dr.currency,
                    dr.sector,
                    dr.industry,
                    dr.name,
                    cl.pca_loading_0,
                    cl.pca_loading_1,
                    cl.pca_loading_2,
                    cl.cluster
                FROM anl.daily_return AS dr
                    LEFT JOIN anl.ml_ticker_clustering AS cl
                        ON dr.ticker = cl.ticker
                WHERE date >= NOW() - INTERVAL '730 DAY'
                ORDER BY date ASC          
            );
        """
    )

    drop_dash_main_table = PostgresOperator(
        task_id="drop_dash_main_table",
        sql="DROP TABLE IF EXISTS anl.dash_main;"
    )

    cluster_tickers = PythonOperator(
        task_id="cluster_tickers",
        python_callable=update_ticker_clusters
    )

    upload_stmnt_scores = PythonOperator(
        task_id="upload_stmnt_scores",
        python_callable=update_stmnt_scores
    )

    earnings_calendar_update = PythonOperator(
        task_id="earnings_calendar_update",
        python_callable=update_earnings_calendar
    )

    anl_drop_calendar = PostgresOperator(
        task_id="anl_drop_calendar",
        sql="DROP TABLE IF EXISTS anl.earnings_calendar;"
    )

    anl_create_calendar = PostgresOperator(
        task_id="anl_create_calendar",
        sql="""
        CREATE TABLE IF NOT EXISTS anl.earnings_calendar AS (
            SELECT
                CAST(cal."date" AS DATE) AS date,
                cal."symbol",
                cal."time",
                cal."eps",
                cal."epsEstimated",
                cal."revenue",
                cal."revenueEstimated"
            FROM fmp.earnings_calendar AS cal
                INNER JOIN fmp.company_profile AS prof 
                    ON cal.symbol = prof.symbol
            WHERE CAST(cal."date" AS DATE) > NOW() - INTERVAL '730 DAY'
            ORDER BY date ASC  
        );
        """
    )

    truncate_clusters = PostgresOperator(
        task_id="truncate_clusters",
        sql="TRUNCATE anl.ml_ticker_clustering;"
    )

    truncate_stmnt_scores = PostgresOperator(
        task_id="truncate_stmnt_scores",
        sql="TRUNCATE ml.stmnt_scores;"
    )


    drop_daily_return = PostgresOperator(
        task_id="drop_daily_return",
        sql="DROP TABLE IF EXISTS anl.daily_return;"
    )

    create_daily_return = PostgresOperator(
        task_id="create_daily_return",
        sql="""CREATE TABLE IF NOT EXISTS anl.daily_return AS (
                SELECT
                    EXTRACT(EPOCH FROM date) AS timestamp, 
                    DATE(date) AS date, 
                    ticker, 
                    open, 
                    high, 
                    low,
                    close,
                    ROUND((close /LAG(close, 1) OVER (
                                        PARTITION BY ticker
                                        ORDER BY date
                                        ) - 1) * 100, 4) AS daily_return,               
                    currency,
                    sector,
                    industry,
                    name
                FROM (
                            SELECT
                                cndl.time AS date,
                                cndl.c AS close,
                                cndl.h AS high,
                                cndl.l AS low,
                                cndl.o AS open,
                                cndl.v AS volume,
                                sec.ticker,
                                sec.name,
                                sec.currency,                        
                                coalesce(prf.sector, 'other') AS sector,
                                coalesce(prf.industry, 'other') AS industry                     
                            FROM tink.candles_day AS cndl
                                INNER JOIN tink.security AS sec 
                                    ON sec.figi = cndl.figi
                                INNER JOIN fmp.tink_sec_x_fmp_prof AS tink_x_fmp
                                    ON sec.ticker = tink_x_fmp.ticker
                                LEFT JOIN fmp.company_profile AS prf
                                    ON tink_x_fmp.fmp_symbol = prf.symbol
                            UNION ALL
                            SELECT
                                fcndl.time as date,
                                fcndl.close,
                                fcndl.high,
                                fcndl.low,
                                fcndl.open,
                                fcndl.volume,
                                fcndl.ticker,
                                fsec.name,
                                fsec.currency,
                                'indicator' AS sector,
                                'indicator' AS industry
                            FROM fmp.candles_day AS fcndl
                                INNER JOIN fmp.security AS fsec
                                    ON fcndl.ticker = fsec.ticker ) AS stg
                );
            """
    )

    drop_balance_sheet = PostgresOperator(
        task_id="drop_balance_sheet",
        sql="DROP TABLE IF EXISTS anl.balance_sheet;"
    )

    create_balance_sheet = PostgresOperator(
        task_id="create_balance_sheet",
        sql="""CREATE TABLE IF NOT EXISTS anl.balance_sheet AS (
                SELECT 
                    COALESCE(
                        GET_TXT_DATE("date"), 
                        GET_TXT_DATE("fillingDate"), 
                        GET_TXT_DATE("acceptedDate")) AS date,
                    'Year' as period, 
                    "symbol",
                    "cashAndCashEquivalents",
                    "shortTermInvestments",
                    "cashAndShortTermInvestments",
                    "netReceivables",
                    "inventory",
                    "otherCurrentAssets",
                    "totalCurrentAssets",
                    "propertyPlantEquipmentNet",
                    "goodwill",
                    "intangibleAssets",
                    "goodwillAndIntangibleAssets",
                    "longTermInvestments",
                    "taxAssets",
                    "otherNonCurrentAssets",
                    "totalNonCurrentAssets",
                    "otherAssets",
                    "totalAssets",
                    "accountPayables",
                    "shortTermDebt",
                    "taxPayables",
                    "deferredRevenue",
                    "otherCurrentLiabilities",
                    "totalCurrentLiabilities",
                    "longTermDebt",
                    "deferredRevenueNonCurrent",
                    "deferredTaxLiabilitiesNonCurrent",
                    "otherNonCurrentLiabilities",
                    "totalNonCurrentLiabilities",
                    "otherLiabilities",
                    "totalLiabilities",
                    "commonStock",
                    "retainedEarnings",
                    "accumulatedOtherComprehensiveIncomeLoss",
                    "othertotalStockholdersEquity",
                    "totalStockholdersEquity",
                    "totalLiabilitiesAndStockholdersEquity",
                    "totalInvestments",
                    "totalDebt",
                    "netDebt"
                FROM fmp.balance_sheet_y
                UNION ALL
                SELECT 
                    COALESCE(
                        GET_TXT_DATE("date"), 
                        GET_TXT_DATE("fillingDate"), 
                        GET_TXT_DATE("acceptedDate")) AS date,
                    'Quarter' as period, 
                    "symbol",
                    "cashAndCashEquivalents",
                    "shortTermInvestments",
                    "cashAndShortTermInvestments",
                    "netReceivables",
                    "inventory",
                    "otherCurrentAssets",
                    "totalCurrentAssets",
                    "propertyPlantEquipmentNet",
                    "goodwill",
                    "intangibleAssets",
                    "goodwillAndIntangibleAssets",
                    "longTermInvestments",
                    "taxAssets",
                    "otherNonCurrentAssets",
                    "totalNonCurrentAssets",
                    "otherAssets",
                    "totalAssets",
                    "accountPayables",
                    "shortTermDebt",
                    "taxPayables",
                    "deferredRevenue",
                    "otherCurrentLiabilities",
                    "totalCurrentLiabilities",
                    "longTermDebt",
                    "deferredRevenueNonCurrent",
                    "deferredTaxLiabilitiesNonCurrent",
                    "otherNonCurrentLiabilities",
                    "totalNonCurrentLiabilities",
                    "otherLiabilities",
                    "totalLiabilities",
                    "commonStock",
                    "retainedEarnings",
                    "accumulatedOtherComprehensiveIncomeLoss",
                    "othertotalStockholdersEquity",
                    "totalStockholdersEquity",
                    "totalLiabilitiesAndStockholdersEquity",
                    "totalInvestments",
                    "totalDebt",
                    "netDebt"
                FROM fmp.balance_sheet_q
                );
            """
    )

    drop_cash_flows = PostgresOperator(
        task_id="drop_cash_flows",
        sql="DROP TABLE IF EXISTS anl.cash_flows;"
    )

    create_cash_flows = PostgresOperator(
        task_id="create_cash_flows",
        sql="""CREATE TABLE IF NOT EXISTS anl.cash_flows AS (
                SELECT
                    COALESCE(
                        GET_TXT_DATE("date"), 
                        GET_TXT_DATE("fillingDate"), 
                        GET_TXT_DATE("acceptedDate")) AS date,
                    'Year' as period, 
                    "symbol",
                    "netIncome",
                    "depreciationAndAmortization",
                    "deferredIncomeTax",
                    "stockBasedCompensation",
                    "changeInWorkingCapital",
                    "accountsReceivables",
                    "inventory",
                    "accountsPayables",
                    "otherWorkingCapital",
                    "otherNonCashItems",
                    "netCashProvidedByOperatingActivities",
                    "investmentsInPropertyPlantAndEquipment",
                    "acquisitionsNet",
                    "purchasesOfInvestments",
                    "salesMaturitiesOfInvestments",
                    "otherInvestingActivites",
                    "netCashUsedForInvestingActivites",
                    "debtRepayment",
                    "commonStockIssued",
                    "commonStockRepurchased",
                    "dividendsPaid",
                    "otherFinancingActivites",
                    "netCashUsedProvidedByFinancingActivities",
                    "effectOfForexChangesOnCash",
                    "netChangeInCash",
                    "cashAtEndOfPeriod",
                    "cashAtBeginningOfPeriod",
                    "operatingCashFlow",
                    "capitalExpenditure",
                    "freeCashFlow"
                FROM fmp.cash_flows_y
                UNION ALL
                SELECT
                    COALESCE(
                        GET_TXT_DATE("date"), 
                        GET_TXT_DATE("fillingDate"), 
                        GET_TXT_DATE("acceptedDate")) AS date,
                    'Quarter' as period, 
                    "symbol",
                    "netIncome",
                    "depreciationAndAmortization",
                    "deferredIncomeTax",
                    "stockBasedCompensation",
                    "changeInWorkingCapital",
                    "accountsReceivables",
                    "inventory",
                    "accountsPayables",
                    "otherWorkingCapital",
                    "otherNonCashItems",
                    "netCashProvidedByOperatingActivities",
                    "investmentsInPropertyPlantAndEquipment",
                    "acquisitionsNet",
                    "purchasesOfInvestments",
                    "salesMaturitiesOfInvestments",
                    "otherInvestingActivites",
                    "netCashUsedForInvestingActivites",
                    "debtRepayment",
                    "commonStockIssued",
                    "commonStockRepurchased",
                    "dividendsPaid",
                    "otherFinancingActivites",
                    "netCashUsedProvidedByFinancingActivities",
                    "effectOfForexChangesOnCash",
                    "netChangeInCash",
                    "cashAtEndOfPeriod",
                    "cashAtBeginningOfPeriod",
                    "operatingCashFlow",
                    "capitalExpenditure",
                    "freeCashFlow"
                FROM fmp.cash_flows_q
                );
            """
    )

    drop_income_statement = PostgresOperator(
        task_id="drop_income_statement",
        sql="DROP TABLE IF EXISTS anl.income_statement;"
    )

    create_income_statement = PostgresOperator(
        task_id="create_income_statement",
        sql="""CREATE TABLE IF NOT EXISTS anl.income_statement AS (
            SELECT 
                COALESCE(
                    GET_TXT_DATE("date"), 
                    GET_TXT_DATE("fillingDate"), 
                    GET_TXT_DATE("acceptedDate")) AS date,
                'Year' as period, 
                "symbol",
                "revenue",
                "costOfRevenue",
                "grossProfit",
                "grossProfitRatio",
                "researchAndDevelopmentExpenses",
                "generalAndAdministrativeExpenses",
                "sellingAndMarketingExpenses",
                "otherExpenses",
                "operatingExpenses",
                "costAndExpenses",
                "interestExpense",
                "depreciationAndAmortization",
                "ebitda",
                "ebitdaratio",
                "operatingIncome",
                "operatingIncomeRatio",
                "totalOtherIncomeExpensesNet",
                "incomeBeforeTax",
                "incomeBeforeTaxRatio",
                "incomeTaxExpense",
                "netIncome",
                "netIncomeRatio",
                "eps",
                "epsdiluted",
                "weightedAverageShsOut",
                "weightedAverageShsOutDil"
            FROM fmp.income_statement_y
            UNION ALL
            SELECT 
                COALESCE(
                    GET_TXT_DATE("date"), 
                    GET_TXT_DATE("fillingDate"), 
                    GET_TXT_DATE("acceptedDate")) AS date,
                'Quarter' as period, 
                "symbol",
                "revenue",
                "costOfRevenue",
                "grossProfit",
                "grossProfitRatio",
                "researchAndDevelopmentExpenses",
                "generalAndAdministrativeExpenses",
                "sellingAndMarketingExpenses",
                "otherExpenses",
                "operatingExpenses",
                "costAndExpenses",
                "interestExpense",
                "depreciationAndAmortization",
                "ebitda",
                "ebitdaratio",
                "operatingIncome",
                "operatingIncomeRatio",
                "totalOtherIncomeExpensesNet",
                "incomeBeforeTax",
                "incomeBeforeTaxRatio",
                "incomeTaxExpense",
                "netIncome",
                "netIncomeRatio",
                "eps",
                "epsdiluted",
                "weightedAverageShsOut",
                "weightedAverageShsOutDil"
            FROM fmp.income_statement_q
            );
            """
    )

    drop_key_metrics = PostgresOperator(
        task_id="drop_key_metrics",
        sql="DROP TABLE IF EXISTS anl.key_metrics;"
    )

    create_key_metrics = PostgresOperator(
        task_id="create_key_metrics",
        sql="""CREATE TABLE IF NOT EXISTS anl.key_metrics AS (
            SELECT		
                GET_TXT_DATE("date") AS date,
                'Year' as period, 
                "symbol",
                "revenuePerShare",
                "netIncomePerShare",
                "operatingCashFlowPerShare",
                "freeCashFlowPerShare",
                "cashPerShare",
                "bookValuePerShare",
                "tangibleBookValuePerShare",
                "shareholdersEquityPerShare",
                "interestDebtPerShare",
                "marketCap",
                "enterpriseValue",
                "peRatio",
                "priceToSalesRatio",
                "pocfratio",
                "pfcfRatio",
                "pbRatio",
                "ptbRatio",
                "evToSales",
                "enterpriseValueOverEBITDA",
                "evToOperatingCashFlow",
                "evToFreeCashFlow",
                "earningsYield",
                "freeCashFlowYield",
                "debtToEquity",
                "debtToAssets",
                "netDebtToEBITDA",
                "currentRatio",
                "interestCoverage",
                "incomeQuality",
                "dividendYield",
                "payoutRatio",
                "salesGeneralAndAdministrativeToRevenue",
                "researchAndDdevelopementToRevenue",
                "intangiblesToTotalAssets",
                "capexToOperatingCashFlow",
                "capexToRevenue",
                "capexToDepreciation",
                "stockBasedCompensationToRevenue",
                "grahamNumber",
                "roic",
                "returnOnTangibleAssets",
                "grahamNetNet",
                "workingCapital",
                "tangibleAssetValue",
                "netCurrentAssetValue",
                "investedCapital",
                "averageReceivables",
                "averagePayables",
                "averageInventory",
                "daysSalesOutstanding",
                "daysPayablesOutstanding",
                "daysOfInventoryOnHand",
                "receivablesTurnover",
                "payablesTurnover",
                "inventoryTurnover",
                "roe",
                "capexPerShare"
            FROM fmp.key_metrics_y
            UNION ALL
            SELECT		
                GET_TXT_DATE("date") AS date,
                'Quarter' as period, 
                "symbol",
                "revenuePerShare",
                "netIncomePerShare",
                "operatingCashFlowPerShare",
                "freeCashFlowPerShare",
                "cashPerShare",
                "bookValuePerShare",
                "tangibleBookValuePerShare",
                "shareholdersEquityPerShare",
                "interestDebtPerShare",
                "marketCap",
                "enterpriseValue",
                "peRatio",
                "priceToSalesRatio",
                "pocfratio",
                "pfcfRatio",
                "pbRatio",
                "ptbRatio",
                "evToSales",
                "enterpriseValueOverEBITDA",
                "evToOperatingCashFlow",
                "evToFreeCashFlow",
                "earningsYield",
                "freeCashFlowYield",
                "debtToEquity",
                "debtToAssets",
                "netDebtToEBITDA",
                "currentRatio",
                "interestCoverage",
                "incomeQuality",
                "dividendYield",
                "payoutRatio",
                "salesGeneralAndAdministrativeToRevenue",
                "researchAndDdevelopementToRevenue",
                "intangiblesToTotalAssets",
                "capexToOperatingCashFlow",
                "capexToRevenue",
                "capexToDepreciation",
                "stockBasedCompensationToRevenue",
                "grahamNumber",
                "roic",
                "returnOnTangibleAssets",
                "grahamNetNet",
                "workingCapital",
                "tangibleAssetValue",
                "netCurrentAssetValue",
                "investedCapital",
                "averageReceivables",
                "averagePayables",
                "averageInventory",
                "daysSalesOutstanding",
                "daysPayablesOutstanding",
                "daysOfInventoryOnHand",
                "receivablesTurnover",
                "payablesTurnover",
                "inventoryTurnover",
                "roe",
                "capexPerShare"
            FROM fmp.key_metrics_q            
            );
        """
    )

    drop_fund_statements = PostgresOperator(
        task_id="drop_key_metrics",
        sql="DROP TABLE IF EXISTS anl.fund_statements;"
    )

    create_fund_statements = PostgresOperator(
        task_id="create_fund_statements",
        sql="""
        CREATE TABLE IF NOT EXISTS anl.fund_statements AS (
        SELECT
            km."symbol",
            prof."sector",
            prof."currency",
            km."period",
            km."month",
            km."year",
            km."date",
            km."revenuePerShare",
            km."netIncomePerShare",
            km."operatingCashFlowPerShare",
            km."freeCashFlowPerShare",
            km."cashPerShare",
            km."bookValuePerShare",
            km."tangibleBookValuePerShare",
            km."shareholdersEquityPerShare",
            km."interestDebtPerShare",
            km."marketCap",
            km."enterpriseValue",
            km."peRatio",
            km."priceToSalesRatio",
            km."pocfratio",
            km."pfcfRatio",
            km."pbRatio",
            km."ptbRatio",
            km."evToSales",
            km."enterpriseValueOverEBITDA",
            km."evToOperatingCashFlow",
            km."evToFreeCashFlow",
            km."earningsYield",
            km."freeCashFlowYield",
            km."debtToEquity",
            km."debtToAssets",
            km."netDebtToEBITDA",
            km."currentRatio",
            km."interestCoverage",
            km."incomeQuality",
            km."dividendYield",
            km."payoutRatio",
            km."salesGeneralAndAdministrativeToRevenue",
            km."researchAndDdevelopementToRevenue",
            km."intangiblesToTotalAssets",
            km."capexToOperatingCashFlow",
            km."capexToRevenue",
            km."capexToDepreciation",
            km."stockBasedCompensationToRevenue",
            km."grahamNumber",
            km."roic",
            km."returnOnTangibleAssets",
            km."grahamNetNet",
            km."workingCapital",
            km."tangibleAssetValue",
            km."netCurrentAssetValue",
            km."investedCapital",
            km."averageReceivables",
            km."averagePayables",
            km."averageInventory",
            km."daysSalesOutstanding",
            km."daysPayablesOutstanding",
            km."daysOfInventoryOnHand",
            km."receivablesTurnover",
            km."payablesTurnover",
            km."inventoryTurnover",
            km."roe",
            km."capexPerShare",
        
            bs."cashAndCashEquivalents",
            bs."shortTermInvestments",
            bs."cashAndShortTermInvestments",
            bs."netReceivables",
            COALESCE(bs."inventory", cf."inventory") AS "inventory",
            bs."otherCurrentAssets",
            bs."totalCurrentAssets",
            bs."propertyPlantEquipmentNet",
            bs."goodwill",
            bs."intangibleAssets",
            bs."goodwillAndIntangibleAssets",
            bs."longTermInvestments",
            bs."taxAssets",
            bs."otherNonCurrentAssets",
            bs."totalNonCurrentAssets",
            bs."otherAssets",
            bs."totalAssets",
            bs."accountPayables",
            bs."shortTermDebt",
            bs."taxPayables",
            bs."deferredRevenue",
            bs."otherCurrentLiabilities",
            bs."totalCurrentLiabilities",
            bs."longTermDebt",
            bs."deferredRevenueNonCurrent",
            bs."deferredTaxLiabilitiesNonCurrent",
            bs."otherNonCurrentLiabilities",
            bs."totalNonCurrentLiabilities",
            bs."otherLiabilities",
            bs."totalLiabilities",
            bs."commonStock",
            bs."retainedEarnings",
            bs."accumulatedOtherComprehensiveIncomeLoss",
            bs."othertotalStockholdersEquity",
            bs."totalStockholdersEquity",
            bs."totalLiabilitiesAndStockholdersEquity",
            bs."totalInvestments",
            bs."totalDebt",
            bs."netDebt",
        
            COALESCE(cf."depreciationAndAmortization", inc."depreciationAndAmortization") AS "depreciationAndAmortization",
            cf."deferredIncomeTax",
            cf."stockBasedCompensation",
            cf."changeInWorkingCapital",
            cf."accountsReceivables",
            cf."accountsPayables",
            cf."otherWorkingCapital",
            cf."otherNonCashItems",
            cf."netCashProvidedByOperatingActivities",
            cf."investmentsInPropertyPlantAndEquipment",
            cf."acquisitionsNet",
            cf."purchasesOfInvestments",
            cf."salesMaturitiesOfInvestments",
            cf."otherInvestingActivites",
            cf."netCashUsedForInvestingActivites",
            cf."debtRepayment",
            cf."commonStockIssued",
            cf."commonStockRepurchased",
            cf."dividendsPaid",
            cf."otherFinancingActivites",
            cf."netCashUsedProvidedByFinancingActivities",
            cf."effectOfForexChangesOnCash",
            cf."netChangeInCash",
            cf."cashAtEndOfPeriod",
            cf."cashAtBeginningOfPeriod",
            cf."operatingCashFlow",
            cf."capitalExpenditure",
            cf."freeCashFlow",
        
            inc."revenue",
            inc."costOfRevenue",
            inc."grossProfit",
            inc."grossProfitRatio",
            inc."researchAndDevelopmentExpenses",
            inc."generalAndAdministrativeExpenses",
            inc."sellingAndMarketingExpenses",
            inc."otherExpenses",
            inc."operatingExpenses",
            inc."costAndExpenses",
            inc."interestExpense",
            inc."ebitda",
            inc."ebitdaratio",
            inc."operatingIncome",
            inc."operatingIncomeRatio",
            inc."totalOtherIncomeExpensesNet",
            inc."incomeBeforeTax",
            inc."incomeBeforeTaxRatio",
            inc."incomeTaxExpense",
            COALESCE(inc."netIncome", cf."netIncome") AS "netIncome",
            inc."netIncomeRatio",
            inc."eps",
            inc."epsdiluted",
            inc."weightedAverageShsOut",
            inc."weightedAverageShsOutDil"
        FROM (
            SELECT
                *,
                date_part('month', date) as month,
                date_part('year', date) as year
            FROM anl.key_metrics ) AS km
            INNER JOIN (
            SELECT
                *,
                date_part('month', date) as month,
                date_part('year', date) as year
            FROM anl.balance_sheet) as bs 
                ON km.symbol = bs.symbol 
                    AND km.month = bs.month 
                    AND km.year = bs.year 
                    AND km.period = bs.period 
            INNER JOIN (
            SELECT
                *,
                date_part('month', date) as month,
                date_part('year', date) as year
            FROM anl.income_statement) as inc 
                ON km.symbol = inc.symbol 
                    AND km.month = inc.month 
                    AND km.year = inc.year 
                    AND km.period = inc.period 
            INNER JOIN (
            SELECT
                *,
                date_part('month', date) as month,
                date_part('year', date) as year
            FROM anl.cash_flows) as cf 
                ON km.symbol = cf.symbol 
                    AND km.month = cf.month 
                    AND km.year = cf.year 
                    AND km.period = cf.period 
            INNER JOIN(
            SELECT 
                symbol, 
                sector,
                currency
            FROM fmp.company_profile
            ) AS prof ON km.symbol = prof.symbol
        );
        """
    )

    sending_slack_notification = SlackAPIPostOperator(
        task_id="sending_slack",
        channel=slack_channel,
        token=slack_token,
        username="honeySlackApp",
        text="DAG anl_update_daily: DONE",
    )

drop_daily_return >> create_daily_return
drop_cash_flows >> create_cash_flows
drop_balance_sheet >> create_balance_sheet
drop_income_statement >> create_income_statement
drop_key_metrics >> create_key_metrics
earnings_calendar_update >> anl_drop_calendar >> anl_create_calendar
drop_key_metrics >> create_key_metrics


create_daily_return >> truncate_clusters >> cluster_tickers >> drop_dash_main_table >> create_dash_main_table

[create_dash_main_table, create_cash_flows, create_balance_sheet, create_income_statement, create_key_metrics, anl_create_calendar] >> drop_fund_statements

drop_fund_statements >> create_fund_statements >> truncate_stmnt_scores >> upload_stmnt_scores >> sending_slack_notification

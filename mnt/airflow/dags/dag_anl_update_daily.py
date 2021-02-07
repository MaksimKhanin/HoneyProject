from airflow import DAG
from airflow.hooks.base_hook import BaseHook
from airflow.operators.slack_operator import SlackAPIPostOperator
from airflow.operators.postgres_operator import PostgresOperator
from datetime import datetime, timedelta

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

with DAG(dag_id="anl_update_daily", schedule_interval=None, default_args=default_args, catchup=False) as dag:

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


[create_daily_return, create_cash_flows, create_balance_sheet, create_income_statement, create_key_metrics]  >> sending_slack_notification

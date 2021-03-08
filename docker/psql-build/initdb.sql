
CREATE SCHEMA IF NOT EXISTS tink;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS sys_upd;
CREATE SCHEMA IF NOT EXISTS fmp;
CREATE SCHEMA IF NOT EXISTS anl;
CREATE DATABASE airflow;

DROP TABLE IF EXISTS tink.security;
CREATE TABLE IF NOT EXISTS tink.security (
    "figi" TEXT, 
    "ticker" TEXT, 
    "isin" TEXT, 
    "minPriceIncrement" NUMERIC, 
    "lot" NUMERIC,
    "currency" TEXT, 
    "name" TEXT, 
    "type" TEXT,
    PRIMARY KEY("figi", "ticker")
    );

DROP TABLE IF EXISTS tink.candles_day;
CREATE TABLE IF NOT EXISTS tink.candle_day (
    "o" NUMERIC,
    "c" NUMERIC,
    "h" NUMERIC,
    "l" NUMERIC,
    "v" NUMERIC,
    "time" TIMESTAMP WITH TIME ZONE,
    "figi" TEXT,
    PRIMARY KEY("figi", "time")
    );

DROP TABLE IF EXISTS tink.candles_hour;
CREATE TABLE IF NOT EXISTS tink.candle_hour (
    "o" NUMERIC,
    "c" NUMERIC,
    "h" NUMERIC,
    "l" NUMERIC,
    "v" NUMERIC,
    "time" TIMESTAMP WITH TIME ZONE,
    "figi" TEXT,
    PRIMARY KEY("figi", "time")
    );

DROP TABLE IF EXISTS fmp.company_profile;
CREATE TABLE IF NOT EXISTS fmp.company_profile (
    "symbol" TEXT,
    "price" NUMERIC,
    "beta" NUMERIC, 
    "volAvg" NUMERIC,
    "mktCap" NUMERIC,
    "lastDiv" NUMERIC,
    "range" TEXT,
    "changes" NUMERIC,
    "companyName" TEXT,
    "currency" TEXT, 
    "cik" TEXT, 
    "isin" TEXT, 
    "cusip" TEXT,
    "exchange" TEXT, 
    "exchangeShortName" TEXT, 
    "industry" TEXT, 
    "website" TEXT,
    "description" TEXT,
    "ceo" TEXT,
    "sector" TEXT,
    "country" TEXT,
    "fullTimeEmployees" TEXT,
    "phone" TEXT,
    "address" TEXT,
    "city" TEXT,
    "state" TEXT,
    "zip" TEXT,
    "dcfDiff" NUMERIC,
    "dcf" NUMERIC,
    "ipoDate" TEXT,
    PRIMARY KEY("symbol")
    );

DROP TABLE IF EXISTS stg.balance_sheet;
CREATE TABLE IF NOT EXISTS stg.balance_sheet (
    "date" TEXT,
    "symbol" TEXT,
    "fillingDate" TEXT,
    "acceptedDate" TEXT,
    "period" TEXT,
    "cashAndCashEquivalents" NUMERIC,
    "shortTermInvestments" NUMERIC,
    "cashAndShortTermInvestments" NUMERIC,
    "netReceivables" NUMERIC,
    "inventory" NUMERIC,
    "otherCurrentAssets" NUMERIC,
    "totalCurrentAssets" NUMERIC,
    "propertyPlantEquipmentNet" NUMERIC,
    "goodwill" NUMERIC,
    "intangibleAssets" NUMERIC,
    "goodwillAndIntangibleAssets" NUMERIC,
    "longTermInvestments" NUMERIC,
    "taxAssets" NUMERIC,
    "otherNonCurrentAssets" NUMERIC,
    "totalNonCurrentAssets" NUMERIC,
    "otherAssets" NUMERIC,
    "totalAssets" NUMERIC,
    "accountPayables" NUMERIC,
    "shortTermDebt" NUMERIC,
    "taxPayables" NUMERIC,
    "deferredRevenue" NUMERIC,
    "otherCurrentLiabilities" NUMERIC,
    "totalCurrentLiabilities" NUMERIC,
    "longTermDebt" NUMERIC,
    "deferredRevenueNonCurrent" NUMERIC,
    "deferredTaxLiabilitiesNonCurrent" NUMERIC,
    "otherNonCurrentLiabilities" NUMERIC,
    "totalNonCurrentLiabilities" NUMERIC,
    "otherLiabilities" NUMERIC,
    "totalLiabilities" NUMERIC,
    "commonStock" NUMERIC,
    "retainedEarnings" NUMERIC,
    "accumulatedOtherComprehensiveIncomeLoss" NUMERIC,
    "othertotalStockholdersEquity" NUMERIC,
    "totalStockholdersEquity" NUMERIC,
    "totalLiabilitiesAndStockholdersEquity" NUMERIC,
    "totalInvestments" NUMERIC,
    "totalDebt" NUMERIC,
    "netDebt" NUMERIC,
    "link" TEXT,
    "finalLink" TEXT,
    FOREIGN KEY("symbol") REFERENCES fmp.company_profile("symbol") ON DELETE CASCADE,
    UNIQUE("symbol", "date")
);

DROP TABLE IF EXISTS stg.cash_flows;
CREATE TABLE IF NOT EXISTS stg.cash_flows (
    "date" TEXT,
    "symbol" TEXT,
    "fillingDate" TEXT,
    "acceptedDate" TEXT,
    "period" TEXT,
    "netIncome" NUMERIC,
    "depreciationAndAmortization" NUMERIC,
    "deferredIncomeTax" NUMERIC,
    "stockBasedCompensation" NUMERIC,
    "changeInWorkingCapital" NUMERIC,
    "accountsReceivables" NUMERIC,
    "inventory" NUMERIC,
    "accountsPayables" NUMERIC,
    "otherWorkingCapital" NUMERIC,
    "otherNonCashItems" NUMERIC,
    "netCashProvidedByOperatingActivities" NUMERIC,
    "investmentsInPropertyPlantAndEquipment" NUMERIC,
    "acquisitionsNet" NUMERIC,
    "purchasesOfInvestments" NUMERIC,
    "salesMaturitiesOfInvestments" NUMERIC,
    "otherInvestingActivites" NUMERIC,
    "netCashUsedForInvestingActivites" NUMERIC,
    "debtRepayment" NUMERIC,
    "commonStockIssued" NUMERIC,
    "commonStockRepurchased" NUMERIC,
    "dividendsPaid" NUMERIC,
    "otherFinancingActivites" NUMERIC,
    "netCashUsedProvidedByFinancingActivities" NUMERIC,
    "effectOfForexChangesOnCash" NUMERIC,
    "netChangeInCash" NUMERIC,
    "cashAtEndOfPeriod" NUMERIC,
    "cashAtBeginningOfPeriod" NUMERIC,
    "operatingCashFlow" NUMERIC,
    "capitalExpenditure" NUMERIC,
    "freeCashFlow" NUMERIC,
    "link" TEXT,
    "finalLink" TEXT,
    FOREIGN KEY("symbol") REFERENCES fmp.company_profile("symbol") ON DELETE CASCADE,
    UNIQUE("symbol", "date")
);

DROP TABLE IF EXISTS stg.key_metrics;
CREATE TABLE IF NOT EXISTS stg.key_metrics (
    "symbol" TEXT,
    "date" TEXT,
    "revenuePerShare" NUMERIC,
    "netIncomePerShare" NUMERIC,
    "operatingCashFlowPerShare" NUMERIC,
    "freeCashFlowPerShare" NUMERIC,
    "cashPerShare" NUMERIC,
    "bookValuePerShare" NUMERIC,
    "tangibleBookValuePerShare" NUMERIC,
    "shareholdersEquityPerShare" NUMERIC,
    "interestDebtPerShare" NUMERIC,
    "marketCap" NUMERIC,
    "enterpriseValue" NUMERIC,
    "peRatio" NUMERIC,
    "priceToSalesRatio" NUMERIC,
    "pocfratio" NUMERIC,
    "pfcfRatio" NUMERIC,
    "pbRatio" NUMERIC,
    "ptbRatio" NUMERIC,
    "evToSales" NUMERIC,
    "enterpriseValueOverEBITDA" NUMERIC,
    "evToOperatingCashFlow" NUMERIC,
    "evToFreeCashFlow" NUMERIC,
    "earningsYield" NUMERIC,
    "freeCashFlowYield" NUMERIC,
    "debtToEquity" NUMERIC,
    "debtToAssets" NUMERIC,
    "netDebtToEBITDA" NUMERIC,
    "currentRatio" NUMERIC,
    "interestCoverage" NUMERIC,
    "incomeQuality" NUMERIC,
    "dividendYield" NUMERIC,
    "payoutRatio" NUMERIC,
    "salesGeneralAndAdministrativeToRevenue" NUMERIC,
    "researchAndDdevelopementToRevenue" NUMERIC,
    "intangiblesToTotalAssets" NUMERIC,
    "capexToOperatingCashFlow" NUMERIC,
    "capexToRevenue" NUMERIC,
    "capexToDepreciation" NUMERIC,
    "stockBasedCompensationToRevenue" NUMERIC,
    "grahamNumber" NUMERIC,
    "roic" NUMERIC,
    "returnOnTangibleAssets" NUMERIC,
    "grahamNetNet" NUMERIC,
    "workingCapital" NUMERIC,
    "tangibleAssetValue" NUMERIC,
    "netCurrentAssetValue" NUMERIC,
    "investedCapital" NUMERIC,
    "averageReceivables" NUMERIC,
    "averagePayables" NUMERIC,
    "averageInventory" NUMERIC,
    "daysSalesOutstanding" NUMERIC,
    "daysPayablesOutstanding" NUMERIC,
    "daysOfInventoryOnHand" NUMERIC,
    "receivablesTurnover" NUMERIC,
    "payablesTurnover" NUMERIC,
    "inventoryTurnover" NUMERIC,
    "roe" NUMERIC,
    "capexPerShare" NUMERIC,
    FOREIGN KEY("symbol") REFERENCES fmp.company_profile("symbol")  ON DELETE CASCADE,
    UNIQUE("symbol", "date")
);

DROP TABLE IF EXISTS stg.income_statement;
CREATE TABLE IF NOT EXISTS stg.income_statement (
        "date" TEXT,
        "symbol" TEXT,
        "fillingDate" TEXT,
        "acceptedDate" TEXT,
        "period" TEXT,
        "revenue" NUMERIC,
        "costOfRevenue" NUMERIC,
        "grossProfit" NUMERIC,
        "grossProfitRatio" NUMERIC,
        "researchAndDevelopmentExpenses" NUMERIC,
        "generalAndAdministrativeExpenses" NUMERIC,
        "sellingAndMarketingExpenses" NUMERIC,
        "otherExpenses" NUMERIC,
        "operatingExpenses" NUMERIC,
        "costAndExpenses" NUMERIC,
        "interestExpense" NUMERIC,
        "depreciationAndAmortization" NUMERIC,
        "ebitda" NUMERIC,
        "ebitdaratio" NUMERIC,
        "operatingIncome" NUMERIC,
        "operatingIncomeRatio" NUMERIC,
        "totalOtherIncomeExpensesNet" NUMERIC,
        "incomeBeforeTax" NUMERIC,
        "incomeBeforeTaxRatio" NUMERIC,
        "incomeTaxExpense" NUMERIC,
        "netIncome" NUMERIC,
        "netIncomeRatio" NUMERIC,
        "eps" NUMERIC,
        "epsdiluted" NUMERIC,
        "weightedAverageShsOut" NUMERIC,
        "weightedAverageShsOutDil" NUMERIC,
        "link" TEXT,
        "finalLink" TEXT,
        FOREIGN KEY("symbol") REFERENCES fmp.company_profile("symbol") ON DELETE CASCADE,
        UNIQUE("symbol", "date")
);

DROP TABLE IF EXISTS fmp.income_statement_q;
CREATE TABLE IF NOT EXISTS fmp.income_statement_q ( like stg.income_statement including all);
DROP TABLE IF EXISTS fmp.income_statement_y;
CREATE TABLE fmp.income_statement_y ( like stg.income_statement including all);

DROP TABLE IF EXISTS fmp.key_metrics_q;
CREATE TABLE IF NOT EXISTS fmp.key_metrics_q ( like stg.key_metrics including all);
DROP TABLE IF EXISTS fmp.key_metrics_y;
CREATE TABLE IF NOT EXISTS fmp.key_metrics_y ( like stg.key_metrics including all);

DROP TABLE IF EXISTS fmp.cash_flows_q;
CREATE TABLE IF NOT EXISTS fmp.cash_flows_q ( like stg.cash_flows including all);
DROP TABLE IF EXISTS fmp.cash_flows_y;
CREATE TABLE IF NOT EXISTS fmp.cash_flows_y ( like stg.cash_flows including all);

DROP TABLE IF EXISTS fmp.balance_sheet_q;
CREATE TABLE IF NOT EXISTS fmp.balance_sheet_q ( like stg.balance_sheet including all);
DROP TABLE IF EXISTS fmp.balance_sheet_y;
CREATE TABLE IF NOT EXISTS fmp.balance_sheet_y ( like stg.balance_sheet including all);




DROP TABLE IF EXISTS fmp.security;
CREATE TABLE IF NOT EXISTS fmp.security (
    "ticker" TEXT,
    "name" TEXT,
    "currency" TEXT,
    "type" TEXT,
    PRIMARY KEY("ticker")
);

DROP TABLE IF EXISTS sys_upd.fmp_candle;
CREATE TABLE IF NOT EXISTS sys_upd.fmp_candle (
    "ticker" TEXT,
    "interval" TEXT,
    "last_update" TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY("ticker", "interval"),
    FOREIGN KEY("ticker") REFERENCES fmp.security("ticker") ON DELETE CASCADE);

DROP TABLE IF EXISTS stg.fmp_candles;
CREATE TABLE IF NOT EXISTS stg.fmp_candles (
    "date" TIMESTAMP,
    "open" NUMERIC,
    "high" NUMERIC,
    "low" NUMERIC,
    "close" NUMERIC,
    "volume" NUMERIC
);

DROP TABLE IF EXISTS fmp.candles_day;
CREATE TABLE IF NOT EXISTS fmp.candles_day (
    "ticker" TEXT,
    "time" TIMESTAMP,
    "open" NUMERIC,
    "high" NUMERIC,
    "low" NUMERIC,
    "close" NUMERIC,
    "volume" NUMERIC,
    PRIMARY KEY("ticker", "time")
);

DROP TABLE IF EXISTS fmp.earnings_calendar;
CREATE TABLE IF NOT EXISTS fmp.earnings_calendar (
    "date" TEXT,
    "symbol" TEXT,
    "eps" NUMERIC,
    "epsEstimated" NUMERIC,
    "time" TEXT,
    "revenue" NUMERIC,
    "revenueEstimated" NUMERIC,
    PRIMARY KEY("symbol", "date", "time")
);

DROP TABLE IF EXISTS sys_upd.tink_candle;
CREATE TABLE IF NOT EXISTS sys_upd.tink_candle (
    "figi" TEXT,
    "ticker" TEXT,
    "interval" TEXT,
    "last_update" TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY("figi", "ticker", "interval"),
    FOREIGN KEY("figi", "ticker") REFERENCES tink.security("figi", "ticker") ON DELETE CASCADE);

DROP TABLE IF EXISTS sys_upd.fmp_fin_stat;
CREATE TABLE IF NOT EXISTS sys_upd.fmp_fin_stat (
    "symbol" TEXT,
    "stat" TEXT,
    "period" TEXT,
    "last_update" TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY("symbol", "stat", "period"),
    FOREIGN KEY("symbol") REFERENCES fmp.company_profile("symbol") ON DELETE CASCADE);

DROP TABLE IF EXISTS anl.man_company_profiles;
CREATE TABLE IF NOT EXISTS anl.man_company_profiles (
    "symbol" TEXT,
    "sector" TEXT,
    "industry" TEXT,
    PRIMARY KEY("symbol")
);

DROP TABLE IF EXISTS anl.ml_ticker_clustering;
CREATE TABLE IF NOT EXISTS anl.ml_ticker_clustering (
        "ticker" TEXT,
        "pca_loading_0" NUMERIC,
        "pca_loading_1" NUMERIC,
        "pca_loading_2" NUMERIC,
        "cluster" TEXT,
        PRIMARY KEY("ticker")
);

COPY anl.man_company_profiles("symbol", "sector", "industry")
FROM '/manual_sectors.csv'
DELIMITER ','
CSV HEADER;

CREATE OR REPLACE FUNCTION get_txt_date(date TEXT)
RETURNS DATE AS $$
BEGIN
	RETURN
	TO_DATE(
		SUBSTRING(
			SPLIT_PART(date, '-', 1) || ';' ||
			SPLIT_PART(date, '-', 2) || ';' ||
			CASE
				WHEN
					SPLIT_PART(date, '-', 3) = '31' THEN '30'
				ELSE
					SPLIT_PART(date, '-', 3) END,
		'[0-9]{4};[0-9]{2};[0-9]{2}'), 'YYYY;MM;DD');
END;
$$
LANGUAGE PLPGSQL;

CREATE_REL_TINK_FMP_TABLE = """
    CREATE TABLE IF NOT EXISTS fmp.tink_sec_x_fmp_prof AS
    (
        SELECT
            figi,
            ticker,
            CASE 
                WHEN currency = 'RUB' THEN ticker || '.ME' ELSE  ticker 
            END AS fmp_symbol
        FROM tink.security
    );   
"""

INSERT_COMPANY_PROFILE_JSON = """
    INSERT INTO fmp.company_profile
        SELECT * 
        FROM json_populate_recordset(NULL::fmp.company_profile, %s)
        ON CONFLICT ("symbol") DO UPDATE SET
        (
            "price",
            "beta",
            "volAvg",
            "mktCap",
            "lastDiv",
            "range",
            "changes",
            "companyName",
            "currency", 
            "cik", 
            "cusip",
            "exchange", 
            "exchangeShortName", 
            "industry", 
            "website",
            "description",
            "ceo",
            "sector",
            "country",
            "fullTimeEmployees",
            "phone",
            "address",
            "city",
            "state",
            "zip",
            "dcfDiff",
            "dcf",
            "ipoDate"
        )
        =
        (
            EXCLUDED."price",
            EXCLUDED."beta",
            EXCLUDED."volAvg",
            EXCLUDED."mktCap",
            EXCLUDED."lastDiv",
            EXCLUDED."range",
            EXCLUDED."changes",
            EXCLUDED."companyName",
            EXCLUDED."currency", 
            EXCLUDED."cik", 
            EXCLUDED."cusip",
            EXCLUDED."exchange", 
            EXCLUDED."exchangeShortName", 
            EXCLUDED."industry", 
            EXCLUDED."website",
            EXCLUDED."description",
            EXCLUDED."ceo",
            EXCLUDED."sector",
            EXCLUDED."country",
            EXCLUDED."fullTimeEmployees",
            EXCLUDED."phone",
            EXCLUDED."address",
            EXCLUDED."city",
            EXCLUDED."state",
            EXCLUDED."zip",
            EXCLUDED."dcfDiff",
            EXCLUDED."dcf",
            EXCLUDED."ipoDate");
"""


INSERT_INCOME_STATEMENT_JSON = """
    INSERT INTO fmp.income_statement_{period}
        SELECT * 
        FROM json_populate_recordset(NULL::stg.income_statement, %s)
    ON CONFLICT ("symbol", "date") DO UPDATE SET
        (
            "fillingDate",
            "acceptedDate",
            "period",
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
            "weightedAverageShsOutDil",
            "link",
            "finalLink"
        )
        =
        (
            EXCLUDED."fillingDate",
            EXCLUDED."acceptedDate",
            EXCLUDED."period",
            EXCLUDED."revenue",
            EXCLUDED."costOfRevenue",
            EXCLUDED."grossProfit",
            EXCLUDED."grossProfitRatio",
            EXCLUDED."researchAndDevelopmentExpenses",
            EXCLUDED."generalAndAdministrativeExpenses",
            EXCLUDED."sellingAndMarketingExpenses",
            EXCLUDED."otherExpenses",
            EXCLUDED."operatingExpenses",
            EXCLUDED."costAndExpenses",
            EXCLUDED."interestExpense",
            EXCLUDED."depreciationAndAmortization",
            EXCLUDED."ebitda",
            EXCLUDED."ebitdaratio",
            EXCLUDED."operatingIncome",
            EXCLUDED."operatingIncomeRatio",
            EXCLUDED."totalOtherIncomeExpensesNet",
            EXCLUDED."incomeBeforeTax",
            EXCLUDED."incomeBeforeTaxRatio",
            EXCLUDED."incomeTaxExpense",
            EXCLUDED."netIncome",
            EXCLUDED."netIncomeRatio",
            EXCLUDED."eps",
            EXCLUDED."epsdiluted",
            EXCLUDED."weightedAverageShsOut",
            EXCLUDED."weightedAverageShsOutDil",
            EXCLUDED."link",
            EXCLUDED."finalLink"
        );
"""

INSERT_BALANCE_SHEET_JSON = """
    INSERT INTO fmp.balance_sheet_{period}
        SELECT * 
        FROM json_populate_recordset(NULL::stg.balance_sheet, %s)
    ON CONFLICT ("symbol", "date") DO UPDATE SET
        (
            "fillingDate",
            "acceptedDate",
            "period",
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
            "netDebt",
            "link",
            "finalLink"
        )
        =
        (
            EXCLUDED."fillingDate",
            EXCLUDED."acceptedDate",
            EXCLUDED."period",
            EXCLUDED."cashAndCashEquivalents",
            EXCLUDED."shortTermInvestments",
            EXCLUDED."cashAndShortTermInvestments",
            EXCLUDED."netReceivables",
            EXCLUDED."inventory",
            EXCLUDED."otherCurrentAssets",
            EXCLUDED."totalCurrentAssets",
            EXCLUDED."propertyPlantEquipmentNet",
            EXCLUDED."goodwill",
            EXCLUDED."intangibleAssets",
            EXCLUDED."goodwillAndIntangibleAssets",
            EXCLUDED."longTermInvestments",
            EXCLUDED."taxAssets",
            EXCLUDED."otherNonCurrentAssets",
            EXCLUDED."totalNonCurrentAssets",
            EXCLUDED."otherAssets",
            EXCLUDED."totalAssets",
            EXCLUDED."accountPayables",
            EXCLUDED."shortTermDebt",
            EXCLUDED."taxPayables",
            EXCLUDED."deferredRevenue",
            EXCLUDED."otherCurrentLiabilities",
            EXCLUDED."totalCurrentLiabilities",
            EXCLUDED."longTermDebt",
            EXCLUDED."deferredRevenueNonCurrent",
            EXCLUDED."deferredTaxLiabilitiesNonCurrent",
            EXCLUDED."otherNonCurrentLiabilities",
            EXCLUDED."totalNonCurrentLiabilities",
            EXCLUDED."otherLiabilities",
            EXCLUDED."totalLiabilities",
            EXCLUDED."commonStock",
            EXCLUDED."retainedEarnings",
            EXCLUDED."accumulatedOtherComprehensiveIncomeLoss",
            EXCLUDED."othertotalStockholdersEquity",
            EXCLUDED."totalStockholdersEquity",
            EXCLUDED."totalLiabilitiesAndStockholdersEquity",
            EXCLUDED."totalInvestments",
            EXCLUDED."totalDebt",
            EXCLUDED."netDebt",
            EXCLUDED."link",
            EXCLUDED."finalLink"
        );
"""


INSERT_CASH_FLOWS_JSON = """
    INSERT INTO fmp.cash_flows_{period}
        SELECT * 
        FROM json_populate_recordset(NULL::stg.cash_flows, %s)
    ON CONFLICT ("symbol", "date") DO UPDATE SET
        (
            "fillingDate",
            "acceptedDate",
            "period",
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
            "freeCashFlow",
            "link",
            "finalLink"
        )
        =
        (
            EXCLUDED."fillingDate",
            EXCLUDED."acceptedDate",
            EXCLUDED."period",
            EXCLUDED."netIncome",
            EXCLUDED."depreciationAndAmortization",
            EXCLUDED."deferredIncomeTax",
            EXCLUDED."stockBasedCompensation",
            EXCLUDED."changeInWorkingCapital",
            EXCLUDED."accountsReceivables",
            EXCLUDED."inventory",
            EXCLUDED."accountsPayables",
            EXCLUDED."otherWorkingCapital",
            EXCLUDED."otherNonCashItems",
            EXCLUDED."netCashProvidedByOperatingActivities",
            EXCLUDED."investmentsInPropertyPlantAndEquipment",
            EXCLUDED."acquisitionsNet",
            EXCLUDED."purchasesOfInvestments",
            EXCLUDED."salesMaturitiesOfInvestments",
            EXCLUDED."otherInvestingActivites",
            EXCLUDED."netCashUsedForInvestingActivites",
            EXCLUDED."debtRepayment",
            EXCLUDED."commonStockIssued",
            EXCLUDED."commonStockRepurchased",
            EXCLUDED."dividendsPaid",
            EXCLUDED."otherFinancingActivites",
            EXCLUDED."netCashUsedProvidedByFinancingActivities",
            EXCLUDED."effectOfForexChangesOnCash",
            EXCLUDED."netChangeInCash",
            EXCLUDED."cashAtEndOfPeriod",
            EXCLUDED."cashAtBeginningOfPeriod",
            EXCLUDED."operatingCashFlow",
            EXCLUDED."capitalExpenditure",
            EXCLUDED."freeCashFlow",
            EXCLUDED."link",
            EXCLUDED."finalLink"
        );
"""

INSERT_KEY_METRICS_JSON = """
    INSERT INTO fmp.key_metrics_{period}
        SELECT * 
        FROM json_populate_recordset(NULL::stg.key_metrics, %s)
    ON CONFLICT ("symbol", "date") DO UPDATE SET
        (
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
        )
        =
        (
            EXCLUDED."revenuePerShare",
            EXCLUDED."netIncomePerShare",
            EXCLUDED."operatingCashFlowPerShare",
            EXCLUDED."freeCashFlowPerShare",
            EXCLUDED."cashPerShare",
            EXCLUDED."bookValuePerShare",
            EXCLUDED."tangibleBookValuePerShare",
            EXCLUDED."shareholdersEquityPerShare",
            EXCLUDED."interestDebtPerShare",
            EXCLUDED."marketCap",
            EXCLUDED."enterpriseValue",
            EXCLUDED."peRatio",
            EXCLUDED."priceToSalesRatio",
            EXCLUDED."pocfratio",
            EXCLUDED."pfcfRatio",
            EXCLUDED."pbRatio",
            EXCLUDED."ptbRatio",
            EXCLUDED."evToSales",
            EXCLUDED."enterpriseValueOverEBITDA",
            EXCLUDED."evToOperatingCashFlow",
            EXCLUDED."evToFreeCashFlow",
            EXCLUDED."earningsYield",
            EXCLUDED."freeCashFlowYield",
            EXCLUDED."debtToEquity",
            EXCLUDED."debtToAssets",
            EXCLUDED."netDebtToEBITDA",
            EXCLUDED."currentRatio",
            EXCLUDED."interestCoverage",
            EXCLUDED."incomeQuality",
            EXCLUDED."dividendYield",
            EXCLUDED."payoutRatio",
            EXCLUDED."salesGeneralAndAdministrativeToRevenue",
            EXCLUDED."researchAndDdevelopementToRevenue",
            EXCLUDED."intangiblesToTotalAssets",
            EXCLUDED."capexToOperatingCashFlow",
            EXCLUDED."capexToRevenue",
            EXCLUDED."capexToDepreciation",
            EXCLUDED."stockBasedCompensationToRevenue",
            EXCLUDED."grahamNumber",
            EXCLUDED."roic",
            EXCLUDED."returnOnTangibleAssets",
            EXCLUDED."grahamNetNet",
            EXCLUDED."workingCapital",
            EXCLUDED."tangibleAssetValue",
            EXCLUDED."netCurrentAssetValue",
            EXCLUDED."investedCapital",
            EXCLUDED."averageReceivables",
            EXCLUDED."averagePayables",
            EXCLUDED."averageInventory",
            EXCLUDED."daysSalesOutstanding",
            EXCLUDED."daysPayablesOutstanding",
            EXCLUDED."daysOfInventoryOnHand",
            EXCLUDED."receivablesTurnover",
            EXCLUDED."payablesTurnover",
            EXCLUDED."inventoryTurnover",
            EXCLUDED."roe",
            EXCLUDED."capexPerShare"
        );
"""

INSERT_EARNINGS_CALENDAR = """
    INSERT INTO fmp.earnings_calendar
        SELECT * 
        FROM json_populate_recordset(NULL::fmp.earnings_calendar, %s)
    ON CONFLICT ("symbol", "date", "time") DO UPDATE SET
        (
            "eps",
            "epsEstimated",
            "revenue",
            "revenueEstimated"
        )
        =
        (
            EXCLUDED."eps",
            EXCLUDED."epsEstimated",
            EXCLUDED."revenue",
            EXCLUDED."revenueEstimated"
        );
"""

GET_TINK_TICKERS_LIST = """
    SELECT 
        CASE 
            WHEN currency = 'RUB' THEN ticker || '.ME' ELSE  ticker 
        END 
    FROM tink.security;
"""

GET_TINK_X_FMP_SYMBOLS_LIST = """
    SELECT 
    DISTINCT fmp_symbol 
    FROM fmp.tink_sec_x_fmp_prof;
"""

GET_FMP_TICKERS_LIST = """
    SELECT 
        symbol
    FROM fmp.company_profile;
"""


GET_LAST_FIN_METRIC_UPDATE = """
    SELECT 
        MAX("last_update")
    FROM sys_upd.fmp_fin_stat
    WHERE 1=1
        AND "symbol" = %s
        AND "stat" = %s
        AND "period" = %s
"""

UPDATE_COMPANY_FIN_METRIC = """
    INSERT INTO sys_upd.fmp_fin_stat VALUES
    (%s, %s, %s, %s)
    ON CONFLICT ("symbol", "stat", "period") DO UPDATE SET
    "last_update" = EXCLUDED."last_update";
"""

GET_FMP_SYMBOL_LIST = """
    SELECT
        ticker
    FROM fmp.security;
"""

UPDATE_FMP_LAST_CANDLE_UPDATE = """
    INSERT INTO sys_upd.fmp_candle VALUES
    (%s, %s, %s)
    ON CONFLICT ("ticker", "interval") DO UPDATE SET
    "last_update" = EXCLUDED."last_update";
"""

GET_FMP_CANDLE_LAST_UPDATE = """
    SELECT 
        MAX("last_update")
    FROM sys_upd.fmp_candle
    WHERE 1=1
        AND "ticker" = %s
        AND "interval" = %s;
"""

INSERT_FMP_CANDLE_JSON = """
    INSERT INTO fmp.candles_{tf}
        SELECT 
            '{ticker}' AS "ticker",
            stg."date" AS "time",
            stg."open" AS "open",
            stg."high" AS "high",
            stg."low" AS "low",
            stg."close" AS "close",
            stg."volume" AS "volume"
        FROM (
            SELECT * 
            FROM json_populate_recordset(NULL::stg.fmp_candles, %s)
            ) AS stg
        WHERE stg."date" IS NOT NULL
    ON CONFLICT ("ticker", "time") DO UPDATE SET
        (
            "ticker",
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume"
        )
        =
        (
            EXCLUDED."ticker",
            EXCLUDED."time",
            EXCLUDED."open",
            EXCLUDED."high",
            EXCLUDED."low",
            EXCLUDED."close",
            EXCLUDED."volume"
        );
"""
GET_DAILY_RETURN = """
    SELECT 
        date, 
        ticker, 
        daily_return
    FROM anl.daily_return;
"""

# CREATE_ML_TICKER_CLUSTERING = """
#     CREATE TABLE IF NOT EXISTS anl.ml_ticker_clustering (
#         "ticker" TEXT,
#         "pca_loading_0" NUMERIC,
#         "pca_loading_1" NUMERIC,
#         "pca_loading_2" NUMERIC,
#         "cluster" TEXT,
#         PRIMARY KEY("ticker"));"""
import os
############################
# Defining .env
############################
# DB_USER = os.environ["DB_USER"]
# DB_PASSWORD = os.environ["DB_PASSWORD"]
# DB_HOST = os.environ["DB_HOST"]
# DB_PORT = os.environ["DB_PORT"]
#
#FMP_TOKEN = os.environ["FMP_TOKEN"]

NM_TRIES = 3

# from src.etl import fmp_etl
from src.ml import honeyML

from src.etl import fmp_etl
from src.etl.fmp_etl import fmp_con
from src.etl.fmp_etl import db_con

import pandas as pd
# honeyML.upload_clustering_df()

# ticker_list = fmp_etl.db_con.get_fetchAll(fmp_etl.queryLib.GET_TINK_TICKERS_LIST)
# ticker_array = list(map(lambda x: x[0], ticker_list))
# ticker_string = ",".join(ticker_array)
#
# #print(fmp_etl.fmp_con.get_finansials(stat="profile", ticker=ticker_string).text)
#
# fmp_etl.etl_fmp_stat(stat="key-metrics", period="year")
#
#
# fmp_con.get_calendar("earning_calendar")
# kwargs = dict()
# kwargs["from"] = "2021-01-01"
# kwargs["to"] = "2021-03-01"
# df = pd.DataFrame(fmp_con.get_calendar("earning_calendar", **kwargs).json())
# print(df[df["symbol"]=="SAGE"])
#fmp_etl.update_earnings_calendar(fmp_con, db_con)
#
# print(pd.DataFrame(fmp_con.get_calendar("historical/earning_calendar", ticker="SAGE", **kwargs).json()))
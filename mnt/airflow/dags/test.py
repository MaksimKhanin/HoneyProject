import os
############################
# Defining .env
############################
# DB_USER = os.environ["DB_USER"]
# DB_PASSWORD = os.environ["DB_PASSWORD"]
# DB_HOST = os.environ["DB_HOST"]
# DB_PORT = os.environ["DB_PORT"]
#
# FMP_TOKEN = os.environ["FMP_TOKEN"]


# from src.etl import fmp_etl
from src.etl import tink_etl

tink_etl.etl_candles("day")

# ticker_list = fmp_etl.db_con.get_fetchAll(fmp_etl.queryLib.GET_TINK_TICKERS_LIST)
# ticker_array = list(map(lambda x: x[0], ticker_list))
# ticker_string = ",".join(ticker_array)
#
# #print(fmp_etl.fmp_con.get_finansials(stat="profile", ticker=ticker_string).text)
#
# fmp_etl.etl_fmp_stat(stat="key-metrics", period="year")
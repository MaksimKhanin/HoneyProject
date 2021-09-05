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
import time
# from src.etl import fmp_etl
from src.ml import priceClustering

from src.etl import tink_etl
from src.etl import fmp_etl
from src.etl.fmp_etl import fmp_con
from src.etl.fmp_etl import db_con
from src.ml import stmnt_analyzer
from src.ml import trendLocator

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
# fmp_etl.update_market_cap(fmp_con, db_con, stat="historical-market-capitalization")
#fmp_etl.etl_fmp_stat(stat="enterprise-values", period="quarter")

from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score
from sklearn.metrics import plot_confusion_matrix
from sklearn.model_selection import train_test_split
import pickle
from src.ml import ml_utils

# X, y = stmnt_analyzer._stmnt_to_Xy(stmnt_analyzer._stmnt_prep_USD(), return_target=True)
# model = stmnt_analyzer.train_sttmnt_analyzer(X, y)
#
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33)
#
# y_pred_train = model.predict(X_train)
# y_pred_test = model.predict(X_test)
# cm_train = confusion_matrix(y_train, y_pred_train)
# cm_test = confusion_matrix(y_test, y_pred_test)
# print("train accur", accuracy_score(y_pred_train, y_train))
# print("test accur ",accuracy_score(y_pred_test, y_test))
# print(cm_train)
# print(cm_test)
#
# importance = pd.DataFrame(zip(model.feature_importances_, X_train.columns), columns = ["importance", "feature"]).set_index("feature")
# print(importance[importance["importance"]>0.01].sort_values("importance", ascending=False))
#
# #
# model_id = 'stmnt_binary_class'
# #
# ml_utils.save_model_in_db(model_id, model)
# pickle.dump(model, open(filename, 'wb'))
# loaded_model = pickle.load(open(filename, 'rb'))
#
# loaded_model = ml_utils.load_model_from_db(model_id)
# df = stmnt_analyzer._stmnt_prep_USD()
# X, y = stmnt_analyzer._stmnt_to_Xy(df, return_target=True)
#
# y_pred = loaded_model.predict(X)
# cm = confusion_matrix(y, y_pred)
# print("accur", accuracy_score(y_pred, y))
# print(cm)
# print(stmnt_analyzer.return_stmnt_scores(model_id))
#
# df["statement_score"] = loaded_model.predict_proba(X)[:, 1].round(4)
# print(df[df["symbol"] == "UPWK"][["ar_1_eps_sector_ratio", "statement_score", "revenuePerShare_sector_ratio", "ar_1_netIncomePerShare_sector_ratio", "ar_1_marketCap_sector_ratio"]])
#priceClustering.upload_clustering_df()


# fmp_etl.etl_fmp_candles("day")
#fmp_etl.etl_fmp_profiles()

# df = trendLocator._get_features().dropna()
# X, y_reg, y_class = trendLocator._features_to_Xy(df, return_target=True)
# print(X.columns)
# reg_model = trendLocator.train_trendLoc_reg_analyzer(X, y_reg)
# class_model = trendLocator.train_trendLoc_class_analyzer(X, y_class)
# ml_utils.save_model_in_db("trend_locator_12_reg", reg_model)
# ml_utils.save_model_in_db("trend_locator_12_class", class_model)

#trendLocator.upload_trend_scores("trend_locator_12_reg", "trend_locator_12_class")
#resp = tink_etl.t_con.show_portfolio()
tink_etl.etl_portfolio()
#print(resp.status_code)

# df = pd.DataFrame(resp.json()["payload"]["positions"])
# expected_yeild = pd.json_normalize(df.expectedYield)
# averagePositionPrice = pd.json_normalize(df.averagePositionPrice)
# df["currency"] = expected_yeild["currency"]
# df["averagePositionPrice"] = averagePositionPrice["value"]
# df["yeild"] = expected_yeild["value"]
# print(df.columns)
# print(df[['ticker', 'name', 'instrumentType', 'balance', 'lots', 'averagePositionPrice', 'yeild']])

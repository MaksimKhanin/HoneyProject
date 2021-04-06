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

X, y = stmnt_analyzer._stmnt_to_Xy(stmnt_analyzer._stmnt_prep_USD(), return_target=True)
model = stmnt_analyzer.train_sttmnt_analyzer(X, y)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33)

y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)
cm_train = confusion_matrix(y_train, y_pred_train)
cm_test = confusion_matrix(y_test, y_pred_test)
print("train accur", accuracy_score(y_pred_train, y_train))
print("test accur ",accuracy_score(y_pred_test, y_test))
print(cm_train)
print(cm_test)

importance = pd.DataFrame(zip(model.feature_importances_, X_train.columns), columns = ["importance", "feature"]).set_index("feature")
print(importance[importance["importance"]>0.01].sort_values("importance", ascending=False))

#
model_id = 'stmnt_binary_class'
#
ml_utils.save_model_in_db(model_id, model)
# pickle.dump(model, open(filename, 'wb'))
# loaded_model = pickle.load(open(filename, 'rb'))

loaded_model = ml_utils.load_model_from_db(model_id)
X = stmnt_analyzer._stmnt_to_Xy(stmnt_analyzer._stmnt_prep_USD(), return_target=False)

y_pred = loaded_model.predict(X)
cm = confusion_matrix(y, y_pred)
print("accur", accuracy_score(y_pred, y))
print(cm)
print(stmnt_analyzer.return_stmnt_scores(model_id))

stmnt_analyzer.upload_stmnt_scores_df(model_id)
#priceClustering.upload_clustering_df()
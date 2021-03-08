import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import time
from ..etl.connectors import PSQL_connector as db_con
from ..etl.logger.dag_logger import init_logger
from sklearn import preprocessing
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.decomposition import PCA
from . import ml_PSQL_queries as querylib


import pandas as pd
import numpy as np

############################
# Defining logger
############################

logger = init_logger("ml_enrich_logger")
logger.info("loading local .env")

############################
# Defining connectors
############################

load_dotenv()

############################
# Defining .env
############################

DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ["DB_PORT"]

NM_TRIES = 3

############################
# Defining connectors
############################

logger.info("Defining db connector")
db_con = db_con.PostgresConnector(DB_HOST, DB_PASSWORD, DB_PORT, DB_USER)

def get_data_from_db(query, params=None):
    cols, data = db_con.get_fetchAll(query, withColumns=True, params=params)
    return pd.DataFrame(data, columns=cols)

def df_to_return_matrix(dataframe):
    dataframe = dataframe.astype({"daily_return": "float64"})
    return_matrix = dataframe.groupby(['date','ticker'])["daily_return"].first().unstack().fillna(0).round(5)
    return return_matrix

def st_normilize_dataframe(return_matrix):
    normilizer = preprocessing.StandardScaler()
    return_matrix_norm = normilizer.fit_transform(return_matrix)
    return_matrix_norm = pd.DataFrame(return_matrix_norm, index=return_matrix.index, columns = return_matrix.columns)
    return return_matrix_norm

def hierarchy_cluster(return_matrix, distance=20):
    linked = linkage(return_matrix.T, 'complete')
    T = fcluster(linked, distance, criterion='distance')
    clusters  = pd.DataFrame(zip(return_matrix.columns, T), columns=["ticker", "cluster"]).set_index("ticker")
    return clusters

def PCA_matrix(matrix, n_components=10):
    pca = PCA(n_components=n_components)
    pca.fit(matrix)
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
    transformed = pca.fit_transform(matrix.T)
    pca_data = np.array((loadings[:, 0], loadings[:, 1], loadings[:, 2])).T
    pca_df = pd.DataFrame(pca_data, index = matrix.columns,
                          columns = ["pca_loading_0", "pca_loading_1", "pca_loading_2"])
    return pca_df

def upload_clustering_df():
    df = st_normilize_dataframe(df_to_return_matrix(get_data_from_db(querylib.GET_DAILY_RETURN)))
    clusters = hierarchy_cluster(df)
    PCA_loadings = PCA_matrix(df)
    df_to_upload = PCA_loadings.join(clusters, how='left').reset_index()
    db_con.insert_many(df_to_upload, "anl.ml_ticker_clustering")




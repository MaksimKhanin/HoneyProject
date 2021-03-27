
from ..etl.connectors import PSQL_connector as db_con
from sklearn import preprocessing
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.decomposition import PCA
from . import ml_PSQL_queries as querylib
from . import ml_utils
import pandas as pd
import numpy as np

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

def prep_cluster_df():
    df = st_normilize_dataframe(df_to_return_matrix(ml_utils.get_data_from_db(querylib.GET_DAILY_RETURN)))
    clusters = hierarchy_cluster(df)
    PCA_loadings = PCA_matrix(df)
    return PCA_loadings.join(clusters, how='left').reset_index()

def upload_clustering_df():
    ml_utils.upload_df_db(prep_cluster_df(), "anl.ml_ticker_clustering")








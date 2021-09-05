from datetime import datetime, timezone, timedelta
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.ensemble import GradientBoostingRegressor
from . import ml_PSQL_queries as querylib
from . import ml_utils
import pandas as pd

NON_FEATURE_COLUMNS = {"date", "ticker",
                       'target_12_reg', 'target_12_class',
                       'target_5_class', 'target_5_reg'}

def _transform_column_types(df):
    columns = df.columns
    stopColumns = {'ticker', 'date', 'name'}
    dateColumns = {"date"}
    for each_col in columns:
        if each_col in stopColumns:
            continue
        elif each_col in dateColumns:
            df[each_col] = df[each_col].astype("datetime64")
        else:
            df[each_col] = df[each_col].astype("float64").round(5)
    return df

def train_trendLoc_reg_analyzer(X, y):
    model = GradientBoostingRegressor(n_estimators=50, max_depth=5, subsample=0.8)
    model.fit(X, y)
    return model

def train_trendLoc_class_analyzer(X, y):
    model = GradientBoostingClassifier(n_estimators=50, max_depth=2, subsample=0.8)
    model.fit(X, y)
    return model

def _get_features():
    # quering data
    stmnts = ml_utils.get_data_from_db(querylib.QUERY_TREND_LOCATOR_FEATURES)
    Xy = _transform_column_types(stmnts)
    return Xy

def _features_to_Xy(Xy, return_target=True, y_col_reg = 'target_12_reg', y_col_class = 'target_12_class'):

    columns_to_drop = Xy.columns.intersection(NON_FEATURE_COLUMNS)
    X = Xy.drop(columns=columns_to_drop)

    # markTheTarget
    if return_target == True:
        Xy.dropna()
        y_reg = Xy[y_col_reg]
        y_class = Xy[y_col_class]
        return X, y_reg, y_class
    else:
        return X

def return_stmnt_scores(model_id_reg, model_id_class):

    df = _get_features()
    X = _features_to_Xy(df, return_target=False)

    X['date'] = df['date']
    X['ticker'] = df['ticker']
    X = X.dropna()
    df = X[['date', 'ticker']].copy()

    model_class = ml_utils.load_model_from_db(model_id_class)
    model_reg = ml_utils.load_model_from_db(model_id_reg)
    df["return_pred"] = model_reg.predict(X.drop(columns=['date', 'ticker'])).round(4)
    df["prob_pred"] = model_class.predict_proba(X.drop(columns=['date', 'ticker']))[:, 1].round(2)
    return df[["ticker", "date", "return_pred", "prob_pred"]].drop_duplicates(subset=["ticker", "date"])

def upload_trend_scores(model_id_reg, model_id_class):
    ml_utils.upload_df_db(return_stmnt_scores(model_id_reg, model_id_class), "ml.trend_locator")

from datetime import datetime, timezone, timedelta
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from . import ml_PSQL_queries as querylib
from . import ml_utils
import pandas as pd

NON_FEATURE_COLUMNS = {"date", "month", "year", "symbol",
                       "target", "marketCap_grow", "sector", "period",
                       "currency"}

def _transform_column_types(df):
    columns = df.columns
    stopColumns = {'symbol', 'time', 'currency', 'sector', 'period'}
    dateColumns = {"date"}
    for each_col in columns:
        if each_col in stopColumns:
            continue
        elif each_col in dateColumns:
            df[each_col] = df[each_col].astype("datetime64")
        else:
            df[each_col] = df[each_col].astype("float64").round(5)
    return df

def _create_mnth_year(df):
    df["month"] = df['date'].dt.month
    df["year"] = df['date'].dt.year
    return df

def train_sttmnt_analyzer(X, y):
    model = GradientBoostingClassifier(n_estimators=100, max_depth=2, max_features='sqrt', subsample=0.8)
    model.fit(X, y)
    return model


def _stmnt_prep_USD():

    stmnt_since_date = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0))) - timedelta(days=1095)

    # quering data
    stmnts = ml_utils.get_data_from_db(querylib.QUERY_STATEMENTS, params=(stmnt_since_date.isoformat(),'USD',))
    Xy = _transform_column_types(stmnts[(stmnts["marketCap"]>0)]).fillna(0).sort_values(["date", "symbol"])

    for each_col in Xy.columns:
        if each_col in NON_FEATURE_COLUMNS:
            continue
        else:
            Xy["ar_1_"+each_col] = (Xy[each_col] - Xy.groupby(["symbol"])[each_col].shift(1)) / Xy.groupby(["symbol"])[each_col].shift(1)

    sectors = Xy.copy()
    sectors["date"] = sectors["date"] + pd.DateOffset(months=1)
    sectors["month"] = sectors["date"].dt.month
    sectors["year"] = sectors["date"].dt.year

    sector_eps = sectors[["year", "month", "sector", "eps"]].groupby(["year","month", "sector"]).mean().reset_index().rename(columns={"eps":"sector_eps"})
    sector_ar1eps = sectors[["year", "month", "sector", "ar_1_eps"]].groupby(["year","month", "sector"]).mean().reset_index().rename(columns={"ar_1_eps":"sector_ar_1_eps"})
    sector_rps = sectors[["year", "month", "sector", "revenuePerShare"]].groupby(["year","month", "sector"]).mean().reset_index().rename(columns={"revenuePerShare":"sector_revenuePerShare"})
    sector_ar1rps = sectors[["year", "month", "sector", "ar_1_revenuePerShare"]].groupby(["year","month", "sector"]).mean().reset_index().rename(columns={"ar_1_revenuePerShare":"sector_ar_1_revenuePerShare"})
    sector_netIncPs = sectors[["year", "month", "sector", "netIncomePerShare"]].groupby(["year","month", "sector"]).mean().reset_index().rename(columns={"netIncomePerShare":"sector_netIncomePerShare"})
    sector_ar1netIncPs = sectors[["year", "month", "sector", "ar_1_netIncomePerShare"]].groupby(["year","month", "sector"]).mean().reset_index().rename(columns={"ar_1_netIncomePerShare":"sector_ar_1_netIncomePerShare"})
    sector_marketCap = sectors[["year", "month", "sector", "marketCap"]].groupby(["year","month", "sector"]).mean().reset_index().rename(columns={"marketCap":"sector_marketCap"})
    sector_ar1marketCap = sectors[["year", "month", "sector", "ar_1_marketCap"]].groupby(["year","month", "sector"]).mean().reset_index().rename(columns={"ar_1_marketCap":"sector_ar_1_marketCap"})

    Xy = Xy.set_index(["sector", "year", "month"])

    Xy = Xy.merge(sector_eps.set_index(["sector", "year", "month"]), how='inner', left_index=True, right_index=True)
    Xy = Xy.merge(sector_ar1eps.set_index(["sector", "year", "month"]), how='inner', left_index=True, right_index=True)
    Xy = Xy.merge(sector_rps.set_index(["sector", "year", "month"]), how='inner', left_index=True, right_index=True)
    Xy = Xy.merge(sector_ar1rps.set_index(["sector", "year", "month"]), how='inner', left_index=True, right_index=True)
    Xy = Xy.merge(sector_netIncPs.set_index(["sector", "year", "month"]), how='inner', left_index=True, right_index=True)
    Xy = Xy.merge(sector_ar1netIncPs.set_index(["sector", "year", "month"]), how='inner', left_index=True, right_index=True)
    Xy = Xy.merge(sector_marketCap.set_index(["sector", "year", "month"]), how='inner', left_index=True, right_index=True)
    Xy = Xy.merge(sector_ar1marketCap.set_index(["sector", "year", "month"]), how='inner', left_index=True, right_index=True).reset_index()

    Xy["eps_sector_ratio"] = (Xy["eps"] / Xy["sector_eps"]).round(2)
    Xy["ar_1_eps_sector_ratio"] = (Xy["ar_1_eps"] / Xy["sector_ar_1_eps"])
    Xy["revenuePerShare_sector_ratio"] = (Xy["revenuePerShare"] / Xy["sector_revenuePerShare"])
    Xy["ar_1_revenuePerShare_sector_ratio"] = (Xy["ar_1_revenuePerShare"] / Xy["sector_ar_1_revenuePerShare"])
    Xy["netIncomePerShare_sector_ratio"] = (Xy["netIncomePerShare"] / Xy["sector_netIncomePerShare"])
    Xy["ar_1_netIncomePerShare_sector_ratio"] = (Xy["ar_1_netIncomePerShare"] / Xy["sector_ar_1_netIncomePerShare"])
    Xy["marketCap_sector_ratio"] = (Xy["marketCap"] / Xy["sector_marketCap"])
    Xy["ar_1_marketCap_sector_ratio"] = (Xy["ar_1_marketCap"] / Xy["sector_ar_1_marketCap"])

    Xy.drop_duplicates(inplace=True)
    Xy.replace(-np.inf, -9999, inplace=True)
    Xy.replace(np.inf, 9999, inplace=True)
    Xy.fillna(0, inplace=True)

    return Xy

def _stmnt_to_Xy(Xy, return_target=True):

    columns_to_drop = Xy.columns.intersection(NON_FEATURE_COLUMNS)
    X = Xy.drop(columns=columns_to_drop)

    # markTheTarget
    if return_target == True:
        Xy['marketCap'] = Xy['marketCap'] / 1000000000
        Xy["marketCap_grow"] = Xy.groupby(["symbol"])['marketCap'].shift(-1) - Xy['marketCap']
        Xy.dropna()
        Xy["target"] = Xy["marketCap_grow"] > 0
        y = Xy["target"]
        return X, y
    else:
        return X

def return_stmnt_scores(model_id):
    df = _stmnt_prep_USD()
    X = _stmnt_to_Xy(df, return_target=False)
    model = ml_utils.load_model_from_db(model_id)
    df["statement_score"] = model.predict_proba(X)[:, 1].round(4)
    return df[["symbol", "date", "sector", "statement_score"]].drop_duplicates(subset=["symbol", "date"])

def upload_stmnt_scores_df(model_id):
    ml_utils.upload_df_db(return_stmnt_scores(model_id), "ml.stmnt_scores")
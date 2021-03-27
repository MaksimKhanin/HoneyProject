from dotenv import load_dotenv
import os
from . import ml_PSQL_queries as querylib


from ..etl.connectors import PSQL_connector as db_con
from ..etl.logger.dag_logger import init_logger

import pickle
import pandas as pd

############################
# Defining logger
############################

logger = init_logger("ml_stmnt_logger")
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

def save_model_in_db(model_id, model):
    pickle_string = pickle.dumps(model)
    db_con.perform_query(querylib.QUERY_INSERT_MODEL, (model_id, pickle_string,))

def load_model_from_db(model_id):
    binary = bytes(db_con.get_row(querylib.QUERY_GET_MODEL, (model_id,))[0])
    model = pickle.loads(binary)
    return model

def upload_df_db(data_frame, table_name):
    db_con.insert_many(data_frame, table_name)
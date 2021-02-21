from dotenv import load_dotenv
import os
from datetime import datetime
import dash_bootstrap_components as dbc
import flask
import dash
import dash_auth
import dash_core_components as dcc
from datetime import datetime, timedelta
from src.connectors import PSQL_connector as db_con
#from flask_caching import Cache
import pandas as pd

ENV_PATH = "./cfg/.env"
load_dotenv(ENV_PATH)

CACHE_TIMEOUT = 3600

DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ["DB_PORT"]
DASH_USERNAME_PASSWORD_PAIRS = eval(os.environ["DASH_USERNAME_PASSWORD_PAIRS"])
DASH_HEARTBEAT_SEC = os.environ["DASH_HEARTBEAT_SEC"]
INTERVAL_DELTA_UPDATE = timedelta(minutes=60)

# DASH BUTTONS = https://github.com/plotly/plotly.js/blob/master/src/components/modebar/buttons.js
# DASH CONFIG_OPTIONS = https://github.com/plotly/plotly.js/blob/master/src/plot_api/plot_config.js#L6
DEFAULT_GRAPH_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["toggleSpikelines",
                               "hoverCompareCartesian",
                               "select2d",
                               "lasso2d",
                               "pan2d",
                               "zoom2d",
                               "zoomIn2d",
                               "zoomOut2d",
                               "autoScale2d",
                               "resetScale2d",
                               "hoverClosestCartesian",
                               "hoverCompareCartesian",
                               "toggleSpikelines"],

    "modeBarButtonsToAdd": ["drawline",
                            "drawopenpath",
                            "drawcircle",
                            "drawrect",
                            "eraseshape"],
    "doubleClickDelay": 1000,
    "responsive": True,
    "scrollZoom": False

}

DASH_COLORS = {
    "blue": "#007bff",
    "indigo": "#6610f2",
    "purple": "#6f42c1",
    "pink": "#e83e8c",
    "red": "#ee5f5b",
    "orange": "#fd7e14",
    "yellow": "#f89406",
    "green": "#62c462",
    "teal": "#20c997",
    "cyan": "#5bc0de",
    "white": "#fff",
    "gray": "#7a8288",
    "gray-dark": "#3a3f44",
    "primary": "#3a3f44",
    "secondary": "#7a8288",
    "success": "#62c462",
    "info": "#5bc0de",
    "warning": "#f89406",
    "danger": "#ee5f5b",
    "light": "#e9ecef",
    "dark": "#272b30"
}

DB_CON = db_con.PostgresConnector(DB_HOST, DB_PASSWORD, DB_PORT, DB_USER)

#BS = https://www.bootstrapcdn.com/bootswatch/
server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.COSMO])
auth = dash_auth.BasicAuth(app, DASH_USERNAME_PASSWORD_PAIRS)
app.config.suppress_callback_exceptions = True
# cache = Cache(app.server, config={
#     'CACHE_TYPE': 'filesystem',
#     'CACHE_DIR': 'cache-directory'
# })


# @cache.memoize(timeout=CACHE_TIMEOUT)
# def get_data_from_db(query, params=None):
#     cols, data = DB_CON.get_fetchAll(query, withColumns=True, params=params)
#     df = pd.DataFrame(data, columns=cols)
#     return df.to_json()

def get_data_from_db(query, params=None):
    cols, data = DB_CON.get_fetchAll(query, withColumns=True, params=params)
    return pd.DataFrame(data, columns=cols)

def pd_date_to_timestamp(series):
    return series.astype("int64") // 10 ** 9

def prepare_slider_marks(date_array, step=86400):
    slider_date_marks = dict()
    for each_timestamp in range(date_array.min(), date_array.max(), step*5):

        slider_date_marks[each_timestamp] = {
            "label": datetime.fromtimestamp(each_timestamp).strftime("%Y-%m-%d"),
            "style": {
                "writing-mode": "vertical-rl",
                "height": 70}}
    return slider_date_marks
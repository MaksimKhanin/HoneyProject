from dotenv import load_dotenv
import os
from src.connectors import PSQL_connector as db_con
import src.PSQL_queries as querylib
import pandas as pd
import plotly.graph_objs as go

import dash
import dash_auth
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import numpy as np
import json
from datetime import datetime, date, time, timedelta, timezone
import flask

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


def create_date_slider(slider_id, date_array):
    step = 86400
    slider_date_marks = dict()
    for each_timestamp in range(date_range.min(), date_range.max(), step):
        if each_timestamp % (step*5) == 0:
            slider_date_marks[each_timestamp] = {
                "label": datetime.fromtimestamp(each_timestamp).strftime("%Y-%m-%d"),
                "style": {
                    "writing-mode": "vertical-rl",
                    "height": 70}}

    return dcc.RangeSlider(
            id=slider_id,
            min=date_array.min(),
            max=date_array.max(),
            value=[date_array.min(), date_array.max()],
            marks=slider_date_marks,
            step=step,
            included=True,
            allowCross=False)

#BS = https://www.bootstrapcdn.com/bootswatch/
server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.COSMO])
app.config.suppress_callback_exceptions = True


############################
#Defining connectors
############################
load_dotenv()

############################
#Defining .env
############################
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ["DB_PORT"]
USERNAME_PASSWORD_PAIRS = eval(os.environ["USERNAME_PASSWORD_PAIRS"])
auth = dash_auth.BasicAuth(app, USERNAME_PASSWORD_PAIRS)
db_con = db_con.PostgresConnector(DB_HOST, DB_PASSWORD, DB_PORT, DB_USER)
cols, data = db_con.get_fetchAll(querylib.GET_RAW_DAILY_PRICES, withColumns=True)
df = pd.DataFrame(data, columns=cols)

df = df.astype({
    "usd_daily_return": "float64",
    "daily_return": "float64",
    "close": "float64",
    "open": "float64",
    "high": "float64",
    "low": "float64"})

tickers = df["ticker"].unique()
sectors = df["sector"].unique()
#industries = df["industry"].unique()
currencies = df["currency"].unique()
csum_options = np.concatenate((tickers, sectors))

date_range = df["timestamp"].values.astype(int)

app.layout = html.Div([
    html.H1("Welcome to HoneyDashboard"),
    html.Div(
        dcc.Tabs([
            dcc.Tab(label="Tab one", children=[

                html.Div(create_date_slider("tab1-slider", date_range),
                         style={"margin-bottom": "50px", "margin-top": "30px"}),

                dcc.Checklist(
                    id='tab1-currency-selector',
                    options=[{'label': currency, 'value': currency} for currency in currencies],
                    value=["USD"],
                    labelStyle={'display': 'inline-block'}),

                dcc.Dropdown(id='tab1-return-selector',
                             options=[{'label': option, 'value': option} for option in csum_options],
                             value=["MSFT", "USDRUB", "Technology"],
                             multi=True),

                dcc.Graph(id='cum-return',
                          config=DEFAULT_GRAPH_CONFIG),

                dcc.Graph(id='uprising_table',
                          config=DEFAULT_GRAPH_CONFIG)]),



            dcc.Tab(label="Tab two", children=[

                html.Div(create_date_slider("tab2-slider", date_range),
                         style={"margin-bottom": "50px", "margin-top": "30px"}),

                dcc.Dropdown(id='ticker-selection',
                             options=[{'label': ticker, 'value': ticker} for ticker in tickers],
                             value='AAPL'),

                dcc.Graph(id='chart', config=DEFAULT_GRAPH_CONFIG)])]))

])

# @app.callback(
#     Output("my-dynamic-dropdown", "options"),
#     [Input("my-dynamic-dropdown", "search_value")],
# )
# def update_options(search_value):
#     if not search_value:
#         raise PreventUpdate
#     return [o for o in options if search_value in o["label"]]

@app.callback(Output('uprising_table', 'figure'),
              [Input('tab1-slider', 'value'),
               Input('tab1-currency-selector', 'value')])
def update_uprise_table(date_range, currency_options):
    datetime_min = date_range[0]
    datetime_max = date_range[1]
    chart_df = df[(df['currency'].isin(currency_options)) &
                  (datetime_min <= df['timestamp']) &
                  (datetime_max >= df['timestamp'])]

    chart_df = chart_df[["ticker", "name", "sector", "industry", "daily_return"]].\
        groupby(["ticker", "name", "sector", "industry"]).sum().\
        sort_values("daily_return", ascending=False).reset_index()

    return {"data":[go.Table(
        header={"values": chart_df.columns,
                "fill_color": 'paleturquoise',
                "align": "left"},
        cells={"values": [chart_df.ticker, chart_df.name, chart_df.sector, chart_df.industry, chart_df.daily_return],
                "fill_color": "lavender",
                "align":'left'})]}


@app.callback(
    Output('cum-return', 'figure'),
    [Input('tab1-slider', 'value'),
     Input('tab1-return-selector', 'value'),
     Input('tab1-currency-selector', 'value')])
def update_creturn(date_range, option_selector, currency_options):
    datetime_min = date_range[0]
    datetime_max = date_range[1]
    chart_df = df[(df['currency'].isin(currency_options)) &
                  (datetime_min <= df['timestamp']) &
                  (datetime_max >= df['timestamp'])]

    ticker_df = chart_df[["timestamp", "date", "ticker", "daily_return"]]. \
        groupby(["timestamp", "date", "ticker"]).mean().reset_index(). \
        rename(columns={"ticker": "option"})

    # industry_df = chart_df[["timestamp", "date", "industry", "daily_return"]]. \
    #     groupby(["timestamp", "date", "industry"]).mean().reset_index(). \
    #     rename(columns={"industry":"option"})

    sector_df = chart_df[["timestamp", "date", "sector", "daily_return"]]. \
        groupby(["timestamp", "date", "sector"]).mean().reset_index(). \
        rename(columns={"sector":"option"})

    ticker_df["daily_return"] = ticker_df["daily_return"].fillna(0)
    # industry_df["daily_return"] = industry_df["daily_return"].fillna(0)
    sector_df["daily_return"] = sector_df["daily_return"].fillna(0)

    ticker_df["cum_return"] = ticker_df[["option", "daily_return"]].groupby(['option']).cumsum()
    # industry_df["cum_return"] = industry_df[["option", "daily_return"]].groupby(['option']).cumsum()
    sector_df["cum_return"] = sector_df[["option", "daily_return"]].groupby(['option']).cumsum()

    cum_df = pd.concat([#industry_df[["date", "option", "cum_return"]],
                        sector_df[["date", "option", "cum_return"]],
                        ticker_df[["date", "option", "cum_return"]]])

    data = []
    for each_csum_opt in option_selector:
        new_line = cum_df[cum_df["option"] == each_csum_opt]
        data.append(
            go.Scattergl(
                x=new_line["date"],
                y=new_line["cum_return"],
                mode="lines",
                name=each_csum_opt)
        )
    return {
        'data': data,
        'layout': go.Layout(
            title='Chart',
            xaxis={'title': 'date', 'type': 'date', "fixedrange": True},
            yaxis={'title': '% return', "fixedrange": True}
        )
    }

@app.callback(
    Output('chart', 'figure'),
    [Input('ticker-selection', 'value'),
     Input('tab2-slider', 'value')])
def update_graph(ticker, date_range):
    datetime_min = date_range[0]
    datetime_max = date_range[1]
    chart_df = df[(df["ticker"] == ticker) & (datetime_min <= df['timestamp']) & (datetime_max >= df['timestamp'])]

    return {
        'data': [
            go.Candlestick(
                x=chart_df["date"],
                open=chart_df["open"],
                high=chart_df["high"],
                low=chart_df["low"],
                close=chart_df["close"],
            )
        ],
        'layout': go.Layout(
            title='Chart',
            xaxis={'title': 'date', 'type': 'date', "fixedrange": True, "rangeslider": {"visible": False}},
            yaxis={'title': 'price', "fixedrange": True}
        )
    }


app.run_server(host="0.0.0.0", port=8050, debug=False)

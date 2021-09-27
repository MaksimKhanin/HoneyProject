#from src.connectors import PSQL_connector as db_con
import src.PSQL_queries as querylib
import pandas as pd
import dash_bootstrap_components as dbc
import dash_table
from dash.exceptions import PreventUpdate

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import main_app
from main_app import app
import plotly.graph_objs as go
from datetime import datetime, timezone, timedelta
#from src.connectors import PSQL_connector as db_con

last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

tab1_df = main_app.get_data_from_db(querylib.GET_RAW_DAILY_RETURN)
tab1_df = tab1_df.astype({"daily_return": "float64",
                          "timestamp": "int64",
                          "date": "datetime64",
                          "currency": "category"})
currencies = tab1_df["currency"].unique()
date_range = tab1_df["timestamp"].values

tab1_pca_df = main_app.get_data_from_db(querylib.GET_PCA)
tab1_pca_df = tab1_pca_df.astype({"pca_loading_0": "float64","pca_loading_1": "float64"})

layout = html.Div([

    dcc.Interval(id='tab1-interval-update', interval=3600*1000, n_intervals=0),
    dbc.Row([
        dbc.Col(html.Div(id="tab1-last-update-info"), width={'size': 5,  "offset": 1, 'order': 1})]),
    dbc.Row(dbc.Col(
        html.Div(
            dcc.RangeSlider(id="tab1-slider", step=86400, included=True, allowCross=False),
            style={"margin-bottom": "50px", "margin-top": "30px"}),
        width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    html.Br(),
    dbc.Row([dbc.Col(
        dcc.Checklist(
            id='tab1-currency-selector',
            value=["USD"], persistence=True, persistence_type='local',
            labelStyle={'display': 'inline-block'}), width={'size': 3,  "offset": 1, 'order': 1})]),
    html.Br(),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dash_table.DataTable(
                id='daily-return-table',
                columns=[
                    {"name": i, "id": i} for i in ["ticker", "name", "sector", "industry", "cluster", "cumulative return"]
                ],
                editable=False,              # allow editing of data inside all cells
                cell_selectable=False,
                sort_by = [{"column_id": "cumulative return", "direction": "asc"}],
                filter_action="native",     # allow filtering of data by user ('native') or not ('none')
                sort_action="native",       # enables data to be sorted per-column by user or not ('none')
                sort_mode="single",         # sort across 'multi' or 'single' columns
                selected_columns=[],        # ids of columns that user selects
                selected_rows=[],           # indices of rows that user selects
                page_action="native",       # all data is passed to the table up-front or not ('none')
                page_current=0,             # page number that user is on
                page_size=10,                # number of rows visible per page
                style_cell={                # ensure adequate header width when text is shorter than cell's text
                    'minWidth': 95, 'maxWidth': 95, 'width': 95
                },
                style_cell_conditional=[    # align text columns to left. By default they are aligned to right
                    {
                        'if': {'column_id': c},
                        'textAlign': 'left'
                    } for c in ["ticker", "name", "sector", "industry", "cluster"]
                ],
                style_data={                # overflow cells' content into multiple lines
                    'whiteSpace': 'normal',
                    'height': 'auto'
                }), size="lg", color="primary", type="border", fullscreen=False),
        width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    dbc.Row([
        dbc.Col(html.H6("Sector selection:"), width={'size': 3,  "offset": 1, 'order': 1}),
        dbc.Col(html.H6("Cluster selection:"), width={'size': 3,  "offset": 0, 'order': 2}),
        dbc.Col(html.H6("Ticker selection:"), width={'size': 3,  "offset": 1, 'order': 3})]),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(id='tab1-sector-selector',
                         persistence=True, persistence_type='local',
                         multi=True), width={'size': 3,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Dropdown(id='tab1-cluster-selector',
                         persistence=True, persistence_type='local',
                         multi=True), width={'size': 3,  "offset": 0, 'order': 2}),
        dbc.Col(
            dcc.Dropdown(id='tab1-ticker-selector',
                         persistence=True, persistence_type='local',
                         multi=True), width={'size': 3,  "offset": 1, 'order': 3})]),
    html.Br(),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dcc.Graph(id='cum-return', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '600px'}),
            size="lg", color="primary", type="border", fullscreen=False)
        , width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    html.Br(),
    dbc.Row([
        dbc.Col(html.H6("Ticker Selection:"), width={'size': 5,  "offset": 1, 'order': 1})]),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(id='tab1-ticker-selector-2',
                         persistence=True, persistence_type='local',
                         multi=True), width={'size': 5,  "offset": 1, 'order': 1})]),

    dbc.Row(dbc.Col(
        dbc.Spinner(
            dcc.Graph(id='cum-return-portfolio', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '600px'}),
            size="lg", color="primary", type="border", fullscreen=False)
        , width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center')
])



@app.callback(
    Output("tab1-last-update-info", 'children'),
    [Input('tab1-interval-update', 'n_intervals')])
def get_tab1_data(n_intervals):
    global tab1_df
    global last_update_dttm
    global currencies
    global date_range

    current_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

    if (current_dttm - last_update_dttm) > main_app.INTERVAL_DELTA_UPDATE:

        last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))
        tab1_df = main_app.get_data_from_db(querylib.GET_RAW_DAILY_RETURN)
        tab1_df = tab1_df.astype({"daily_return": "float64",
                                  "timestamp": "int64",
                                  "date": "datetime64",
                                  "currency": "category"})
                                  #"ticker": "category",
                                  #"sector": "category",
                                  #"industry": "category",
                                  #"name": "category"})
        currencies = tab1_df["currency"].unique()
        date_range = tab1_df["timestamp"].values

    return f"Last update utc dttm {last_update_dttm}"

@app.callback(Output('tab1-currency-selector', 'options'),
              [Input('tab1-interval-update', 'n_intervals')])
def set_currency_selector(n_intervals):
    return [{'label': currency, 'value': currency} for currency in currencies]

@app.callback([Output('tab1-slider', 'min'),
               Output('tab1-slider', 'max'),
               Output('tab1-slider', 'value'),
               Output('tab1-slider', 'marks')],
              [Input('tab1-interval-update', 'n_intervals')])
def create_slider(n_intervals):
    marks = main_app.prepare_slider_marks(date_range)

    return date_range.min(), \
           date_range.max(), \
           (date_range.min(), date_range.max()), \
           marks

# @app.callback([Output('tab1-pca2-distance', 'min'),
#                Output('tab1-pca2-distance', 'max'),
#                Output('tab1-pca2-distance', 'step')],
#               [Input('tab1-interval-update', 'n_intervals')])
# def create_slider(n_intervals):
#     slider = tab1_pca_df["pca_loading_1"].abs()
#     step = (slider - slider.shift(1)).mean()
#     return slider.min(), \
#            slider.max(), \
#            step

@app.callback(Output('daily-return-table', 'data'),
              [Input('tab1-slider', 'value'),
               Input('tab1-currency-selector', 'value')])
def update_uprise_table(date_range, currency_options):
    if not date_range:
        raise PreventUpdate
    df = tab1_df
    datetime_min = date_range[0]
    datetime_max = date_range[1]
    chart_df = df[(df['currency'].isin(currency_options)) &
                  (datetime_min <= df['timestamp']) &
                  (datetime_max >= df['timestamp'])]

    chart_df = chart_df[["ticker", "name", "sector", "industry", "cluster", "daily_return"]]. \
        groupby(["ticker", "name", "sector", "industry", "cluster"]).sum().round(2). \
        sort_values("daily_return", ascending=False).reset_index()

    chart_df = chart_df.rename(columns = {"daily_return": "cumulative return"}). \
        set_index("ticker", drop=False)

    return chart_df.to_dict('records')

@app.callback(
    Output('tab1-sector-selector', 'options'),
    Input('daily-return-table', 'derived_virtual_data'))
def set_sector_options(data):
    if not data:
        raise PreventUpdate
    sectors = pd.DataFrame(data)["sector"].unique()
    return [{'label': i, 'value': i} for i in sectors]

# @app.callback(
#     Output('tab1-cluster-option', 'options'),
#     Input('daily-return-table', 'derived_virtual_data'))
# def set_cluster_options(data):
#     if not data:
#         raise PreventUpdate
#     clusters = pd.DataFrame(data)["cluster"].unique()
#     return [{'label': i, 'value': i} for i in clusters]

@app.callback(
    Output('tab1-ticker-selector', 'options'),
    Input('daily-return-table', 'derived_virtual_data'))
def set_ticker_options(data):
    if not data:
        raise PreventUpdate
    tickers = pd.DataFrame(data)["ticker"].unique()
    return [{'label': i, 'value': i} for i in tickers]

@app.callback(
    Output('tab1-cluster-selector', 'options'),
    Input('daily-return-table', 'derived_virtual_data'))
def set_cluster_options(data):
    if not data:
        raise PreventUpdate
    clusters = pd.DataFrame(data)["cluster"].unique()
    return [{'label': i, 'value': i} for i in clusters]

@app.callback(
    Output('tab1-ticker-selector-2', 'options'),
    Input('daily-return-table', 'derived_virtual_data'))
def set_ticker_options2(data):
    if not data:
        raise PreventUpdate
    tickers = pd.DataFrame(data)["ticker"].unique()
    return [{'label': i, 'value': i} for i in tickers]

@app.callback(
    Output('cum-return-portfolio', 'figure'),
    [Input('tab1-slider', 'value'),
     Input('tab1-ticker-selector-2', 'value')])
def update_cum_portfolio(date_range, ticker_selector):
    if not date_range:
        raise PreventUpdate
    df = tab1_df
    datetime_min = date_range[0]
    datetime_max = date_range[1]
    if not ticker_selector:
        ticker_selector = df["ticker"].unique()

    data_df = df[(df['ticker'].isin(ticker_selector)) &
                 (datetime_min <= df['timestamp']) &
                 (datetime_max >= df['timestamp'])]
    ticker_df = prep_cum_portfolio_graph(data_df, "ticker", ticker_selector)
    chart = {
        'data':[
            go.Scatter(x=ticker_df["date"],
                       y=ticker_df["daily_return"].round(2),
                       mode="lines")
        ],
        'layout': go.Layout(
            title='Portfolio return',
            height=600,
            xaxis={'title': 'date', 'type': 'date', "fixedrange": True},
            yaxis={'title': '% return', "fixedrange": True},
            showlegend=False)
    }
    return chart

@app.callback(
    Output('cum-return', 'figure'),
    [Input('tab1-slider', 'value'),
     Input('tab1-sector-selector', 'value'),
     Input('tab1-ticker-selector', 'value'),
     Input('tab1-currency-selector', 'value'),
     Input('tab1-cluster-selector', 'value')])
def update_creturn(date_range, sector_selector, ticker_selector, currency_options, cluster_selector):
    if not date_range:
        raise PreventUpdate
    df = tab1_df
    datetime_min = date_range[0]
    datetime_max = date_range[1]

    data_df = df[(df['currency'].isin(currency_options)) &
                 (datetime_min <= df['timestamp']) &
                 (datetime_max >= df['timestamp'])]

    ticker_df = pd.DataFrame(columns=["date", "option", "cum_return"])
    sector_df = pd.DataFrame(columns=["date", "option", "cum_return"])
    cluster_df = pd.DataFrame(columns=["date", "option", "cum_return"])
    if ticker_selector is not None:
        ticker_df = prep_cum_graph(data_df, "ticker", ticker_selector). \
            rename(columns={"ticker": "option"})
    if sector_selector is not None:
        sector_df = prep_cum_graph(data_df, "sector", sector_selector). \
            rename(columns={"sector": "option"})
    if cluster_selector is not None:
        cluster_df = prep_cum_graph(data_df, "sector", cluster_selector). \
            rename(columns={"cluster": "option"})

    cum_df = pd.concat([sector_df[["date", "option", "cum_return"]],
                        ticker_df[["date", "option", "cum_return"]],
                        cluster_df[["date", "option", "cum_return"]]])

    data = []
    for each_csum_opt in cum_df["option"].unique():
        new_line = cum_df[cum_df["option"] == each_csum_opt]
        data.append(
            go.Scatter(
                x=new_line["date"],
                y=new_line["cum_return"].round(2),
                mode="lines",
                name=each_csum_opt)
        )
    return {
        'data': data,
        'layout': go.Layout(
            title='Cumulative return',
            height=600,
            xaxis={'title': 'date', 'type': 'date', "fixedrange": True},
            yaxis={'title': '% return', "fixedrange": True}
        )
    }

def prep_cum_portfolio_graph(data, trace_name, trace_array):
    trace_df = data[data[trace_name].isin(trace_array)]
    trace_df = trace_df[["date", trace_name, "daily_return"]].groupby(["date", trace_name]).mean().reset_index()
    trace_df["daily_return"] = trace_df["daily_return"].fillna(0)
    portfolio_return = trace_df[["date", "daily_return"]].groupby(["date"]).mean()
    return portfolio_return.cumsum().reset_index()


def prep_cum_graph(data, trace_name, trace_array):
    trace_df = data[data[trace_name].isin(trace_array)]

    trace_df = trace_df[["timestamp", "date", trace_name, "daily_return"]]. \
        groupby(["timestamp", "date", trace_name]).mean().reset_index()

    trace_df["daily_return"] = trace_df["daily_return"].fillna(0)
    trace_df["cum_return"] = trace_df[[trace_name, "daily_return"]].groupby([trace_name]).cumsum()
    return trace_df

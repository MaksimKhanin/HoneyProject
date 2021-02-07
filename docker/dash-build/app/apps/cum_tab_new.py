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
from datetime import datetime

#df = main_app.get_data_from_db(querylib.GET_RAW_DAILY_RETURN)
#db_con = db_con.PostgresConnector(main_app.DB_HOST, main_app.DB_PASSWORD, main_app.DB_PORT, main_app.DB_USER)
#cols, data = db_con.get_fetchAll(querylib.GET_RAW_DAILY_RETURN, withColumns=True)
#df = pd.DataFrame(data, columns=cols)

#df = df.astype({"daily_return": "float64", "timestamp": "int64"})

# tickers = df["ticker"].unique()
# sectors = df["sector"].unique()
# currencies = df["currency"].unique()
#
# date_range = df["timestamp"].values

layout = html.Div([

    dcc.Interval(id='tab1-interval-update', interval=3600*1000, n_intervals=0),
    dbc.Spinner(
        html.Div(id='tab1-hidden-daily-return-data', style={'display': 'none'}),
                size="lg", color="primary", type="border", fullscreen=True),


    dbc.Row(dbc.Col(html.Div(id="tab1-slider",
             style={"margin-bottom": "50px", "margin-top": "30px"}), width={'size': 10,  "offset": 0, 'order': 1}),
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
                    {"name": i, "id": i} for i in ["ticker", "name", "sector", "industry", "cumulative return"]
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
                    } for c in ["ticker", "name", "sector", "industry"]
                ],
                style_data={                # overflow cells' content into multiple lines
                    'whiteSpace': 'normal',
                    'height': 'auto'
                }), size="lg", color="primary", type="border", fullscreen=False),
        width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    dbc.Row([
        dbc.Col(html.H6("Ticker selection:"), width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(html.H6("Sector selection:"), width={'size': 5,  "offset": 0, 'order': 2})]),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(id='tab1-sector-selector',
                         persistence=True, persistence_type='local',
                         multi=True), width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Dropdown(id='tab1-ticker-selector',
                         persistence=True, persistence_type='local',
                         multi=True), width={'size': 5,  "offset": 0, 'order': 2})]),
    html.Br(),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dcc.Graph(id='cum-return', config=main_app.DEFAULT_GRAPH_CONFIG),
            size="lg", color="primary", type="border", fullscreen=False)
                    , width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    ])


@app.callback(
    Output('tab1-hidden-daily-return-data', 'children'),
    [Input('tab1-interval-update', 'n_intervals')])
def get_tab1_data(n_intervals):
    price_df = main_app.get_data_from_db(querylib.GET_RAW_DAILY_RETURN)
    return price_df

@app.callback(Output('tab1-currency-selector', 'options'),
              [Input('tab1-hidden-daily-return-data', 'children')])
def set_currency_selector(main_data):
    if not main_data:
        raise PreventUpdate
    currencies = pd.read_json(main_data)["currency"].unique()
    return [{'label': currency, 'value': currency} for currency in currencies]

@app.callback(Output('tab1-slider', 'children'),
              [Input('tab1-hidden-daily-return-data', 'children')])
def create_slider(main_data):
    if not main_data:
        raise PreventUpdate
    date_range = main_app.pd_date_to_timestamp(pd.read_json(main_data)["timestamp"])
    return main_app.create_date_slider("tab1-slider", date_range)


@app.callback(Output('daily-return-table', 'data'),
              [Input('tab1-slider', 'value'),
               Input('tab1-currency-selector', 'value'),
               Input('tab1-hidden-daily-return-data', 'children')])
def update_uprise_table(date_range, currency_options, main_data):
    if not main_data or not date_range or not currency_options:
        raise PreventUpdate
    df = pd.read_json(main_data)
    df = df.astype({
        "timestamp": "int64",
        "daily_return": "float64"})
    df['timestamp'] = main_app.pd_date_to_timestamp(df['timestamp'])
    datetime_min = date_range[0]
    datetime_max = date_range[1]
    chart_df = df[(df['currency'].isin(currency_options)) &
                  (datetime_min <= df['timestamp']) &
                  (datetime_max >= df['timestamp'])]

    chart_df = chart_df[["ticker", "name", "sector", "industry", "daily_return"]]. \
        groupby(["ticker", "name", "sector", "industry"]).sum().round(2).\
        sort_values("daily_return", ascending=False).reset_index()

    chart_df = chart_df.rename(columns = {"daily_return": "cumulative return"}).\
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


@app.callback(
        Output('tab1-ticker-selector', 'options'),
        Input('daily-return-table', 'derived_virtual_data'))
def set_ticker_options(data):
    if not data:
        raise PreventUpdate
    tickers = pd.DataFrame(data)["ticker"].unique()
    return [{'label': i, 'value': i} for i in tickers]


@app.callback(
    Output('cum-return', 'figure'),
    [Input('tab1-slider', 'value'),
     Input('tab1-sector-selector', 'value'),
     Input('tab1-ticker-selector', 'value'),
     Input('tab1-currency-selector', 'value'),
     Input('tab1-hidden-daily-return-data', 'children')])
def update_creturn(date_range, sector_selector, ticker_selector, currency_options, main_data):
    if not main_data or not date_range or not currency_options or not ticker_selector or not sector_selector:
        raise PreventUpdate
    df = pd.read_json(main_data)
    df = df.astype({
        "timestamp": "int64",
        "daily_return": "float64"})
    df['timestamp'] = main_app.pd_date_to_timestamp(df['timestamp']).values
    datetime_min = date_range[0]
    datetime_max = date_range[1]

    data_df = df[(df['currency'].isin(currency_options)) &
                   (datetime_min <= df['timestamp']) &
                   (datetime_max >= df['timestamp'])]

    ticker_df = None
    sector_df = None
    if ticker_selector is not None:
        ticker_df = prep_cum_graph(data_df, "ticker", ticker_selector). \
            rename(columns={"ticker": "option"})
    if sector_selector is not None:
        sector_df = prep_cum_graph(data_df, "sector", sector_selector). \
            rename(columns={"sector": "option"})

    if ticker_df is None and sector_df is None:
        raise PreventUpdate
    elif sector_df is None:
        cum_df = ticker_df
    elif ticker_df is None:
        cum_df = sector_df
    else:
        cum_df = pd.concat([sector_df[["date", "option", "cum_return"]], ticker_df[["date", "option", "cum_return"]]])

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
            xaxis={'title': 'date', 'type': 'date', "fixedrange": True},
            yaxis={'title': '% return', "fixedrange": True}
        )
    }


def prep_cum_graph(data, trace_name, trace_array):
    trace_df = data[data[trace_name].isin(trace_array)]

    trace_df = trace_df[["timestamp", "date", trace_name, "daily_return"]]. \
        groupby(["timestamp", "date", trace_name]).mean().reset_index()

    trace_df["daily_return"] = trace_df["daily_return"].fillna(0)
    trace_df["cum_return"] = trace_df[[trace_name, "daily_return"]].groupby([trace_name]).cumsum()
    return trace_df

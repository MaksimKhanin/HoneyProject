import pandas as pd
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from main_app import app
import main_app
import plotly.graph_objs as go
from datetime import datetime
from src.connectors import PSQL_connector as db_con
import src.PSQL_queries as querylib

db_con = db_con.PostgresConnector(main_app.DB_HOST, main_app.DB_PASSWORD, main_app.DB_PORT, main_app.DB_USER)
cols, data = db_con.get_fetchAll(querylib.GET_RAW_CANDLES, withColumns=True)
candles_df = pd.DataFrame(data, columns=cols)

cols, data = db_con.get_fetchAll(querylib.GET_COMPANY_BALANCESHEET, withColumns=True)
balance_sheet_df = pd.DataFrame(data, columns=cols)
cols, data = db_con.get_fetchAll(querylib.GET_COMPANY_CASHFLOW, withColumns=True)
cash_flow_df = pd.DataFrame(data, columns=cols)
cols, data = db_con.get_fetchAll(querylib.GET_COMPANY_INCOMESTATEMENT, withColumns=True)
income_statement_df = pd.DataFrame(data, columns=cols)
cols, data = db_con.get_fetchAll(querylib.GET_COMPANY_KEYMETRICS, withColumns=True)
key_metrics_df = pd.DataFrame(data, columns=cols)

candles_df = candles_df.astype({
    "timestamp": "int64",
    "close": "float64",
    "open": "float64",
    "high": "float64",
    "low": "float64"})

tickers = candles_df["ticker"].unique()

date_range = candles_df["timestamp"].values.astype(int)


layout = html.Div([

    dbc.Row(dbc.Col(html.Div(main_app.create_date_slider("tab2-slider", date_range),
                             style={"margin-bottom": "50px", "margin-top": "30px"}),
                    width={'size': 10,  "offset": 0, 'order': 1}),
            justify='center', align='center'),
    html.Br(),
    dbc.Row([
        dbc.Col(html.H6("Sector selection:"), width={'size': 3,  "offset": 1, 'order': 1})],
        justify='left', align='center'),
    dbc.Row([
        dbc.Col(
                dcc.Dropdown(id='ticker-selection',
                    options=[{'label': ticker, 'value': ticker} for ticker in tickers],
                    value='AAPL', persistence=True, persistence_type='local'),
            width={'size': 3,  "offset": 1, 'order': 1})],
        justify='left', align='center'),
    html.Br(),
    dbc.Row([
        dbc.Col(
            dcc.Input(
                id="input-mv1", type="number", placeholder="0-200", inputMode="numeric",
                min=0, max=200, step=1, value=21, persistence=True, persistence_type='local'),
            width={'size': 3,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Input(
                id="input-mv2", type="number", placeholder="0-200", inputMode="numeric",
                min=0, max=200, step=1, value=50, persistence=True, persistence_type='local'),
            width={'size': 3,  "offset": 1, 'order': 2}),
        dbc.Col(
            dcc.Input(
                id="input-BB", type="number", placeholder="0-200", inputMode="numeric",
                min=0, max=200, step=1, value=50, persistence=True, persistence_type='local'),
            width={'size': 3,  "offset": 1, 'order': 3})],
        justify='center', align='center'),
    html.Br(),
    dbc.Row([
        dbc.Col(
            html.Div(id="tech-chart-info"), width={'size': 5,  "offset": 1, 'order': 1})],
        justify='left', align='center'),
    html.Br(),
    dbc.Row(
        dbc.Col(
            dbc.Spinner(dcc.Graph(id='chart', config=main_app.DEFAULT_GRAPH_CONFIG),
                        size="lg", color="primary", type="border", fullscreen=False),
            width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    html.Br(),
    dbc.Row(
        dbc.Col(
            dcc.RadioItems(
                id='period-selection',
                options=[
                    {'label': 'Year', 'value': 'Year'},
                    {'label': 'Quarter', 'value': 'Quarter'}
                ],
                value='Quarter',
                persistence=True, persistence_type='local'
            ), width={'size': 5,  "offset": 1, 'order': 1})),
    html.Br(),
    dbc.Row([
        dbc.Col(html.H6("Income statement report"), width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(html.H6("Cash flows report"), width={'size': 5,  "offset": 0, 'order': 2})]),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id='metric-INC-selection',
                options=[{'label': metric, 'value': metric} for metric in income_statement_df.columns.drop(["date", "symbol", "period"])],
                value="grossProfit", persistence=True, persistence_type='local'),
            width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Dropdown(
                id='metric-CF-selection',
                options=[{'label': metric, 'value': metric} for metric in cash_flow_df.columns.drop(["date", "symbol", "period"])],
                value="netIncome", persistence=True, persistence_type='local'),
            width={'size': 5,  "offset": 0, 'order': 2})
    ]),
    html.Br(),
    dbc.Row([
        dbc.Col(
            dbc.Spinner(dcc.Graph(id='INC-chart', config=main_app.DEFAULT_GRAPH_CONFIG),
                        size="lg", color="primary", type="border", fullscreen=False),
            width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(
            dbc.Spinner(dcc.Graph(id='CF-chart', config=main_app.DEFAULT_GRAPH_CONFIG),
                        size="lg", color="primary", type="border", fullscreen=False),
            width={'size': 5,  "offset": 0, 'order': 2})]),
    html.Br(),
    dbc.Row([
        dbc.Col(html.H6("Balance sheet reports"), width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(html.H6("Key Metrics"), width={'size': 5,  "offset": 0, 'order': 2})]),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id='metric-BS-selection',
                options=[{'label': metric, 'value': metric} for metric in balance_sheet_df.columns.drop(["date", "symbol", "period"])],
                value="cashAndCashEquivalents", persistence=True, persistence_type='local'),
            width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Dropdown(
                id='metric-KM-selection',
                options=[{'label': metric, 'value': metric} for metric in key_metrics_df.columns.drop(["date", "symbol", "period"])],
                value="revenuePerShare", persistence=True, persistence_type='local'),
            width={'size': 5,  "offset": 0, 'order': 2})
        ]),
    html.Br(),
    dbc.Row([
        dbc.Col(
            dbc.Spinner(dcc.Graph(id='BS-chart', config=main_app.DEFAULT_GRAPH_CONFIG),
                        size="lg", color="primary", type="border", fullscreen=False),
            width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(
            dbc.Spinner(dcc.Graph(id='KM-chart', config=main_app.DEFAULT_GRAPH_CONFIG),
                        size="lg", color="primary", type="border", fullscreen=False),
            width={'size': 5,  "offset": 0, 'order': 2})])])


@app.callback(
    Output('tech-chart-info', 'children'),
    [Input('ticker-selection', 'value'),
     Input('input-mv1', 'value'),
     Input('input-mv2', 'value'),
     Input('input-BB', 'value')])
def update_chart_info(ticker, mv1, mv2, bb):
    return f"""Ticker = {ticker} Moving averages 1 period = {mv1}; 
    Moving averages 2 period = {mv2} Bbands period = {bb}"""

@app.callback(
    Output('BS-chart', 'figure'),
    [Input('ticker-selection', 'value'),
     Input('metric-BS-selection', 'value'),
     Input('period-selection', 'value')])
def update_balance_sheet(ticker, metric, period):



    calc_df = balance_sheet_df[(balance_sheet_df["symbol"] == ticker) &
                               (balance_sheet_df["period"] == period)]


    return {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            xaxis={"fixedrange": True, "type":"date"},
                            yaxis={"fixedrange": True},
                            height=500)
    }

@app.callback(
    Output('CF-chart', 'figure'),
    [Input('ticker-selection', 'value'),
     Input('metric-CF-selection', 'value'),
     Input('period-selection', 'value')])
def update_cashflow_sheet(ticker, metric, period):


    calc_df =cash_flow_df[(cash_flow_df["symbol"] == ticker) &
                               (cash_flow_df["period"] == period)]

    return {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            xaxis={"fixedrange": True, "type":"date"},
                            yaxis={"fixedrange": True},
                            height=500)
    }

@app.callback(
    Output('INC-chart', 'figure'),
    [Input('ticker-selection', 'value'),
     Input('metric-INC-selection', 'value'),
     Input('period-selection', 'value')])
def update_income_state_sheet(ticker, metric, period):

    calc_df = income_statement_df[(income_statement_df["symbol"] == ticker) &
                          (income_statement_df["period"] == period)]

    return {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            xaxis={"fixedrange": True, "type":"date"},
                            yaxis={"fixedrange": True},
                            height=500)
    }

@app.callback(
    Output('KM-chart', 'figure'),
    [Input('ticker-selection', 'value'),
     Input('metric-KM-selection', 'value'),
     Input('period-selection', 'value')])
def update_key_metric_sheet(ticker, metric, period):

    calc_df = key_metrics_df[(key_metrics_df["symbol"] == ticker) &
                             (key_metrics_df["period"] == period)]

    return {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            xaxis={"fixedrange": True, "type":"date"},
                            yaxis={"fixedrange": True},
                            height=500)
    }

@app.callback(
    Output('chart', 'figure'),
    [Input('ticker-selection', 'value'),
     Input('tab2-slider', 'value'),
     Input('input-mv1', 'value'),
     Input('input-mv2', 'value'),
     Input('input-BB', 'value')])
def update_graph(ticker, date_range, mv1, mv2, bb):
    datetime_min = date_range[0]
    datetime_max = date_range[1]
    calc_df = candles_df[(candles_df["ticker"] == ticker)]

    chart_index = calc_df[(datetime_min <= candles_df['timestamp']) &
                       (datetime_max >= candles_df['timestamp'])].index

    chart = {
        'data': [go.Candlestick(
            x=calc_df["date"].loc[chart_index],
            open=calc_df["open"].loc[chart_index],
            high=calc_df["high"].loc[chart_index],
            low=calc_df["low"].loc[chart_index],
            close=calc_df["close"].loc[chart_index])],
        'layout': go.Layout(
            showlegend=False,
            #hovermode="closest",
            height=600,
            xaxis={'title': 'date',
                   'type': 'date',
                   "fixedrange": True,
                   "rangeslider": {"visible": False}},
            yaxis={'title': 'price',
                   "fixedrange": True,
                   "range":(
                       calc_df["low"].loc[chart_index].min()/1.1,
                       calc_df["high"].loc[chart_index].max()*1.1)}
        )
    }

    if mv1 != 0:
        mv_1 = calc_df["close"].rolling(mv1).mean()
        chart["data"].append(
            go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=mv_1.loc[chart_index],
                mode="lines",
                line={
                    "color":"#eb7d07", "width":2
                },
                name=f"Moving Average - {mv1}")
        )

    if mv2 != 0:
        mv_2 = calc_df["close"].rolling(mv2).mean()
        chart["data"].append(
            go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=mv_2.loc[chart_index],
                mode="lines",
                line={
                    "color":"#1207eb", "width":2
                },
                name=f"Moving Average - {mv2}")
        )
    if bb != 0:
        bb_mv = calc_df["close"].rolling(bb).mean()
        bb_std = calc_df["close"].rolling(bb).std()
        bb_up_lvl_1 = bb_mv + bb_std
        bb_down_lvl_1 = bb_mv - bb_std
        bb_up_lvl_2 = bb_mv + (bb_std*2)
        bb_down_lvl_2 = bb_mv - (bb_std*2)
        bb_up_lvl_3 = bb_mv + (bb_std*3)
        bb_down_lvl_3 = bb_mv - (bb_std*3)

        chart["data"].extend(
            [go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=bb_mv.loc[chart_index],
                hoverinfo='skip',
                line={
                    "color":"#32a852", "width": 2, "dash":"dash"
                },
                mode="lines",
                name="Bbands - baseline"),
            go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=bb_up_lvl_1.loc[chart_index],
                hoverinfo='skip',
                line={
                    "color":"#32a852", "width": 2, "dash":"dot"
                },
                mode="lines",
                name="Bbands x1 upper"),
            go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=bb_down_lvl_1.loc[chart_index],
                hoverinfo='skip',
                line={
                    "color":"#32a852", "width": 2, "dash":"dot"
                },
                mode="lines",
                name="Bbands x1 lower"),
            go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=bb_up_lvl_2.loc[chart_index],
                hoverinfo='skip',
                line={
                    "color":"#a8a232", "width": 2, "dash":"dot"
                },
                mode="lines",
                name="Bbands x2 upper"),
            go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=bb_down_lvl_2.loc[chart_index],
                hoverinfo='skip',
                line={
                    "color":"#a8a232", "width": 2, "dash":"dot"
                },
                mode="lines",
                name="Bbands x2 lower"),
            go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=bb_up_lvl_3.loc[chart_index],
                hoverinfo='skip',
                line={
                    "color":"#a83232", "width": 2, "dash":"dot"
                },
                mode="lines",
                name="Bbands x3 upper"),
            go.Scatter(
                x=calc_df["date"].loc[chart_index],
                y=bb_down_lvl_3.loc[chart_index],
                hoverinfo='skip',
                line={
                    "color":"#a83232", "width": 2, "dash":"dot"
                },
                mode="lines",
                name="Bbands x3 lower")]
        )
    return chart
import pandas as pd
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from main_app import app
import main_app
import plotly.graph_objs as go
from datetime import datetime, timezone, timedelta
import src.PSQL_queries as querylib
from dash.exceptions import PreventUpdate
#from src.connectors import PSQL_connector as db_con

# db_con = db_con.PostgresConnector(main_app.DB_HOST, main_app.DB_PASSWORD, main_app.DB_PORT, main_app.DB_USER)
# cols, data = db_con.get_fetchAll(querylib.GET_RAW_CANDLES, withColumns=True)
# candles_df = pd.DataFrame(data, columns=cols)
last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))
candles_df = main_app.get_data_from_db(querylib.GET_RAW_CANDLES)
#
# balance_sheet_df = main_app.get_data_from_db(querylib.GET_COMPANY_BALANCESHEET)
# cash_flow_df = main_app.get_data_from_db(querylib.GET_COMPANY_CASHFLOW)
# income_statement_df = main_app.get_data_from_db(querylib.GET_COMPANY_INCOMESTATEMENT)
# key_metrics_df = main_app.get_data_from_db(querylib.GET_COMPANY_KEYMETRICS)

# cols, data = db_con.get_fetchAll(querylib.GET_COMPANY_BALANCESHEET, withColumns=True)
# balance_sheet_df = pd.DataFrame(data, columns=cols)
# cols, data = db_con.get_fetchAll(querylib.GET_COMPANY_CASHFLOW, withColumns=True)
# cash_flow_df = pd.DataFrame(data, columns=cols)
# cols, data = db_con.get_fetchAll(querylib.GET_COMPANY_INCOMESTATEMENT, withColumns=True)
# income_statement_df = pd.DataFrame(data, columns=cols)
# cols, data = db_con.get_fetchAll(querylib.GET_COMPANY_KEYMETRICS, withColumns=True)
# key_metrics_df = pd.DataFrame(data, columns=cols)

candles_df = candles_df.astype({
    "timestamp": "int64",
    "close": "float64",
    "open": "float64",
    "high": "float64",
    "low": "float64"})

tickers = candles_df["ticker"].unique()

date_range = candles_df["timestamp"].values.astype(int)


layout = html.Div([
    dcc.Interval(id='tab2-interval-update', interval=3600*1000, n_intervals=0),
    dbc.Row([
        dbc.Col(html.Div(id="tab2-last-update-info"), width={'size': 5,  "offset": 1, 'order': 1})]),

    dbc.Row(dbc.Col(
        html.Div(
            dcc.RangeSlider(id="tab2-slider", step=86400, included=True, allowCross=False),
            style={"margin-bottom": "50px", "margin-top": "30px"}),
        width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    html.Br(),
    dbc.Row([
        dbc.Col(html.H6("Ticker selection:"), width={'size': 3,  "offset": 1, 'order': 1})],
        justify='left', align='center'),
    dbc.Row([
        dbc.Col(
                dcc.Dropdown(id='tab2-ticker-selector',
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
            dbc.Spinner(dcc.Graph(id='candle-chart', config=main_app.DEFAULT_GRAPH_CONFIG),
                        size="lg", color="primary", type="border", fullscreen=False),
            width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    html.Br(),
    # dbc.Row(
    #     dbc.Col(
    #         dcc.RadioItems(
    #             id='period-selection',
    #             options=[
    #                 {'label': 'Year', 'value': 'Year'},
    #                 {'label': 'Quarter', 'value': 'Quarter'}
    #             ],
    #             value='Quarter',
    #             persistence=True, persistence_type='local'
    #         ), width={'size': 5,  "offset": 1, 'order': 1})),
    # html.Br(),
    #     dbc.Row([
    #         dbc.Col(html.H6("Income statement report"), width={'size': 5,  "offset": 1, 'order': 1}),
    #         dbc.Col(html.H6("Cash flows report"), width={'size': 5,  "offset": 0, 'order': 2})]),
    #     dbc.Row([
    #         dbc.Col(
    #             dcc.Dropdown(
    #                 id='metric-INC-selection',
    #                 value="grossProfit", persistence=True, persistence_type='local'),
    #             width={'size': 5,  "offset": 1, 'order': 1}),
    #         dbc.Col(
    #             dcc.Dropdown(
    #                 id='metric-CF-selection',
    #                 value="netIncome", persistence=True, persistence_type='local'),
    #             width={'size': 5,  "offset": 0, 'order': 2})
    #     ]),
    #     html.Br(),
    #     dbc.Row([
    #         dbc.Col(
    #             dbc.Spinner(dcc.Graph(id='INC-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
    #                         size="lg", color="primary", type="border", fullscreen=False),
    #             width={'size': 5,  "offset": 1, 'order': 1}),
    #         dbc.Col(
    #             dbc.Spinner(dcc.Graph(id='CF-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
    #                         size="lg", color="primary", type="border", fullscreen=False),
    #             width={'size': 5,  "offset": 0, 'order': 2})]),
    #     html.Br(),
    #     dbc.Row([
    #         dbc.Col(html.H6("Balance sheet reports"), width={'size': 5,  "offset": 1, 'order': 1}),
    #         dbc.Col(html.H6("Key Metrics"), width={'size': 5,  "offset": 0, 'order': 2})]),
    #     dbc.Row([
    #         dbc.Col(
    #             dcc.Dropdown(
    #                 id='metric-BS-selection',
    #                 value="cashAndCashEquivalents", persistence=True, persistence_type='local'),
    #             width={'size': 5,  "offset": 1, 'order': 1}),
    #         dbc.Col(
    #             dcc.Dropdown(
    #                 id='metric-KM-selection',
    #                 value="revenuePerShare", persistence=True, persistence_type='local'),
    #             width={'size': 5,  "offset": 0, 'order': 2})
    #         ]),
    #     html.Br(),
    #     dbc.Row([
    #         dbc.Col(
    #             dbc.Spinner(dcc.Graph(id='BS-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
    #                         size="lg", color="primary", type="border", fullscreen=False),
    #             width={'size': 5,  "offset": 1, 'order': 1}),
    #         dbc.Col(
    #             dbc.Spinner(dcc.Graph(id='KM-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
    #                         size="lg", color="primary", type="border", fullscreen=False),
    #             width={'size': 5,  "offset": 0, 'order': 2})])
])

@app.callback(
    Output("tab2-last-update-info", 'children'),
    [Input('tab2-interval-update', 'n_intervals')])
def get_tab2_data(n_intervals):
    global candles_df
    global last_update_dttm
    global tickers
    global date_range

    current_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

    if (current_dttm - last_update_dttm) > main_app.INTERVAL_DELTA_UPDATE:

        last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))
        candles_df = main_app.get_data_from_db(querylib.GET_RAW_CANDLES)
        candles_df = candles_df.astype({
            "timestamp": "int64",
            "close": "float64",
            "open": "float64",
            "high": "float64",
            "low": "float64"})
        tickers = candles_df["ticker"].unique()
        date_range = candles_df["timestamp"].values

        # balance_sheet_df = main_app.get_data_from_db(querylib.GET_COMPANY_BALANCESHEET)
        # cash_flow_df = main_app.get_data_from_db(querylib.GET_COMPANY_CASHFLOW)
        # income_statement_df = main_app.get_data_from_db(querylib.GET_COMPANY_INCOMESTATEMENT)
        # key_metrics_df = main_app.get_data_from_db(querylib.GET_COMPANY_KEYMETRICS)

    return f"Last update utc dttm {last_update_dttm}"

# @app.callback(
#     Output('tab2-hidden-candles-data', 'children'),
#     [Input('tab2-interval-update', 'n_intervals')])
# def get_tab2_candles(n_intervals):
#     return main_app.get_data_from_db(querylib.GET_RAW_CANDLES)

@app.callback([Output('tab2-slider', 'min'),
               Output('tab2-slider', 'max'),
               Output('tab2-slider', 'value'),
               Output('tab2-slider', 'marks')],
              [Input('tab2-interval-update', 'n_intervals')])
def create_slider(n_intervals):
    marks = main_app.prepare_slider_marks(date_range)
    return date_range.min(), \
           date_range.max(), \
           (date_range.min(), date_range.max()), \
           marks

#
# @app.callback(
#     Output('tab2-BS-data', 'children'),
#     [Input('tab2-interval-update', 'n_intervals'),
#      Input('tab2-ticker-selector', 'value')])
# def get_tab2_BS(n_intervals, ticker):
#     if not ticker:
#         raise PreventUpdate
#     return main_app.get_data_from_db(querylib.GET_COMPANY_BALANCESHEET, params=(ticker,))
#
# @app.callback(
#     Output('tab2-CF-data', 'children'),
#     [Input('tab2-interval-update', 'n_intervals'),
#      Input('tab2-ticker-selector', 'value')])
# def get_tab2_CF(n_intervals, ticker):
#     if not ticker:
#         raise PreventUpdate
#     return main_app.get_data_from_db(querylib.GET_COMPANY_CASHFLOW, params=(ticker,))
#
# @app.callback(
#     Output('tab2-INC-data', 'children'),
#     [Input('tab2-interval-update', 'n_intervals'),
#      Input('tab2-ticker-selector', 'value')])
# def get_tab2_INC(n_intervals, ticker):
#     if not ticker:
#         raise PreventUpdate
#     return main_app.get_data_from_db(querylib.GET_COMPANY_INCOMESTATEMENT, params=(ticker,))
#
# @app.callback(
#     Output('tab2-KM-data', 'children'),
#     [Input('tab2-interval-update', 'n_intervals'),
#      Input('tab2-ticker-selector', 'value')])
# def get_tab2_KM(n_intervals, ticker):
#     if not ticker:
#         raise PreventUpdate
#     return main_app.get_data_from_db(querylib.GET_COMPANY_KEYMETRICS, params=(ticker,))

#
# @app.callback(Output('tab2-slider', 'children'),
#               [Input('tab2-hidden-candles-data', 'children')])
# def create_slider(main_data):
#     if not main_data:
#         raise PreventUpdate
#     date_range = main_app.pd_date_to_timestamp(pd.read_json(main_data)["timestamp"])
#     return main_app.create_date_slider("tab2-slider", date_range)

# @app.callback(
#     Output('tab2-ticker-selector', 'options'),
#     [Input('tab2-hidden-candles-data', 'children')])
# def set_ticker_options(main_data):
#     if not main_data:
#         raise PreventUpdate
#     tickers = pd.read_json(main_data)["ticker"]
#     return [{'label': i, 'value': i} for i in tickers]

@app.callback(Output('tab2-ticker-selector', 'options'),
              [Input('tab2-interval-update', 'n_intervals')])
def set_currency_selector(n_intervals):
    return [{'label': ticker, 'value': ticker} for ticker in tickers]

@app.callback(
    Output('tech-chart-info', 'children'),
    [Input('tab2-ticker-selector', 'value'),
     Input('input-mv1', 'value'),
     Input('input-mv2', 'value'),
     Input('input-BB', 'value')])
def update_chart_info(ticker, mv1, mv2, bb):
    return f"""Ticker = {ticker} Moving averages 1 period = {mv1}; 
    Moving averages 2 period = {mv2} Bbands period = {bb}"""
#
# @app.callback(
#     Output('BS-chart', 'figure'),
#     [Input('tab2-ticker-selector', 'value'),
#      Input('metric-BS-selection', 'value'),
#      Input('period-selection', 'value'),
#      Input('tab2-BS-data', 'children')])
# def update_balance_sheet(ticker, metric, period, main_data):
#     if period or not ticker or not metric:
#         raise PreventUpdate
#     df = pd.read_json(main_data)
#     calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)]
#
#     return {
#         'data': [go.Bar(
#             x=calc_df["date"],
#             y=calc_df[metric])],
#         'layout': go.Layout(showlegend=False,
#                             xaxis={"fixedrange": True, "type":"date"},
#                             yaxis={"fixedrange": True},
#                             height=500)
#     }
#
# @app.callback(
#     Output('metric-BS-selection', 'options'),
#     Input('tab2-BS-data', 'children'))
# def set_ticker_options(data):
#     if not data:
#         raise PreventUpdate
#     metrics = pd.read_json(data).columns.drop(["date", "symbol", "period"])
#     return [{'label': metric, 'value': metric} for metric in metrics]
#
# @app.callback(
#     Output('CF-chart', 'figure'),
#     [Input('tab2-ticker-selector', 'value'),
#      Input('metric-CF-selection', 'value'),
#      Input('period-selection', 'value'),
#      Input('tab2-CF-data', 'children')])
# def update_cash_sheet(ticker, metric, period, main_data):
#     if not main_data or not period or not ticker or not metric:
#         raise PreventUpdate
#     df = pd.read_json(main_data)
#     calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)]
#     return {
#         'data': [go.Bar(
#             x=calc_df["date"],
#             y=calc_df[metric])],
#         'layout': go.Layout(showlegend=False,
#                             xaxis={"fixedrange": True, "type":"date"},
#                             yaxis={"fixedrange": True},
#                             height=500)
#     }
#
# @app.callback(
#     Output('metric-CF-selection', 'options'),
#     Input('tab2-CF-data', 'children'))
# def set_ticker_options(data):
#     if not data:
#         raise PreventUpdate
#     metrics = pd.read_json(data).columns.drop(["date", "symbol", "period"])
#     return [{'label': metric, 'value': metric} for metric in metrics]
#
# @app.callback(
#     Output('INC-chart', 'figure'),
#     [Input('tab2-ticker-selector', 'value'),
#      Input('metric-INC-selection', 'value'),
#      Input('period-selection', 'value'),
#      Input('tab2-INC-data', 'children')])
# def update_income_sheet(ticker, metric, period, main_data):
#     if not main_data or not period or not ticker or not metric:
#         raise PreventUpdate
#     df = pd.read_json(main_data)
#     calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)]
#     return {
#         'data': [go.Bar(
#             x=calc_df["date"],
#             y=calc_df[metric])],
#         'layout': go.Layout(showlegend=False,
#                             xaxis={"fixedrange": True, "type":"date"},
#                             yaxis={"fixedrange": True},
#                             height=500)
#     }
#
# @app.callback(
#     Output('metric-INC-selection', 'options'),
#     Input('tab2-INC-data', 'children'))
# def set_ticker_options(data):
#     if not data:
#         raise PreventUpdate
#     metrics = pd.read_json(data).columns.drop(["date", "symbol", "period"])
#     return [{'label': metric, 'value': metric} for metric in metrics]
#
# @app.callback(
#     Output('KM-chart', 'figure'),
#     [Input('tab2-ticker-selector', 'value'),
#      Input('metric-KM-selection', 'value'),
#      Input('period-selection', 'value'),
#      Input('tab2-KM-data', 'children')])
# def update_income_sheet(ticker, metric, period, main_data):
#     if not main_data or not period or not ticker or not metric:
#         raise PreventUpdate
#     df = pd.read_json(main_data)
#     calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)]
#     return {
#         'data': [go.Bar(
#             x=calc_df["date"],
#             y=calc_df[metric])],
#         'layout': go.Layout(showlegend=False,
#                             xaxis={"fixedrange": True, "type": "date"},
#                             yaxis={"fixedrange": True},
#                             height=500)
#     }
#
# @app.callback(
#     Output('metric-KM-selection', 'options'),
#     Input('tab2-KM-data', 'children'))
# def set_ticker_options(data):
#     if not data:
#         raise PreventUpdate
#     metrics = pd.read_json(data).columns.drop(["date", "symbol", "period"])
#     return [{'label': metric, 'value': metric} for metric in metrics]

@app.callback(
    Output('candle-chart', 'figure'),
    [Input('tab2-ticker-selector', 'value'),
     Input('tab2-slider', 'value'),
     Input('input-mv1', 'value'),
     Input('input-mv2', 'value'),
     Input('input-BB', 'value')])
def update_graph(ticker, date_range, mv1, mv2, bb):

    if not date_range or not ticker:
        raise PreventUpdate
    df = candles_df
    df = df.astype({
        "timestamp": "int64",
        "close": "float64",
        "open": "float64",
        "high": "float64",
        "low": "float64"})

    datetime_min = date_range[0]
    datetime_max = date_range[1]
    calc_df = df[(df["ticker"] == ticker)]

    chart_index = calc_df[(datetime_min <= df['timestamp']) &
                          (datetime_max >= df['timestamp'])].index

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

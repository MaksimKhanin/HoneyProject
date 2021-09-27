import pandas as pd
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output
from main_app import app
import main_app
import plotly.graph_objs as go
from datetime import datetime, timezone, timedelta
import src.PSQL_queries as querylib
from dash.exceptions import PreventUpdate

last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

tech_monitoring_df = main_app.get_data_from_db(querylib.GET_ML_SCORES_FOR_TODAY)
tech_monitoring_df = tech_monitoring_df.astype({"date": "datetime64",
                                "z_50_close": "float64",
                                "return_pred": "float64",
                                "prob_pred": "float64",
                                "target_price": "float64",
                                "statement_score": "float64"})

candles_df = main_app.get_data_from_db(querylib.GET_RAW_CANDLES)
candles_df = candles_df.astype({"timestamp": "int64",
                                "date": "datetime64",
                                "close": "float64",
                                "open": "float64",
                                "high": "float64",
                                "low": "float64"})

tickers = candles_df["ticker"].unique()
date_range = candles_df["timestamp"]

layout = html.Div([
    dcc.Interval(id='tab2-interval-update', interval=3600*1000, n_intervals=0),
    dbc.Row([
        dbc.Col(html.Div(id="tab2-last-update-info"), width={'size': 5,  "offset": 1, 'order': 1})]),

    html.Br(),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dash_table.DataTable(
                id='tech-tab-ml-agg',
                columns=[
                    {"name": i, "id": i} for i in ["Date", "Ticker", "Sector",
                                                   "Cluster", "z_score", "Target Price",
                                                   "Expected Return", "Trend Score", "Statement Score"]
                ],
                editable=False,              # allow editing of data inside all cells
                cell_selectable=False,
                sort_by = [{"column_id": "Trend Score", "direction": "desc"}],
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
                    } for c in ["Date", "Ticker", "Sector", "Statement Score"]
                ],
                style_data={                # overflow cells' content into multiple lines
                    'whiteSpace': 'normal',
                    'height': 'auto'
                }), size="lg", color="primary", type="border", fullscreen=False),
        width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    html.Br(),

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
    global tech_monitoring_df

    current_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

    if (current_dttm - last_update_dttm) > main_app.INTERVAL_DELTA_UPDATE:

        last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))
        candles_df = main_app.get_data_from_db(querylib.GET_RAW_CANDLES)
        candles_df = candles_df.astype({"timestamp": "int64",
                                        "date": "datetime64",
                                        "close": "float64",
                                        "open": "float64",
                                        "high": "float64",
                                        "low": "float64"})

        tech_monitoring_df = main_app.get_data_from_db(querylib.GET_ML_SCORES_FOR_TODAY)
        tech_monitoring_df = tech_monitoring_df.astype({"date": "datetime64",
                                                        "z_50_close": "float64",
                                                        "return_pred": "float64",
                                                        "prob_pred": "float64",
                                                        "target_price": "float64",
                                                        "statement_score": "float64"})

        tickers = candles_df["ticker"].unique()
        date_range = candles_df["timestamp"].values


    return f"Last update utc dttm {last_update_dttm}"

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

@app.callback(Output('tech-tab-ml-agg', 'data'),
              [Input('tab2-interval-update', 'n_intervals')])
def update_stmnts_score_table(n_intervals):
    chart_df = tech_monitoring_df

    chart_df["statement_score"] = chart_df["statement_score"].round(2)
    # chart_df["date"] = pd.to_datetime(chart_df["date"]).dt.strftime('%Y-%m-%d')
    chart_df = chart_df.rename(columns = {
        "ticker": "Ticker",
        "sector" : "Sector",
        "date" : "Date",
        "z_50_close" : "z_score",
        "cluster": "Cluster",
        "return_pred": "Expected Return",
        "target_price": "Target Price",
        "statement_score" : "Statement Score",
        "prob_pred": "Trend Score"

    })
    chart_df["z_score"] = chart_df["z_score"].round(2)
    chart_df["Expected Return"] = chart_df["Expected Return"].round(2)
    chart_df["Trend Score"] = chart_df["Trend Score"].round(2)
    chart_df["Statement Score"] = chart_df["Statement Score"].round(2)

    return chart_df.to_dict('records')

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
calendar_df = main_app.get_data_from_db(querylib.GET_EARNINGS_CALENDAR)
calendar_df = calendar_df.astype({"date": "datetime64",
                          "eps": "float64",
                          "epsEstimated": "float64",
                          "revenue": "float64",
                          "revenueEstimated": "float64"})
tickers = calendar_df["symbol"].unique()

balance_sheet_df = main_app.get_data_from_db(querylib.GET_COMPANY_BALANCESHEET)
cash_flow_df = main_app.get_data_from_db(querylib.GET_COMPANY_CASHFLOW)
income_statement_df = main_app.get_data_from_db(querylib.GET_COMPANY_INCOMESTATEMENT)
key_metrics_df = main_app.get_data_from_db(querylib.GET_COMPANY_KEYMETRICS)

layout = html.Div([
    dcc.Interval(id='fundtab-interval-update', interval=3600*1000, n_intervals=0),
    dbc.Row([
        dbc.Col(html.Div(id="fundtab-last-update-info"),
                width={'size': 5,  "offset": 1, 'order': 1})]),
    html.Br(),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dash_table.DataTable(
                id='fundtab-earnings-calendar-table',
                columns=[
                    {"name": i, "id": i} for i in ["date", "ticker", "eps", "epsEstimated", "revenue", "revenueEstimated"]
                ],
                editable=False,              # allow editing of data inside all cells
                cell_selectable=False,
                sort_by = [{"column_id": "date", "direction": "asc"}],
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
                    } for c in ["date", "ticker", "eps", "epsEstimated", "revenue", "revenueEstimated"]
                ],
                style_data={                # overflow cells' content into multiple lines
                    'whiteSpace': 'normal',
                    'height': 'auto'
                }), size="lg", color="primary", type="border", fullscreen=False),
        width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(id='fundtab-ticker-selector', value="AAPL",
                         persistence=True, persistence_type='local'),
            width={'size': 5,  "offset": 1, 'order': 1})]),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dcc.Graph(id='fundtab-eps-chart',
                      config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '600px'}),
            size="lg", color="primary", type="border", fullscreen=False),
        width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    dbc.Row(
        dbc.Col(
            dcc.RadioItems(
                id='fundtab-period-selection',
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
                    id='fundtab-metric-INC-selection',
                    value="grossProfit", persistence=True, persistence_type='local'),
                width={'size': 5,  "offset": 1, 'order': 1}),
            dbc.Col(
                dcc.Dropdown(
                    id='fundtab-metric-CF-selection',
                    value="netIncome", persistence=True, persistence_type='local'),
                width={'size': 5,  "offset": 0, 'order': 2})
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col(
                dbc.Spinner(dcc.Graph(id='fundtab-INC-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
                            size="lg", color="primary", type="border", fullscreen=False),
                width={'size': 5,  "offset": 1, 'order': 1}),
            dbc.Col(
                dbc.Spinner(dcc.Graph(id='fundtab-CF-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
                            size="lg", color="primary", type="border", fullscreen=False),
                width={'size': 5,  "offset": 0, 'order': 2})]),
        html.Br(),
        dbc.Row([
            dbc.Col(html.H6("Balance sheet reports"), width={'size': 5,  "offset": 1, 'order': 1}),
            dbc.Col(html.H6("Key Metrics"), width={'size': 5,  "offset": 0, 'order': 2})]),
        html.Br(),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id='fundtab-metric-BS-selection',
                    value="cashAndCashEquivalents", persistence=True, persistence_type='local'),
                width={'size': 5,  "offset": 1, 'order': 1}),
            dbc.Col(
                dcc.Dropdown(
                    id='fundtab-metric-KM-selection',
                    value="revenuePerShare", persistence=True, persistence_type='local'),
                width={'size': 5,  "offset": 0, 'order': 2})
            ]),
        html.Br(),
        dbc.Row([
            dbc.Col(
                dbc.Spinner(dcc.Graph(id='fundtab-BS-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
                            size="lg", color="primary", type="border", fullscreen=False),
                width={'size': 5,  "offset": 1, 'order': 1}),
            dbc.Col(
                dbc.Spinner(dcc.Graph(id='fundtab-KM-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
                            size="lg", color="primary", type="border", fullscreen=False),
                width={'size': 5,  "offset": 0, 'order': 2})])
])

@app.callback(Output('fundtab-ticker-selector', 'options'),
              [Input('fundtab-interval-update', 'n_intervals')])
def tab3_set_ticker_selector3(n_intervals):
    return [{'label': ticker, 'value': ticker} for ticker in tickers]

@app.callback(
    Output("fundtab-last-update-info", 'children'),
    [Input('fundtab-interval-update', 'n_intervals')])
def get_fund_data(n_intervals):
    global calendar_df
    global last_update_dttm
    global tickers
    global balance_sheet_df
    global cash_flow_df
    global income_statement_df
    global key_metrics_df

    current_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

    if (current_dttm - last_update_dttm) > main_app.INTERVAL_DELTA_UPDATE:

        last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))
        calendar_df = main_app.get_data_from_db(querylib.GET_EARNINGS_CALENDAR)
        calendar_df = calendar_df.astype({"date": "datetime64",
                                          "eps": "float64",
                                          "epsEstimated": "float64",
                                          "revenue": "float64",
                                          "revenueEstimated": "float64"})
        tickers = calendar_df["symbol"].unique()

        balance_sheet_df = main_app.get_data_from_db(querylib.GET_COMPANY_BALANCESHEET)
        cash_flow_df = main_app.get_data_from_db(querylib.GET_COMPANY_CASHFLOW)
        income_statement_df = main_app.get_data_from_db(querylib.GET_COMPANY_INCOMESTATEMENT)
        key_metrics_df = main_app.get_data_from_db(querylib.GET_COMPANY_KEYMETRICS)

    return f"Last update utc dttm {last_update_dttm}"

@app.callback([Output('fundtab-earnings-calendar-table', 'data'),
               Output('fundtab-earnings-calendar-table', 'filter_query')],
              [Input('fundtab-interval-update', 'n_intervals')])
def update_calendar_table(n_intervals):
    chart_df = calendar_df

    chart_df["revenue"] = chart_df["revenue"].round(2)
    chart_df["revenueEstimated"] = chart_df["revenueEstimated"].round(2)
    # chart_df["EPS Surprise"] = chart_df["eps"] - chart_df["epsEstimated"]
    # chart_df["Revenue Surprise"] = chart_df["revenue"] - chart_df["revenueEstimated"]
    chart_df["date"] = chart_df["date"].dt.date
    chart_df = chart_df.rename(columns = {"symbol": "ticker"}). \
        set_index("ticker", drop=False)

    return [chart_df.to_dict('records'), "{date} = "+str(last_update_dttm.date())]

@app.callback(
    Output('fundtab-eps-chart', 'figure'),
    [Input('fundtab-ticker-selector', 'value')])
def update_eps_chart(ticker):
    if not ticker:
        raise PreventUpdate
    calc_df = calendar_df
    calc_df = calc_df[(calc_df["symbol"] == ticker)]

    calc_df["color_eps"] = "#47ff34"
    calc_df.loc[calc_df["eps"] < 0,"color_eps"] = "#fe000a"

    calc_df["color_eps_estimate"] = "#7dff8f"
    calc_df.loc[calc_df["epsEstimated"] < 0,"color_eps_estimate"] = "#ff8085"

    chart = {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df["eps"],
            marker_color=calc_df["color_eps"],
            name="EPS")],
        'layout': go.Layout(showlegend=True,
                            xaxis={"fixedrange": True, "type":"date", 'title': 'date'},
                            yaxis={"fixedrange": True},
                            height=500)
    }

    chart["data"].append(go.Bar(
        x=calc_df["date"],
        y=calc_df["epsEstimated"],
        marker_color=calc_df["color_eps_estimate"],
        name="EPS Estimated"))
    return chart

@app.callback(
    Output('fundtab-BS-chart', 'figure'),
    [Input('fundtab-ticker-selector', 'value'),
     Input('fundtab-metric-BS-selection', 'value'),
     Input('fundtab-period-selection', 'value')])
def update_balance_sheet(ticker, metric, period):
    if not period or not ticker or not metric:
        raise PreventUpdate
    df = balance_sheet_df
    calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)]

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
    Output('fundtab-metric-BS-selection', 'options'),
    [Input('fundtab-interval-update', 'n_intervals')])
def set_ticker_options(n_intervals):
    metrics = balance_sheet_df.columns.drop(["date", "symbol", "period"])
    return [{'label': metric, 'value': metric} for metric in metrics]

@app.callback(
    Output('fundtab-CF-chart', 'figure'),
    [Input('fundtab-ticker-selector', 'value'),
     Input('fundtab-metric-CF-selection', 'value'),
     Input('fundtab-period-selection', 'value')])
def update_cash_sheet(ticker, metric, period):
    if not period or not ticker or not metric:
        raise PreventUpdate
    df = cash_flow_df
    calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)]
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
    Output('fundtab-metric-CF-selection', 'options'),
    [Input('fundtab-interval-update', 'n_intervals')])
def set_ticker_options(n_intervals):
    metrics = cash_flow_df.columns.drop(["date", "symbol", "period"])
    return [{'label': metric, 'value': metric} for metric in metrics]

@app.callback(
    Output('fundtab-INC-chart', 'figure'),
    [Input('fundtab-ticker-selector', 'value'),
     Input('fundtab-metric-INC-selection', 'value'),
     Input('fundtab-period-selection', 'value')])
def update_income_sheet(ticker, metric, period):
    if not period or not ticker or not metric:
        raise PreventUpdate
    df = income_statement_df
    calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)]
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
    Output('fundtab-metric-INC-selection', 'options'),
    [Input('fundtab-interval-update', 'n_intervals')])
def set_ticker_options(n_intervals):
    metrics = income_statement_df.columns.drop(["date", "symbol", "period"])
    return [{'label': metric, 'value': metric} for metric in metrics]

@app.callback(
    Output('fundtab-KM-chart', 'figure'),
    [Input('fundtab-ticker-selector', 'value'),
     Input('fundtab-metric-KM-selection', 'value'),
     Input('fundtab-period-selection', 'value')])
def update_income_sheet(ticker, metric, period):
    if not period or not ticker or not metric:
        raise PreventUpdate
    df = key_metrics_df
    calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)]
    return {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            xaxis={"fixedrange": True, "type": "date"},
                            yaxis={"fixedrange": True},
                            height=500)
    }

@app.callback(
    Output('fundtab-metric-KM-selection', 'options'),
    [Input('fundtab-interval-update', 'n_intervals')])
def set_ticker_options(n_intervals):
    metrics = key_metrics_df.columns.drop(["date", "symbol", "period"])
    return [{'label': metric, 'value': metric} for metric in metrics]
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

sttmt_df = main_app.get_data_from_db(querylib.GET_COMPANY_STTMNTS)
sttmt_score_df = main_app.get_data_from_db(querylib.GET_STTMNTS_SCORES)
sttmt_score_df = sttmt_score_df.astype({"date": "datetime64",
                                        "statement_score": "float64"})
sttmt_sector_score_df = main_app.get_data_from_db(querylib.GET_STTMNTS_SECTOR_SCORES)
sttmt_sector_score_df = sttmt_sector_score_df.astype({"avg_score": "float64"})

#CHART OPTIONS
CHART_EXTRA_OPTIONS = [
    {
    'label': "differentiate",
    'value': "diff"
    },
    {
        'label': "Ratio to mean sector",
        'value': "sector_mean"
    }]

layout = html.Div([
    dcc.Interval(id='fund-tab-interval-update', interval=3600*1000, n_intervals=0),
    dbc.Row([
        dbc.Col(html.Div(id="fund-tab-last-update-info"),
                width={'size': 5,  "offset": 1, 'order': 1})]),
    html.Br(),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dash_table.DataTable(
                id='fund-tab-stmnts-scores',
                columns=[
                    {"name": i, "id": i} for i in ["Date", "Ticker", "Sector", "Statement Score"]
                ],
                editable=False,              # allow editing of data inside all cells
                cell_selectable=False,
                sort_by = [{"column_id": "Date", "direction": "desc"}],
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
    html.Br(),
    dbc.Row(
        dbc.Col(
            dcc.Dropdown(id='fund-tab-ticker-selector',
                         value='AAPL', persistence=True, persistence_type='local'),
            width={'size': 3,  "offset": 1, 'order': 1}),
        justify='left', align='center'),
    dbc.Row(
        [dbc.Col(
        dbc.Spinner(
            dcc.Graph(id='fund-tab-eps-chart',
                      config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '600px'}),
            size="lg", color="primary", type="border", fullscreen=False),
        width={'size': 5,  "offset": 0, 'order': 1}),
        dbc.Col(
            dbc.Spinner(
                dash_table.DataTable(
                    id='fund-tab-earnings-calendar-table',
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
            width={'size': 5,  "offset": 0, 'order': 2})],
        justify='center', align='start'),
    dbc.Row(
        dbc.Col(
            dcc.RadioItems(
                id='fund-tab-period-selection',
                options=[
                    {'label': 'Year', 'value': 'Year'},
                    {'label': 'Quarter', 'value': 'Quarter'}
                ],
                value='Quarter',
                persistence=True, persistence_type='local'
            ), width={'size': 5,  "offset": 1, 'order': 1})),
    html.Br(),
        # dbc.Row([
        #     dbc.Col(html.H6("Income statement report"), width={'size': 5,  "offset": 1, 'order': 1}),
        #     dbc.Col(html.H6("Cash flows report"), width={'size': 5,  "offset": 0, 'order': 2})]),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id='fund-tab-stmnt-dropdown-1',
                    value="marketCap", persistence=True, persistence_type='local'),
                width={'size': 2,  "offset": 1, 'order': 1}),
            dbc.Col(
                dcc.Checklist(
                    id='fund-tab-stmnt-chart-options-1', persistence=True, persistence_type='local',
                    options=CHART_EXTRA_OPTIONS,
                    labelStyle={'display': 'inline-block'}), width={'size': 3,  "offset": 0, 'order': 2}),
            dbc.Col(
                dcc.Dropdown(
                    id='fund-tab-stmnt-dropdown-2',
                    value="investmentsInPropertyPlantAndEquipment", persistence=True, persistence_type='local'),
                width={'size': 2,  "offset": 0, 'order': 3}),
            dbc.Col(
                dcc.Checklist(
                    id='fund-tab-stmnt-chart-options-2', persistence=True, persistence_type='local',
                    options=CHART_EXTRA_OPTIONS,
                    labelStyle={'display': 'inline-block'}), width={'size': 3,  "offset": 0, 'order': 4}),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col(
                dbc.Spinner(dcc.Graph(id='fund-tab-stmnt-chart-1', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
                            size="lg", color="primary", type="border", fullscreen=False),
                width={'size': 5,  "offset": 1, 'order': 1}),
            dbc.Col(
                dbc.Spinner(dcc.Graph(id='fund-tab-stmnt-chart-2', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
                            size="lg", color="primary", type="border", fullscreen=False),
                width={'size': 5,  "offset": 0, 'order': 2})]),
        html.Br(),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id='fund-tab-stmnt-dropdown-3',
                    value="priceToSalesRatio", persistence=True, persistence_type='local'),
                width={'size': 2,  "offset": 1, 'order': 1}),
            dbc.Col(
                dcc.Checklist(
                    id='fund-tab-stmnt-chart-options-3', persistence=True, persistence_type='local',
                    options=CHART_EXTRA_OPTIONS,
                    labelStyle={'display': 'inline-block'}), width={'size': 3,  "offset": 0, 'order': 2}),
            dbc.Col(
                dcc.Dropdown(
                    id='fund-tab-stmnt-dropdown-4',
                    value="revenuePerShare", persistence=True, persistence_type='local'),
                width={'size': 2,  "offset": 0, 'order': 3}),
            dbc.Col(
                dcc.Checklist(
                    id='fund-tab-stmnt-chart-options-4', persistence=True, persistence_type='local',
                    options=CHART_EXTRA_OPTIONS,
                    labelStyle={'display': 'inline-block'}), width={'size': 3,  "offset": 0, 'order': 4}),
            ]),
        html.Br(),
        dbc.Row([
            dbc.Col(
                dbc.Spinner(dcc.Graph(id='fund-tab-stmnt-chart-3', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
                            size="lg", color="primary", type="border", fullscreen=False),
                width={'size': 5,  "offset": 1, 'order': 1}),
            dbc.Col(
                dbc.Spinner(dcc.Graph(id='fund-tab-stmnt-chart-4', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '500px'}),
                            size="lg", color="primary", type="border", fullscreen=False),
                width={'size': 5,  "offset": 0, 'order': 2})])
])

@app.callback(Output('fund-tab-ticker-selector', 'options'),
              [Input('fund-tab-interval-update', 'n_intervals')])
def tab3_set_ticker_selector3(n_intervals):
    return [{'label': ticker, 'value': ticker} for ticker in tickers]

@app.callback(
    Output("fund-tab-last-update-info", 'children'),
    [Input('fund-tab-interval-update', 'n_intervals')])
def get_fund_data(n_intervals):
    global calendar_df
    global last_update_dttm
    global tickers
    global sttmt_df
    global sttmt_score_df
    global sttmt_sector_score_df


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

        sttmt_df = main_app.get_data_from_db(querylib.GET_COMPANY_STTMNTS)
        sttmt_score_df = main_app.get_data_from_db(querylib.GET_STTMNTS_SCORES)
        sttmt_score_df = sttmt_score_df.astype({"date": "datetime64",
                                          "statement_score": "float64"})
        sttmt_sector_score_df = main_app.get_data_from_db(querylib.GET_STTMNTS_SECTOR_SCORES)
        sttmt_sector_score_df = sttmt_sector_score_df.astype({"date": "datetime64",
                                                              "statement_score": "float64"})

    return f"Last update utc dttm {last_update_dttm}"

@app.callback(Output('fund-tab-stmnts-scores', 'data'),
              [Input('fund-tab-interval-update', 'n_intervals')])
def update_stmnts_score_table(n_intervals):
    chart_df = sttmt_score_df

    chart_df["statement_score"] = chart_df["statement_score"].round(2)
    chart_df["date"] = pd.to_datetime(chart_df["date"]).dt.strftime('%Y-%m-%d')
    chart_df = chart_df.rename(columns = {
        "symbol": "Ticker",
        "statement_score" : "Statement Score",
        "date" : "Date",
        "sector" : "Sector",
    })
    return chart_df.to_dict('records')

@app.callback([Output('fund-tab-earnings-calendar-table', 'data'),
               Output('fund-tab-earnings-calendar-table', 'filter_query')],
              [Input('fund-tab-interval-update', 'n_intervals')])
def update_calendar_table(n_intervals):
    chart_df = calendar_df

    chart_df["revenue"] = chart_df["revenue"].round(2)
    chart_df["revenueEstimated"] = chart_df["revenueEstimated"].round(2)
    chart_df["date"] = pd.to_datetime(chart_df["date"]).dt.strftime('%Y-%m-%d')
    chart_df = chart_df.rename(columns = {"symbol": "ticker"}). \
        set_index("ticker", drop=False)

    return [chart_df.to_dict('records'), "{date} >= "+str(last_update_dttm.date())]

@app.callback(
    Output('fund-tab-eps-chart', 'figure'),
    [Input('fund-tab-ticker-selector', 'value')])
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
    Output('fund-tab-stmnt-chart-1', 'figure'),
    [Input('fund-tab-ticker-selector', 'value'),
     Input('fund-tab-stmnt-dropdown-1', 'value'),
     Input('fund-tab-period-selection', 'value'),
     Input('fund-tab-stmnt-chart-options-1', 'value')])
def update_smnt_chart_1(ticker, metric, period, chart_extra_options):
    if not period or not ticker or not metric:
        raise PreventUpdate
    if chart_extra_options is None:
        chart_extra_options = []
    df = sttmt_df
    calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)][["date", "year", 'month', "sector", metric]].copy()
    calc_df[metric] = calc_df[metric].astype(float)

    title = metric

    if 'sector_mean' in chart_extra_options:
        sector = calc_df["sector"].iloc[0]
        avg_sector = df[(df["period"] == period) & (df["sector"] == sector)][["date", "year", 'month', metric]].copy()
        avg_sector[metric] = avg_sector[metric].astype(float)
        sector_metric_name = metric+"_sector_avg"
        avg_sector = avg_sector[["year", "month", metric]].groupby(["year", "month"]).mean().reset_index().rename(columns={metric:sector_metric_name}).set_index(["year", "month"])
        calc_df = calc_df.set_index(["year", "month"])
        calc_df = calc_df.merge(avg_sector, how='inner', left_index=True, right_index=True).reset_index().dropna()
        calc_df[metric] = calc_df[metric] / calc_df[sector_metric_name]
        title = title + " to sector mean ratio"

    if 'diff' in chart_extra_options:
        calc_df[metric] = calc_df[metric] - calc_df[metric].shift(1)
        title = title + " change"

    calc_df = calc_df.sort_values("date")

    chart = {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            title=title,
                            xaxis={
                                "fixedrange": True, "type":"date"},
                            yaxis={"fixedrange": True, 'title': metric},
                            height=500)
    }

    return chart

@app.callback(
    Output('fund-tab-stmnt-dropdown-1', 'options'),
    [Input('fund-tab-interval-update', 'n_intervals')])
def update_smnt_chart_1_options(n_intervals):
    metrics = sttmt_df.columns.drop(["date", "symbol", "period", "sector", "currency", "month", "year"])
    return [{'label': metric, 'value': metric} for metric in metrics]

@app.callback(
    Output('fund-tab-stmnt-chart-2', 'figure'),
    [Input('fund-tab-ticker-selector', 'value'),
     Input('fund-tab-stmnt-dropdown-2', 'value'),
     Input('fund-tab-period-selection', 'value'),
     Input('fund-tab-stmnt-chart-options-2', 'value')])
def update_smnt_chart_2(ticker, metric, period, chart_extra_options):
    if not period or not ticker or not metric:
        raise PreventUpdate
    if chart_extra_options is None:
        chart_extra_options = []
    df = sttmt_df
    calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)][["date", "year", 'month', "sector", metric]].copy()
    calc_df[metric] = calc_df[metric].astype(float)

    title = metric

    if 'sector_mean' in chart_extra_options:
        sector = calc_df["sector"].iloc[0]
        avg_sector = df[(df["period"] == period) & (df["sector"] == sector)][["date", "year", 'month', metric]].copy()
        avg_sector[metric] = avg_sector[metric].astype(float)
        sector_metric_name = metric+"_sector_avg"
        avg_sector = avg_sector[["year", "month", metric]].groupby(["year", "month"]).mean().reset_index().rename(columns={metric:sector_metric_name}).set_index(["year", "month"])
        calc_df = calc_df.set_index(["year", "month"])
        calc_df = calc_df.merge(avg_sector, how='inner', left_index=True, right_index=True).reset_index().dropna()
        calc_df[metric] = calc_df[metric] / calc_df[sector_metric_name]
        title = title + " to sector mean ratio"

    if 'diff' in chart_extra_options:
        calc_df[metric] = calc_df[metric] - calc_df[metric].shift(1)
        title = title + " change"

    calc_df = calc_df.sort_values("date")

    chart = {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            title=title,
                            xaxis={
                                "fixedrange": True, "type":"date"},
                            yaxis={"fixedrange": True, 'title': metric},
                            height=500)
    }

    return chart

@app.callback(
    Output('fund-tab-stmnt-dropdown-2', 'options'),
    [Input('fund-tab-interval-update', 'n_intervals')])
def update_smnt_chart_2_options(n_intervals):
    metrics = sttmt_df.columns.drop(["date", "symbol", "period", "sector", "currency", "month", "year"])
    return [{'label': metric, 'value': metric} for metric in metrics]

@app.callback(
    Output('fund-tab-stmnt-chart-3', 'figure'),
    [Input('fund-tab-ticker-selector', 'value'),
     Input('fund-tab-stmnt-dropdown-3', 'value'),
     Input('fund-tab-period-selection', 'value'),
     Input('fund-tab-stmnt-chart-options-3', 'value')])
def update_smnt_chart_3(ticker, metric, period, chart_extra_options):
    if not period or not ticker or not metric:
        raise PreventUpdate
    if chart_extra_options is None:
        chart_extra_options = []
    df = sttmt_df
    calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)][["date", "year", 'month', "sector", metric]].copy()
    calc_df[metric] = calc_df[metric].astype(float)

    title = metric

    if 'sector_mean' in chart_extra_options:
        sector = calc_df["sector"].iloc[0]
        avg_sector = df[(df["period"] == period) & (df["sector"] == sector)][["date", "year", 'month', metric]].copy()
        avg_sector[metric] = avg_sector[metric].astype(float)
        sector_metric_name = metric+"_sector_avg"
        avg_sector = avg_sector[["year", "month", metric]].groupby(["year", "month"]).mean().reset_index().rename(columns={metric:sector_metric_name}).set_index(["year", "month"])
        calc_df = calc_df.set_index(["year", "month"])
        calc_df = calc_df.merge(avg_sector, how='inner', left_index=True, right_index=True).reset_index().dropna()
        calc_df[metric] = calc_df[metric] / calc_df[sector_metric_name]
        title = title + " to sector mean ratio"

    if 'diff' in chart_extra_options:
        calc_df[metric] = calc_df[metric] - calc_df[metric].shift(1)
        title = title + " change"

    calc_df = calc_df.sort_values("date")

    chart = {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            title=title,
                            xaxis={
                                "fixedrange": True, "type":"date"},
                            yaxis={"fixedrange": True, 'title': metric},
                            height=500)
    }

    return chart

@app.callback(
    Output('fund-tab-stmnt-dropdown-3', 'options'),
    [Input('fund-tab-interval-update', 'n_intervals')])
def update_smnt_chart_3_options(n_intervals):
    metrics = sttmt_df.columns.drop(["date", "symbol", "period", "sector", "currency", "month", "year"])
    return [{'label': metric, 'value': metric} for metric in metrics]

@app.callback(
    Output('fund-tab-stmnt-chart-4', 'figure'),
    [Input('fund-tab-ticker-selector', 'value'),
     Input('fund-tab-stmnt-dropdown-4', 'value'),
     Input('fund-tab-period-selection', 'value'),
     Input('fund-tab-stmnt-chart-options-4', 'value')])
def update_smnt_chart_4(ticker, metric, period, chart_extra_options):
    if not period or not ticker or not metric:
        raise PreventUpdate
    if chart_extra_options is None:
        chart_extra_options = []
    df = sttmt_df
    calc_df = df[(df["symbol"] == ticker) & (df["period"] == period)][["date", "year", 'month', "sector", metric]].copy()
    calc_df[metric] = calc_df[metric].astype(float)

    title = metric

    if 'sector_mean' in chart_extra_options:
        sector = calc_df["sector"].iloc[0]
        avg_sector = df[(df["period"] == period) & (df["sector"] == sector)][["date", "year", 'month', metric]].copy()
        avg_sector[metric] = avg_sector[metric].astype(float)
        sector_metric_name = metric+"_sector_avg"
        avg_sector = avg_sector[["year", "month", metric]].groupby(["year", "month"]).mean().reset_index().rename(columns={metric:sector_metric_name}).set_index(["year", "month"])
        calc_df = calc_df.set_index(["year", "month"])
        calc_df = calc_df.merge(avg_sector, how='inner', left_index=True, right_index=True).reset_index().dropna()
        calc_df[metric] = calc_df[metric] / calc_df[sector_metric_name]
        title = title + " to sector mean ratio"

    if 'diff' in chart_extra_options:
        calc_df[metric] = calc_df[metric] - calc_df[metric].shift(1)
        title = title + " change"

    calc_df = calc_df.sort_values("date")

    chart = {
        'data': [go.Bar(
            x=calc_df["date"],
            y=calc_df[metric])],
        'layout': go.Layout(showlegend=False,
                            title=title,
                            xaxis={
                                "fixedrange": True, "type":"date"},
                            yaxis={"fixedrange": True, 'title': metric},
                            height=500)
    }

    return chart

@app.callback(
    Output('fund-tab-stmnt-dropdown-4', 'options'),
    [Input('fund-tab-interval-update', 'n_intervals')])
def update_smnt_chart_4_options(n_intervals):
    metrics = sttmt_df.columns.drop(["date", "symbol", "period", "sector", "currency", "month", "year"])
    return [{'label': metric, 'value': metric} for metric in metrics]

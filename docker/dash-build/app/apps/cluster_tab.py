
import src.PSQL_queries as querylib
import pandas as pd
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import main_app
from main_app import app
import plotly.graph_objs as go
from datetime import datetime, timezone, timedelta


last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

PCA_NUMS = ["0", "1", "2"]
PCA_TIME_BASES = ["100", "365", "730"]

tab3_df = main_app.get_data_from_db(querylib.GET_CLOSE_PRICES)
tab3_df = tab3_df.astype({"close": "float64",
                          "timestamp": "int64",
                          "date": "datetime64"})

tab3_pca_df = main_app.get_data_from_db(querylib.GET_PCA)
tab3_pca_df = tab3_pca_df.astype({"pca_loading_0": "float64","pca_loading_1": "float64","pca_loading_2": "float64"})
currencies = tab3_pca_df["currency"].unique()
sectors = tab3_pca_df["sector"].unique()
tickers = tab3_pca_df["ticker"].unique()

layout = html.Div([

    dcc.Interval(id='tab3-interval-update', interval=3600*1000, n_intervals=0),
    dbc.Row([
        dbc.Col(html.Div(id="tab3-last-update-info"), width={'size': 5,  "offset": 1, 'order': 1})]),
    dbc.Row([dbc.Col(
        dcc.Checklist(
            id='tab3-currency-selector',
            value=["USD"], persistence=True, persistence_type='local',
            labelStyle={'display': 'inline-block'}), width={'size': 3,  "offset": 1, 'order': 1})]),
    html.Br(),
    dbc.Row([
        dbc.Col(html.H6("Sector selection:"), width={'size': 3,  "offset": 1, 'order': 1})]),
    dbc.Row([
        dbc.Col(
        dcc.Dropdown(
            id='tab3-sector-selector', persistence=True, multi=True, persistence_type='local'), width={'size': 3,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Dropdown(
                id='tab3-ticker-sensor', persistence=True, multi=True, persistence_type='local'), width={'size': 3,  "offset": 1, 'order': 1})]),
    html.Br(),
    dbc.Row([
        dbc.Col(html.H6("PCA X selection:"), width={'size': 3,  "offset": 1, 'order': 1}),
        dbc.Col(html.H6("PCA Y selection:"), width={'size': 3,  "offset": 0, 'order': 2}),
        dbc.Col(html.H6("PCA time base selection:"), width={'size': 3,  "offset": 0, 'order': 3})]),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(id='tab3-PCA-num-x',
                         persistence=True, persistence_type='local',
                         value="0", options=[{'label': pca_num, 'value': pca_num} for pca_num in PCA_NUMS]),
            width={'size': 3,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Dropdown(id='tab3-PCA-num-y',
                         persistence=True, persistence_type='local',
                         value="1", options=[{'label': pca_num, 'value': pca_num} for pca_num in PCA_NUMS]),
            width={'size': 3,  "offset": 0, 'order': 2}),
        dbc.Col(
            dcc.Dropdown(id='tab3-PCA-time-base',
                         persistence=True, persistence_type='local',
                         value="730", options=[{'label': pca_time_base, 'value': pca_time_base} for pca_time_base in PCA_TIME_BASES]),
            width={'size': 3,  "offset": 0, 'order': 3})]),
    html.Br(),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dcc.Graph(id='tab3-cluster-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '600px'}),
            size="lg", color="primary", type="border", fullscreen=False)
        , width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    html.Br(),
    dbc.Row([
        dbc.Col(html.H6("Ticker 1"), width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(html.H6("Ticker 2"), width={'size': 5,  "offset": 0, 'order': 2})]),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(id='tab3-ticker-rel1',
                         persistence=True, persistence_type='local'),
            width={'size': 5,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Dropdown(id='tab3-ticker-rel2',
                         persistence=True, persistence_type='local'),
            width={'size': 5,  "offset": 0, 'order': 2})]),
    html.Br(),
    dbc.Row([
        dbc.Col(
            dcc.Input(
                id="tab3-mv1", type="number", placeholder="0-200", inputMode="numeric",
                min=0, max=200, step=1, value=5, persistence=True, persistence_type='local'),
            width={'size': 3,  "offset": 1, 'order': 1}),
        dbc.Col(
            dcc.Input(
                id="tab3-mv2", type="number", placeholder="0-200", inputMode="numeric",
                min=0, max=200, step=1, value=60, persistence=True, persistence_type='local'),
            width={'size': 3,  "offset": 1, 'order': 2}),
        # dbc.Col(
        #     dcc.Input(
        #         id="tab3-std-per", type="number", placeholder="0-200", inputMode="numeric",
        #         min=0, max=200, step=1, value=60, persistence=True, persistence_type='local'),
        #     width={'size': 3,  "offset": 1, 'order': 3}),
    ]),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dcc.Graph(id='tab3-pair-rel-chart', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '600px'}),
            size="lg", color="primary", type="border", fullscreen=False)
        , width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center'),
    dbc.Row(dbc.Col(
        dbc.Spinner(
            dcc.Graph(id='tab3-pair-rel-chart-z-scored', config=main_app.DEFAULT_GRAPH_CONFIG, style={'height': '600px'}),
            size="lg", color="primary", type="border", fullscreen=False)
        , width={'size': 10,  "offset": 0, 'order': 1}),
        justify='center', align='center')
])

@app.callback(Output('tab3-last-update-info', 'children'),
              Input('tab3-interval-update', 'n_intervals'))
def get_tab3_data(n_intervals):
    global tab3_df
    global tab3_pca_df
    global last_update_dttm
    global currencies
    global sectors
    global tickers

    current_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))

    if (current_dttm - last_update_dttm) > main_app.INTERVAL_DELTA_UPDATE:

        last_update_dttm = datetime.utcnow().replace(tzinfo=timezone(timedelta(hours=0)))
        tab3_df = main_app.get_data_from_db(querylib.GET_CLOSE_PRICES)
        tab3_df = tab3_df.astype({"close": "float64",
                                  "timestamp": "int64",
                                  "date": "datetime64"})

        tab3_pca_df = main_app.get_data_from_db(querylib.GET_PCA)
        tab3_pca_df = tab3_pca_df.astype({"pca_loading_0": "float64","pca_loading_1": "float64","pca_loading_2": "float64"})
        currencies = tab3_pca_df["currency"].unique()
        sectors = tab3_pca_df["sector"].unique()
        tickers = tab3_pca_df["ticker"].unique()

    return f"Last update utc dttm {last_update_dttm}"

@app.callback(Output('tab3-currency-selector', 'options'),
              [Input('tab3-interval-update', 'n_intervals')])
def tab3_set_currency_selector(n_intervals):
    return [{'label': currency, 'value': currency} for currency in currencies]

@app.callback(Output('tab3-sector-selector', 'options'),
              [Input('tab3-interval-update', 'n_intervals')])
def tab3_set_sector_selector(n_intervals):
    return [{'label': sector, 'value': sector} for sector in sectors]

@app.callback(Output('tab3-ticker-rel1', 'options'),
              [Input('tab3-interval-update', 'n_intervals')])
def tab3_set_ticker_selector1(n_intervals):
    return [{'label': ticker, 'value': ticker} for ticker in tickers]

@app.callback(Output('tab3-ticker-rel2', 'options'),
              [Input('tab3-interval-update', 'n_intervals')])
def tab3_set_ticker_selector2(n_intervals):
    return [{'label': ticker, 'value': ticker} for ticker in tickers]

@app.callback(Output('tab3-ticker-sensor', 'options'),
              [Input('tab3-interval-update', 'n_intervals')])
def tab3_set_ticker_selector3(n_intervals):
    return [{'label': ticker, 'value': ticker} for ticker in tickers]

@app.callback(
    Output('tab3-cluster-chart', 'figure'),
    [Input('tab3-sector-selector', 'value'),
     Input('tab3-currency-selector', 'value'),
     Input('tab3-PCA-num-x', 'value'),
     Input('tab3-PCA-num-y', 'value'),
     Input('tab3-PCA-time-base', 'value'),
     Input('tab3-ticker-sensor', 'value')])
def update_cluster_chart(sector_options, currency_options, pca_x, pca_y, pca_time_base, selected_tickers):

    df = tab3_pca_df
    if not sector_options:
        sector_options = df["sector"].unique()

    data_df = df[(df['currency'].isin(currency_options) &
                  df['sector'].isin(sector_options))]

    data_df["selected_tickers_color"] = '#27d67e'
    data_df["selected_tickers_size"] = 7
    if selected_tickers:
        data_df.loc[data_df["ticker"].isin(selected_tickers), "selected_tickers_size"] = 15
        data_df.loc[data_df["ticker"].isin(selected_tickers), "selected_tickers_color"] = "#d62728"
    pca_x = "pca_loading_{}".format(pca_x)
    pca_y = "pca_loading_{}".format(pca_y)

    hovertext="Ticker: " + data_df["ticker"].astype(str) + "<br>Industry: " + \
              data_df["industry"].astype(str) + "<br>Cluster: " + \
              data_df["cluster"].astype(str)

    chart = {
        'data':[
            go.Scattergl(x=data_df[pca_x],
                         y=data_df[pca_y],
                         mode='markers',
                         hovertext=hovertext,
                         marker=dict(
                             color=data_df["selected_tickers_color"].values,
                             size=data_df["selected_tickers_size"].values,
                             #colorscale='Viridis',
                             line_width=1
                         ))
                         #marker_color=data_df["cluster"].astype("int64"))
        ],
        'layout': go.Layout(
            title="PCA loadings",
            showlegend=False,
            hovermode="closest",
            height=600,
            xaxis={'title': pca_x},
            yaxis={'title': pca_y})
    }

    return chart

@app.callback(
    Output('tab3-pair-rel-chart', 'figure'),
    [Input('tab3-ticker-rel1', 'value'),
     Input('tab3-ticker-rel2', 'value'),
     Input('tab3-mv1', 'value'),
     Input('tab3-mv2', 'value')])
def update_par_rel_chart(ticker1, ticker2, mv1, mv2):
    if not ticker1 or not ticker2:
        raise PreventUpdate

    rel_df = tab3_df.set_index("date")

    rel_trace = rel_df[rel_df["ticker"]==ticker1]["close"] / \
                rel_df[rel_df["ticker"]==ticker2]["close"]

    rel_trace = rel_trace.dropna().sort_index()

    chart = {
        'data':[
            go.Scatter(x=rel_trace.index,
                       y=rel_trace,
                       mode='lines',
                       name="price ratio")],
        'layout': go.Layout(
            title="Return ration",
            showlegend=False,
            hovermode="closest",
            height=600,
            xaxis={'title': "date"},
            yaxis={'title': "Cumulative return ratio"})
    }

    if mv1 != 0:
        mv_1 = rel_trace.rolling(mv1).mean()
    chart["data"].append(
        go.Scatter(
            x=rel_trace.index,
            y=mv_1,
            mode="lines",
            line={
                "color":"#eb7d07", "width":2
            },
            name=f"Moving Average - {mv1}")
    )

    if mv2 != 0:
        mv_2 = rel_trace.rolling(mv2).mean()
        chart["data"].append(
            go.Scatter(
                x=rel_trace.index,
                y=mv_2,
                mode="lines",
                line={
                    "color":"#1207eb", "width":2
                },
                name=f"Moving Average - {mv2}")
        )

    return chart

@app.callback(
    Output('tab3-pair-rel-chart-z-scored', 'figure'),
    [Input('tab3-ticker-rel1', 'value'),
     Input('tab3-ticker-rel2', 'value')])
def update_par_rel_chart(ticker1, ticker2):
    if not ticker1 or not ticker2:
        raise PreventUpdate

    rel_df = tab3_df.set_index("date")

    rel_trace = rel_df[rel_df["ticker"]==ticker1]["close"] / \
                rel_df[rel_df["ticker"]==ticker2]["close"]

    rel_trace = rel_trace.dropna().sort_index()

    mean = rel_trace.mean()
    std = rel_trace.std()

    rel_trace = (rel_trace - mean) / std

    chart = {
        'data':[
            go.Scatter(x=rel_trace.index,
                       y=rel_trace,
                       mode='lines',
                       name = "price ratio z-scored")],
        'layout': go.Layout(
            title="Return ration normilized",
            showlegend=False,
            hovermode="closest",
            height=600,
            xaxis={'title': "date"},
            yaxis={'title': "Cumulative return ratio"})
    }

    chart["data"].append(
        go.Scatter(
            x=rel_trace.index,
            y=[0]*len(rel_trace.index),
            mode="lines",
            hoverinfo='skip',
            line={
                "color":"#3b444b", "width":2
            },
            name=f"Mean")
    )

    chart["data"].append(
        go.Scatter(
            x=rel_trace.index,
            y=[1]*len(rel_trace.index),
            hoverinfo='skip',
            line={
                "color":"#32a852", "width": 2, "dash":"dash"
            },
            mode="lines",
            name=f"+1 bound")
    )
    chart["data"].append(
        go.Scatter(
            x=rel_trace.index,
            y=[-1]*len(rel_trace.index),
            hoverinfo='skip',
            line={
                "color":"#32a852", "width": 2, "dash":"dash"
            },
            mode="lines",
            name=f"-1 bound")
    )

    chart["data"].append(
        go.Scatter(
            x=rel_trace.index,
            y=[2]*len(rel_trace.index),
            hoverinfo='skip',
            line={
                "color":"#a8a232", "width": 2, "dash":"dash"
            },
            mode="lines",
            name=f"+2 bound")
    )
    chart["data"].append(
        go.Scatter(
            x=rel_trace.index,
            y=[-2]*len(rel_trace.index),
            hoverinfo='skip',
            line={
                "color":"#a8a232", "width": 2, "dash":"dash"
            },
            mode="lines",
            name=f"-2 bound")
    )

    chart["data"].append(
        go.Scatter(
            x=rel_trace.index,
            y=[3]*len(rel_trace.index),
            hoverinfo='skip',
            line={
                "color":"#a83232", "width": 2, "dash":"dash"
            },
            mode="lines",
            name=f"+3 bound")
    )
    chart["data"].append(
        go.Scatter(
            x=rel_trace.index,
            y=[-3]*len(rel_trace.index),
            hoverinfo='skip',
            line={
                "color":"#a83232", "width": 2, "dash":"dash"
            },
            mode="lines",
            name=f"-3 bound")
    )

    return chart

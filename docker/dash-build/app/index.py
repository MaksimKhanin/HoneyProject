import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from main_app import app
from main_app import server
import main_app
import os
import time
import pandas as pd
from apps import cum_tab_new, tech_tab_new
import src.PSQL_queries as querylib
from dash.exceptions import PreventUpdate
from datetime import datetime, timezone, timedelta


app.layout = html.Div([
    html.H1("Welcome to HoneyDashboard"),

    # dbc.Spinner(
    #     html.Div(id='index-daily-price-data', style={'display': 'none'}),
    #             size="lg", color="primary", type="border", fullscreen=True),
    #
    # html.Div([
    #     html.H3('Select start and end dates:'),
    #     dcc.DatePickerRange(
    #         id='index-candle-data-date-picker',
    #         clearable=True,
    #         display_format="YYYY MM DD",
    #         persistence=True, persistence_type='local',
    #         min_date_allowed=datetime(2019, 1, 1),
    #     )
    # ], style={'display': 'inline-block'}),
    # html.Div([
    #     html.Button(
    #         id='index-submit-button-date-picker',
    #         n_clicks=0,
    #         children='Submit',
    #         style={'fontSize':24, 'marginLeft':'30px'}
    #     ),
    # ], style={'display':'inline-block'}),

    html.Div([
        html.Button(
            id='index-force-refresh-data',
            n_clicks=0,
            children='Refresh Data',
            style={'fontSize': 24, 'marginLeft':' 30px'}
        ),
    ], style={'display':'inline-block'}),
    html.Div(id="index-last-update-info", style={'display': 'none'}),
    html.Br(),
    html.Div([
        dcc.Tabs(id='tabs-example', value='tab-1', children=[
            dcc.Tab(label='Trends', value='tab-1'),
            dcc.Tab(label='Company review', value='tab-2'),
        ]),
    html.Br(),
        html.Div(id='tabs-example-content', children=[])
    ])
])

# @app.callback(
#     Output('index-daily-price-data', 'children'),
#     [Input('index-interval-update', 'n_intervals')])
# def get_data(n_intervals):
#     price_df = main_app.get_data_from_db(querylib.GET_RAW_DAILY_PRICES)
#     return price_df

# @app.callback(Output('index-slider', 'children'),
#               [Input('index-daily-price-data', 'children')])
# def create_slider(main_data):
#     if not main_data:
#         raise PreventUpdate
#     date_range = pd.read_json(main_data)["timestamp"]
#     date_range = main_app.pd_date_to_timestamp(date_range).values
#
#     return main_app.create_date_slider("index-slider", date_range)

@app.callback(Output('tabs-example-content', 'children'),
              Input('tabs-example', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return cum_tab_new.layout
    elif tab == 'tab-2':
        return tech_tab_new.layout
    else:
        return "404 Page Error! Please choose a link"

@app.callback(Output('index-last-update-info', 'children'),
              Input('index-force-refresh-data', 'n_clicks'))
def force_refresh_globals(n_clicks):
    if n_clicks == 0:
        raise PreventUpdate
    main_app.update_globals()

# @app.callback(
#     Output('index-daily-price-data', 'children'),
#     [Input('index-submit-button-date-picker', 'n_clicks')],
#     [State('index-candle-data-date-picker', 'start_date'),
#      State('index-candle-data-date-picker', 'end_date')])
# def update_graph(n_clicks, start_date, end_date):
#     if n_clicks == 0:
#         raise PreventUpdate
#     start = datetime.strptime(start_date[:10], '%Y-%m-%d')
#     end = datetime.strptime(end_date[:10], '%Y-%m-%d')
#     price_df = main_app.get_data_from_db(querylib.GET_RAW_DAILY_PRICES, params=(start, end))
#     return price_df

#host="127.0.0.1"
#host="0.0.0.0"
if __name__ == '__main__':
    app.run_server(debug=True, host="0.0.0.0", port=8050)




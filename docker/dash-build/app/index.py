import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from main_app import app
from main_app import server
import main_app
import os
import time
import pandas as pd
from apps import cum_tab, tech_tab, cluster_tab, fundamentals_tab


# from apps import cluster_tab, fundamentals_tab
import src.PSQL_queries as querylib
from dash.exceptions import PreventUpdate

app.layout = html.Div([
    html.H1("Welcome to HoneyDashboard"),
    html.Br(),
    html.Div([
        dcc.Tabs(id='index-tab-list', value='tab-4', children=[
            dcc.Tab(label='Trends & Partfolio', value='tab-1'),
            dcc.Tab(label='Tech positioning', value='tab-2'),
            dcc.Tab(label='Clustering & Pair Trading', value='tab-3'),
            dcc.Tab(label='Fundamentals', value='tab-4')
        ]),
        html.Br(),
        html.Div(id='index-tabs-content', children=[])
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
#     return main_app.create_date_slider("index-slider", date_range)

@app.callback(Output('index-tabs-content', 'children'),
              Input('index-tab-list', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return cum_tab.layout
    elif tab == 'tab-2':
        return tech_tab.layout
    elif tab == 'tab-3':
        return cluster_tab.layout
    elif tab == 'tab-4':
        return fundamentals_tab.layout
    else:
        return "404 Page Error! Please choose a link"

#host="127.0.0.1"
#host="0.0.0.0"
if __name__ == '__main__':
    app.run_server(debug=False, host="0.0.0.0", port=8050)




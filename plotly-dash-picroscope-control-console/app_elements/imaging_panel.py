'''
 This module contains the ImagingPanel class.

 it doesn't work, but it's a start

 other modules function as expected

 this one must be hardcoded into app.py

 '''       
from dash import dcc, html
# import dash_core_components as dcc
# import dash_html_components as html
import dash_bootstrap_components as dbc
import dash.exceptions
import numpy as np
import itertools
import time
import plotly.subplots
import plotly.graph_objects as go
# import braingeneers.utils.messaging as messaging
import uuid
import threading
# import json
import datetime
# import pytz
import dash_auth
# from github import Github
import re
import sqlite3
from callbacks import db_interactor

import os
#app = dash.Dash(__name__, server=server, url_base_pathname='/dashboard/', update_title=None)
base_path = os.getenv('BASE_PATH', '/picroscope/')
url = os.getenv('BASE_URL', 'http://localhost:8056') + base_path
        
alert = html.Div(id = 'alert', children = [
        html.Hr(),
        dbc.Alert(
            "Select Device",
            id="no-device-alert-fade",
            dismissable=True,
            is_open=False,
            color="danger",
            duration=4000,
        ),
        dbc.Alert(
            "Imaging Launched",
            id="experiment-launch-alert",
            dismissable=True,
            is_open=False,
            duration=4000,
        ),
        dbc.Alert(
            "Experiment Stopped",
            id="experiment-stop-alert",
            dismissable=True,
            is_open=False,
            color="danger",
            duration=4000,
        ),
    ]
)

IMAGING_PANEL =  dcc.Tab(label='Imaging Launch', value='tab-1-example-graph', children=[
                    dcc.ConfirmDialog(
                        id='confirm-start',

                    ),
                    dcc.ConfirmDialog(
                        id='confirm-stop',
                    ),
                    # Left control panel
                    html.Div(id='left-control-panel-div', className='four columns pretty_container', children=[
                        html.Img(id='logo', src=url+'/assets/app_controlpanel/logo.png'),
                        #         style={'max-width': '80%'}),
                        html.H2(id='title-text', children='Picroscope Control Panel'),
                        dcc.Dropdown(id='picroscope-dropdown', options=[]),
                        dcc.Checklist(
                            id='github-checkbox',
                            options=[
                                {'label': 'Generate Github Issue', 'value': 'generate'}
                            ],
                            value=['generate']
                        ),
                        html.H2(id='state-title', children='Device State'),
                        html.Div(
                            [
                                html.P(id='device-name-display', children='Selected Device : '),
                                html.P(id='uuid-display', children='UUID:'),
                                html.P(id='group-id-text', children='Group id:'),
                                html.P(id='last-connected', children='Last Connected:'),

                                dcc.Loading(
                                    html.Pre(id="relayout-data",
                                            className="info__container"),
                                    type="dot",
                                ),
                            ],
                            className="pb-20",
                        ),
                        dbc.Button(
                            "Refresh State",
                            id="refresh-state",
                            className="me-1",
                            size="lg",
                            color="secondary",
                            n_clicks=0,
                                ),
                        dbc.Row(alert),
                        ]),
                    #Right Middle Panel 

                    html.Div(id='right-data-panel-div', className='five columns pretty_container', children=[
                        html.H2(id='title-text-2', children='Imaging Parameters'),
                        html.Div([       
                            "Select Experiment ",
                            dcc.Dropdown(id='experiment-dropdown', options=[]),
                            html.Br(),
                            "Current Plate ",
                            dcc.Dropdown(id='plate-dropdown', options=[]),
                            html.Br(),
                            dbc.Button(
                                "Update Plate and Experiment Lists",
                                id="refresh-dropdowns",
                                className="me-1",
                                size="lg",
                                color="secondary",
                                n_clicks=0,
                            ),
                            html.Br(),
                            "UUID:        ",
                            dcc.Input(id='uuid-input', value=str(datetime.date.today()) + "-i-", type='text'),
                            html.Br(),
                            "Stack Size:  ",
                            dcc.Input(id='stack-size-input', value='5', type='text'),
                            html.Br(),
                            "Step Size:   ",
                            dcc.Input(id='step-size-input', value='100', type='text'),
                            html.Br(),
                            "Step Offset: ",
                            dcc.Input(id='step-offset-input', value='500', type='text'),
                            html.Br(),
                            "Interval:    ",
                            dcc.Input(id='interval-input', value='1', type='text'),
                            html.Br(),
                            "Cam Params:  ",
                            dcc.Input(id='raspistill-params', value='initial value', type='text'),
                            html.Br(),
                            "Camera Parameter Presets: ",
                            dcc.Dropdown(id='raspistill-param-presets',
                                        options=[
                                            {'label': 'Brightfield',
                                                'value': '-t 4000 -awb off -awbg 1,1 -o'},
                                            {'label': 'GFP',
                                                'value': '-t 4000 -ss 2500000 -awb off -awbg 1,1 -o'},
                                        ],
                                        value = '-t 4000 -awb off -awbg 1,1 -o'
                                        ),
                            html.Br(),
                            "Illumination: ",
                            dcc.Dropdown(id='light-type',
                                        options=[
                                            {'label': 'Above', 'value': 'Above'},
                                            {'label': 'Below', 'value': 'Below'},
                                        ],
                                        value = 'Above'
                                        )

                        ]),
                        # html.Button(id='start-button', n_clicks=0, children='Start'),
                        # html.Button(id='stop-button', children='Stop')
                        html.Br(),
                        dbc.Button(
                            "Start Experiment",
                            id="start-button",
                            className="me-1",
                            size="lg",
                            n_clicks=0,
                                ),
                        dbc.Button(
                            "Stop",
                            id="stop-button",
                            className="me-1",
                            color="danger",
                            size="lg",
                            n_clicks=0,
                        ),
                    ]),
                ])
        
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
        
LIVESTREAM_PANEL = dcc.Tab(label='Live View', value='tab-2-example-graph', children=[
            html.H2(id='scope-name-header', children='Scope'),
            html.Div(id='movement-buttons-panel-div', className='two columns pretty_container', children=[
                html.H2(id='z-plane-adjust', children='Focal Plane'),
                dbc.Button("Up 100",id="move-up",className="me-1",size="lg",n_clicks=0),
                dbc.Button("Reset",id="reset-focus",className="me-1",color="danger",size="lg",n_clicks=0),
                dbc.Button("Stop Stream",id="stop-stream",className="me-1",color="info",size="lg",n_clicks=0),
                html.Div(id='Viewfinder-buttons', children = [
                    html.H2(id='view-title', children='Viewfinder'),
                    dbc.Button("Right 100",id="x-right",className="me-1",size="lg",n_clicks=0),
                    dbc.Button("Left 100",id="x-left",className="me-1",size="lg",n_clicks=0),
                    dbc.Button("Up 100",id="y-up",className="me-1",size="lg",n_clicks=0),
                    dbc.Button("Down 100",id="y-down",className="me-1",size="lg",n_clicks=0),
                ]),
                html.Div(id='light-buttons', children = [
                    html.H2(id='light-title', children='Lights'),
                    dbc.Button("Above",id="l-above",className="me-1",size="lg",n_clicks=0),
                    dbc.Button("Below",id="l-below",className="me-1",size="lg",n_clicks=0),
                    dbc.Button("All off",id="l-off",className="me-1",size="lg",n_clicks=0),
                ]),
            ]),
            html.Div(id='stream-data-panel-div', className='nine columns pretty_container', children=[
                    dcc.Dropdown(id='camera-dropdown', options=[]),
                    html.Div(id='hidden-div', style={'display':'none'}),
                    dbc.Button(
                        "Full Camera Controls",
                        id="show-cam-panel",
                        className="me-1",
                        size="lg",
                        n_clicks=0,
                            ),
                    html.Div(id="iframe-src", style={"height": "1080px", "width": "1920px"}, children=[
                        html.Iframe(id="first", src="http://braingeneers.gi.ucsc.edu:8888/livestream/",style={"height": "640px", "width": "640px"})
                    ])


            ])
        ])
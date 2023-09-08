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
        
EXPERIMENT_PANEL = dcc.Tab(label='Experiment Setup', children=[
                        html.Div(id='experiment-div-1', className='three columns pretty_container', children=[
                            html.H2(id='experiment-title-text', children='Create New Experiment'),
                            #dash text input for experiment name
                            dcc.Input(id='experiment-name-input', type='text', placeholder='Enter Experiment Name'),
                            html.Br(),
                            #dash block text input for experiment notes
                            dcc.Textarea(id='experiment-notes-input', placeholder='Enter Experiment Notes'),
                            html.Br(),
                            #submit button for experiment name
                            dbc.Button(id='experiment-submit-button', children='Submit', color="primary", n_clicks=0),
                            dbc.Alert(
                                "Experiment Added",
                                id="experiment-added-alert-fade",
                                dismissable=True,
                                is_open=False,
                                duration=4000,
                            ),
                            # show experiment button


                            html.H2(id='plate-title-text', children='Create New Plate'),
                            dcc.Input(id='plate-name-input', type='text', placeholder='Enter Plate Name'),
                            html.Br(), 
                            # labeel row input
                            "Rows: ",
                            dcc.Input(id='plate-row-input', type='number', min=0, max=10, step=1, placeholder=4),
                            html.Br(),
                            # label column input
                            "Columns: ",
                            dcc.Input(id='plate-column-input', type='number', min=0, max=10, step=1, placeholder=6),
                            #submit button for experiment name
                            dbc.Button(id='plate-submit-button', children='Submit', color="primary", n_clicks=0),
                            dbc.Alert(
                                "Plate Added",
                                id="plate-added-alert-fade",
                                dismissable=True,
                                is_open=False,
                                duration=4000,
                            ),
                    ]),
                    html.Div(id='experiment-div-2', className='six columns pretty_container', children=[
                            dbc.Button(id='show-experiment-button', children='Refresh', color="primary", n_clicks=0),
                            html.H4(id='experiment-list-header', children='Experiments:'),
                            dcc.Dropdown(
                                    id="Experiment-List",
                                    options=[],
                                ),
                            html.Div(
                                [
                                    dbc.Checklist(
                                        options=[
                                            {"label": "show only active experiments", "value": True},
                                        ],
                                        value=[True],
                                        id="show-only-active-exp",
                                        switch=True,
                                    ),
                                ]),
                            dcc.Loading(children=[
                                html.Pre(id="Experiment-Info",
                                       className="info__container"),
                                # toggle switch for experiment active
                                html.Div(
                                [
                                    dbc.Checklist(
                                        options=[
                                            {"label": "Active", "value": True},

                                            # {"label": "Disabled Option", "value": 3, "disabled": True},
                                        ],
                                        value=[True],
                                        id="switches-input",
                                        switch=True,
                                    ),
                                ]),
                                ],
                                type="dot",
                            ),
                            html.H4(id='plates-list-header', children='Plates'),
                            dcc.Dropdown(
                                id="plates-list",
                                options=[],
                            ),
                            dbc.Checklist(
                                    options=[
                                        {"label": "show only active plates", "value": True},
                                    ],
                                    value=[True],
                                    id="show-only-active-plates",
                                    switch=True,
                            ),
                            dcc.Loading(children=[
                                html.Pre(id="plate-info",
                                       className="info__container"),
                                dbc.Checklist(
                                            options=[
                                                {"label": "Active", "value": True},
                                            ],
                                            value=[True],
                                            id="plate-activate-switch",
                                            switch=True,
                                        ),
                            ],
                            type="dot",
                            ),


                    ]),

                ])


from callbacks import *

def get_callbacks(app):
    """
     def submit_experiment()

        This function is called when the user clicks the "Start Experiment" button. It takes the parameters from the form and sends them to the device.
    """
    @app.callback(
        Output('experiment-added-alert-fade', 'is_open'),
        Output('experiment-dropdown', 'options',allow_duplicate=True),
        Output('experiment-dropdown', 'value'),
        Output('experiment-submit-button', 'n_clicks'),
        Input('experiment-submit-button', 'n_clicks'),
        State('experiment-name-input', 'value'),
        State('experiment-notes-input', 'value'),
        State('experiment-dropdown', 'options'),
        State('experiment-dropdown', 'value'),
        prevent_initial_call=True,
    )
    def submit_experiment(n_clicks, experiment, notes, options, value):
        if n_clicks and experiment:
            exp = db_interactor.create_experiment(experiment, notes)
            exp.attributes["active"] = True
            exp.push()
            #print(json.dumps(str(exp), indent=4))
            return True, db_interactor.list_objects_with_name_and_id("experiments"), exp.id, 0 
        return False, options, value, 0



    """
        def submit_plate()

        This function is called when the user clicks the "Add plate" button. It takes the parameters from the form and sends them to the database.
    """
    @app.callback(
        Output('plate-added-alert-fade', 'is_open'),
        Output('plate-dropdown', 'options', allow_duplicate=True),
        Output('plate-dropdown', 'value'),
        Output('plate-submit-button', 'n_clicks'),
        Input('plate-submit-button', 'n_clicks'),
        State('plate-name-input', 'value'),
        State('plate-row-input', 'value'),
        State('plate-column-input', 'value'),
        State('plate-dropdown', 'options'),
        State('plate-dropdown', 'value'),
        prevent_initial_call=True,
    )
    def submit_plate(n_clicks, plate_name, plate_rows, plate_columns, options, value):
        if n_clicks and plate_name and plate_rows and plate_columns:
            plate = db_interactor.create_plate(plate_name, plate_rows, plate_columns)
            plate.attributes["active"] = True
            plate.push()
            return True, db_interactor.list_objects_with_name_and_id("plates"), plate.id, 0
            #return True, 0
        return False, options, value, 0
        #return False, 0

    """
        def update_experiment_list()

        populate the dropdown list of experiments, optional filter for active experiments

    """    
    @app.callback(
        Output('Experiment-List', 'options'),
        Output('Experiment-List', 'value'),
        Input('show-experiment-button', 'n_clicks'),
        Input('show-only-active-exp', 'value'),
    )
    def update_experiment_list(clicks, show_only_active):
        #weird hack to get bool from toggle switch
        show_only_active = True in show_only_active

        if show_only_active:
            experiments = db_interactor.list_objects_with_name_and_id("experiments","?filters[active][$eq]=true")
        else:
            experiments = db_interactor.list_objects_with_name_and_id("experiments")
        return experiments, experiments[0]["value"]
    
    """
        def update_plate_list()

        populate the dropdown list of plates, optional toggle for active plates only
    """
    @app.callback(
        Output('plates-list', 'options'),
        Output('plates-list', 'value'),
        Input('show-experiment-button', 'n_clicks'),
        Input('show-only-active-plates', 'value'),
    )
    def update_plate_list(clicks, show_only_active):
        #weird hack to get bool from toggle switch
        show_only_active = True in show_only_active

        if show_only_active:
            plates = db_interactor.list_objects_with_name_and_id("plates","?filters[active][$eq]=true")
        else:
            plates = db_interactor.list_objects_with_name_and_id("plates")

        return plates, plates[0]["value"]


    """
        def populate_experiment_info()

    """
    @app.callback(
        # Output('Experiment-Info', 'children'),
        Output('switches-input', 'value'),
        Input('Experiment-List', 'value'),
        Input('show-experiment-button', 'n_clicks')
    )
    def populate_experiment_info(experiment_id, clicks):
        experiment = db_interactor.get_experiment(experiment_id)
        switch_value = [experiment.attributes["active"]]
        # print(type(switch_value[0]))
        # return json.dumps(experiment.to_json(), indent=4), switch_value
        return switch_value

    """
        def toggle_experiment_active()

    """
    @app.callback(
        Output('Experiment-Info', 'children'),
        Input('switches-input', 'value'),
        State('Experiment-List', 'value'),
    )
    def toggle_experiment_active(switch_value, experiment_id):
        experiment = db_interactor.get_experiment(experiment_id)
        # toggle switch doesn't hold state so we have to do a weird thing to get the value
        switch_state = True in switch_value
        if  experiment.attributes["active"] != switch_state:
            experiment.attributes["active"] = switch_state
            experiment.push()

        return json.dumps(experiment.to_json(), indent=4)

    """
        def populate_plate_info()

    """
    @app.callback(
        Output('plate-activate-switch', 'value'),
        Input('plates-list', 'value'),
        Input('show-experiment-button', 'n_clicks')
    )
    def populate_plate_info(plate_id, clicks):
        plate = db_interactor.get_plate(plate_id)
        switch_value = [plate.attributes["active"]]
        return switch_value

    """
        def toggle_plate_active()

    """
    @app.callback(
        Output('plate-info', 'children'),
        Input('plate-activate-switch', 'value'),
        State('plates-list', 'value'),
    )
    def toggle_plate_active(switch_value, plate_id):
        plate = db_interactor.get_plate(plate_id)
        # toggle switch doesn't hold state so we have to do a weird thing to get the value
        switch_state = True in switch_value
        if  plate.attributes["active"] != switch_state:
            plate.attributes["active"] = switch_state
            plate.push()

        return json.dumps(plate.to_json(), indent=4)
# import pip
# pip.main(['install', "dash"])

# import uuid, time
# import pytz
# from pytz import timezone, utc 
# import json
# import re
# import os
# import boto3
from datetime import datetime
from dash.dependencies import ALL


# ROOT_TOPIC = "telemetry"
# from braingeneers.iot import messaging 
# import uuid
# mb = messaging.MessageBroker("dashboard-" + str(uuid.uuid4())) 


import dash
from dash import dcc, html, Input, Output, State

import sys
import os
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard_helpers import *
app = dash.Dash(__name__)
allow_duplicate=True

#-------------------READ METADATA---------------------------------------------

def load_json():
    path = './metadata.json'
    try:
        with open(path, 'r') as file:
            metadata = json.load(file)
            metadata['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            return json.dumps(metadata, indent=4)
    except FileNotFoundError:
        print(f"The file {path} was not found.")
        return {}

#---------------------------------------------------------------------------------

app.layout = html.Div([

        html.H1('Experiment Dashboard'),
        dcc.Input(id='uuid-input', type='text', placeholder='Enter Experiment UUID', value='0000-00-00-efi-testing'),
        html.Button('Check UUID', id='submit-button'),
        html.Div(id='output-message'),
        html.Br(),
        dcc.Tabs(id='tabs-experiment', value = 'tab-control', className="custom-tab", children=[

        #-------------------Tab 1: Init---------------------------------------------
        dcc.Tab(label='Initialize', value='tab-init', children=[
            html.Div([

                html.H3('Enter Metadata Information'),
                html.Label([
                    'Update required fields including ',
                    html.Span('uuid', style={'fontWeight': 'bold'}), ', ',
                    html.Span('timestamp', style={'fontWeight': 'bold'}), ', ',
                    html.Span('maxwell_chip_id', style={'fontWeight': 'bold'}), ' and ',
                    html.Span('biology', style={'fontWeight': 'bold'}), ' notes: ',
                ]),     
                dcc.Textarea(
                    id='json-input',
                    style={'width': '100%', 'height': 600},
                    value=load_json()
                ),
                html.Button('Submit', id='submit-metadata-button', n_clicks=0),
                html.Div(id='container-button-basic', children='Enter JSON and press submit')
            ])
        ]),


        #-------------------Tab 2: Control ---------------------------------------------
        dcc.Tab(label='Control',  value='tab-control', children=[
                        
        html.Br(),
        html.Div(id='control-panel-div', className='three columns', children=[
            html.Label('Select device(s) to control:'),
            html.Br(),
            #dcc.Checklist(id='device-dropdown', options=[]),
            dcc.Dropdown(id='device-dropdown', multi=True, options=[]),
            html.Br(),

            html.Div([
                html.Button('Start', id='start-button', n_clicks=0),
                html.Button('End', id='end-button', n_clicks=0),
            ], style={'display': 'flex', 'gap': '10px', 'align-items': 'center'}),
            html.Div(id='start-output-div'),
            html.Div(id='end-output-div'),


        html.Div([
            html.Button('Ping', id='ping-button'),
            html.Button('Status', id='status-button'),
        ], style={'display': 'flex', 'gap': '10px', 'align-items': 'center'}),  # Added gap for space between buttons

        html.Div(id='ping-output-div'),
        html.Div(id='status-output-div'),
        html.Br(),


        html.Div([
            html.Label('Sec:'),
            dcc.Input(id='seconds-input', type='text', style={'width': '30px'}, placeholder='Enter seconds pause:', value='10'),
            html.Button('Pause', id='pause-button'),
            html.Button('Resume', id='resume-button'),

        ], style={'display': 'flex', 'gap': '10px', 'align-items': 'center'}),  # Added gap for space between buttons

        html.Div(id='pause-output-div'),
        html.Div(id='resume-output-div'),
        html.Br(),


        html.Div([
        dcc.Input(id='command-input', type='text', style={'width': '710px'}, placeholder='Enter command dictionary:', 
                    value='{"COMMAND": "TWIDDLE-REQUEST", "SECONDS": 10, "FROM": "dashboard"}'),
        html.Button('Command', id='command-button'),
        html.Button('Stop', id='stop-button'),
        html.Div(id='command-output-div'),
        html.Div(id='stop-output-div'),
        ], style={'display': 'flex', 'gap': '10px', 'align-items': 'center'}),  # Added gap for space between buttons

         html.Div([
        html.Button('Click for Example Commands', id='toggle-button'),]),
        # The Div you want to toggle
        html.Div([
            #html.Label('Example commands:'),
            html.Div([
                #html.Div('{"COMMAND": "ADD-REQUEST", "HAM": 1, "EGGS": 1, "SPAM": 1, "FROM": "dashboard"}', className='code-line'),
                html.Div('{"COMMAND": "TWIDDLE-REQUEST", "SECONDS": 10, "FROM": "dashboard"}', className='code-line'),
                html.Div('{"COMMAND": "FEED-REQUEST", "WELL_ID": "A?", "VOL": 150, "FROM": "dashboard"}', className='code-line'),
                html.Div('{"COMMAND": "DISPENSE-REQUEST", "WELL_ID": "A1", "VOL": 100, "FROM": "dashboard"}', className='code-line'),
                html.Div('{"COMMAND": "ASPIRATE-REQUEST", "WELL_ID": "B1", "VOL": 500, "FROM": "dashboard"}', className='code-line'),
                #html.Div('{"COMMAND": "PICTURE-REQUEST", "TYPE": ["pH", "volume"], "WELL_ID": "12345", "INDEX": "RIGHT",  "FROM": "dashboard"}', className='code-line'),
                #html.Div('{"COMMAND": "SCHEDULE-REQUEST", "TYPE": "ADD", "EVERY_X_SECONDS": "15", "FLAGS": "ONCE",  "DO": {"COMMAND": "PICTURE-REQUEST", "TYPE": ["pH"], "WELL_ID": "20302",  "INDEX": "RIGHT","FROM": "zambezi"}, "FROM": "zambezi"}'),
                html.Div('{"COMMAND": "SWAP-REQUEST", "WELL_ID": "12345", "CONFIG" : "chip20337-jul10.cfg", "FROM": "dashboard"}', className='code-line'),
                html.Div('{"COMMAND": "SWAP-REQUEST", "WELL_ID": "12345", "CONFIG" : "s3://braingeneers/integrated/0000-00-00-efi-testing/ephys/original/data/configs/test.cfg", "FROM": "dashboard"}', className='code-line'),
                html.Div('{"COMMAND": "RECORD-REQUEST", "WELL_ID": "12345", "MINUTES": 1, "FROM": "dashboard"}', className='code-line'),
                #html.Div('{"COMMAND": "ADD-REQUEST", "PAIRS": { "12345": "1" },  "FROM": "dashboard" }', className='code-line'),
                html.Div('{"COMMAND": "PICTURE-REQUEST", "WELL_ID":  ["12345"], "FROM": "dashboard" }', className='code-line'),
                html.Div('{"COMMAND": "SERVO-REQUEST", "SET_POSITION": ["OPENED", "CLOSED"], "WELL_ID": ["A1"], "FROM": "dashboard" }', className='code-line'),
                html.Div('{"COMMAND": "SET-REQUEST", "VALVE_ID": 2, "SET_POSITION": "OPENED"}', className='code-line'),
                html.Div('{"COMMAND": "SET-REQUEST", "VALVE_ID": 2, "SET_POSITION": "CLOSED"}', className='code-line'),
                html.Div('{"COMMAND": "TOGGLE-REQUEST", "VALVE_ID": 2}', className='code-line'),
                html.Div('{"COMMAND": "UPLOAD-REQUEST", "LOCAL_FILE": "", "S3_LOCATION": ""}', className='code-line'),
            ], style={
                'backgroundColor': '#f7f7f7',
                'border': '1px solid #ccc',
                'padding': '10px',
                'fontFamily': 'monospace',
                'borderRadius': '4px'
            })
        ], style={'marginBottom': '20px', 'display': 'block'}, id='toggle-div'),  # Note the ID assigned here for callback

       
        html.Div([

        html.Label('Every:'),
        dcc.Input(id='time-inverval-input', type='text', style={'width': '30px'}, placeholder='Enter schedule interval:', 
                    value='10'),
        #html.Div(id='time-interval-output-div'),
        dcc.RadioItems(
            id='time-selector',
            options=[
                {'label': 'Seconds', 'value': 'EVERY_X_SECONDS'},
                {'label': 'Minutes', 'value': 'EVERY_X_MINUTES'},
                {'label': 'Hours', 'value': 'EVERY_X_HOURS'},
                {'label': 'Days', 'value': 'EVERY_X_DAYS'}
            ],
            inline=True
        ),

        html.Label('If Hours or Days, at:'),
        dcc.Input(id='at-input', type='text', style={'width': '60px'}, placeholder='At:', 
                    value=':01'),

        #checkbox to run once
        dcc.Checklist(id='run-once-checklist', options=[{'label': 'Run Once', 'value': 'RUN_ONCE'}]),
        

        html.Button('Schedule-Add', id='sched-add-button'),
        html.Button('Schedule-Clear', id='sched-clear-button'),

        ], style={'display': 'flex', 'gap': '10px', 'align-items': 'center'}),  # Using flex to place items in a row
       
       
        html.Div(id='schedule-time-output-div'),
        html.Div(id='sched-add-output-div'),
        html.Div(id='sched-clear-output-div'),

        html.Br(),
     
        html.Label('Schedule-Clear remove job tagged (i.e,. 0, else all jobs will be removed):'),
        dcc.Input(id='tag-input', type='text', style={'width': '30px'}, value=''),
        html.Br(),
        html.Br(),


        html.Div(id='live-time-display'),
        dcc.Interval(
            id='interval-component',
            interval=1*1000,  # in milliseconds
            n_intervals=0
        ),

        html.Div(id='device-states'),  # Div to output the states of selected devices

        dcc.Interval(  # Add this Interval component
            id='interval-update',
            interval=1*1000,  # in milliseconds (1000ms == 1s)
            n_intervals=0
        )


        ])               
                        
        ]),
        
        #-------------------Tab 3: View Experiment---------------------------------------------
        dcc.Tab(label='View Experiment', value='tab-view', children=[


        #     html.Br(),
        #     #Make a refresh button
        #     html.Button('Refresh', id='refresh-button'),
        #     html.Br(),

           
        #     # html.Div(f'Experiment duration:'),
        #     #DD days, HH hours, MM min, Current time: HH:MM:SS

        #     # html.Div(f'Number of recordings'),
        #     # html.Div(f'Number of collection tubes used'),

        #     html.Div([
        #         #html.H1('Content for Tab View'),
        #         #html.Label('Automated Feeding log'),
        #         #X-axis: dates (MM:DD HH:SS)
        #         #Y-axis: mL
        #         #traces -- 
        #         #   Pumped (expected)
        #         #   Computer Vision (observed)


        # dcc.Graph(
        #         figure=dict(
        #             data=data_well1,
        #             layout=layout_well1
        #         ),
        #         style={'height': 300},
        #         id='my-graph-volume-well1'
        #     ),

        #     html.Br(),

        # dcc.Graph(
        #         figure=dict(
        #             data=data_well2,
        #             layout=layout_well2
        #         ),
        #         style={'height': 300},
        #         id='my-graph-volume-well2'
        #     ),
        #     html.Br(),

        # dcc.Graph(
        #         figure=dict(
        #             data=data_well1_error,
        #             layout=layout_well1_error
        #         ),
        #         style={'height': 300},
        #         id='my-graph-error-well1'
        #     ),

        #     html.Br(),

        # dcc.Graph(
        #         figure=dict(
        #             data=data_well2_error,
        #             layout=layout_well2_error
        #         ),
        #         style={'height': 300},
        #         id='my-graph-error-well2'
        #     ),


            # ])
        ]),

         ]),
        

])



@app.callback(
    Output('container-button-basic', 'children'),
    Input('submit-metadata-button', 'n_clicks'),
    State('json-input', 'value')
)
def update_output(n_clicks, value):
    if n_clicks > 0:
        try:
            # Attempt to parse the JSON to ensure it's valid
            data = json.loads(value)
            # Save the valid JSON back to the file
            #  # Convert the dict to a JSON-like string
            #print(data)

            if 'uuid' not in data or check_uuid_format(data['uuid']) == False:
                return 'Error, please enter a valid UUID.'

            s3_path = os.path.join(s3_basepath(data['uuid']), data['uuid'], 'metadata.json')
            try:
                with smart_open.open(s3_path, 'wb') as dest_file:
                    #metadata = json.dumps(value, indent=4)
                    #dest_file.write(metadata.encode('utf-8'))
                    
                    dest_file.write(value.encode('utf-8'))

            except Exception as e:
                print(f"Error uploading file: {e}")
                raise

            return html.Div([
                "JSON saved successfully to: ",
                html.Code(s3_path)
            ])
        #f"JSON saved successfully to: {s3_path}!"
        except json.JSONDecodeError:
            return 'Invalid JSON. Please correct and try again.'
    else:
        return 'Enter JSON and press submit'



@app.callback(
    Output('toggle-div', 'style'),
    [Input('toggle-button', 'n_clicks')]
)
def toggle_collapse(n):
    if n is None or n % 2 == 0:
        # Display the div
        return {'marginBottom': '20px', 'display': 'none'}
    else:
        # Hide the div
        return {'marginBottom': '20px', 'display': 'block'}


@app.callback(
    # Output('device-dropdown', 'options'),
    # [Input('device-dropdown', 'value')]
    Output('device-dropdown', 'options'),
    [Input('device-dropdown', 'value')]
)
def populate_device_checklist(value):
    online_devices_other = mb.list_devices_by_type("Other")
    online_devices_autoculture = mb.list_devices_by_type("Autoculture")
    online_devices = online_devices_other + online_devices_autoculture
    options = [{'label': d['label'], 'value': d['label']}for d in online_devices]
    return options


@app.callback(
    Output('device-states', 'children'),
    [Input('device-dropdown', 'value'),  # When selected devices change
     Input('interval-update', 'n_intervals')]  # When interval event is triggered
)
def update_device_states(selected_devices, n_intervals):
    if selected_devices is None or len(selected_devices) == 0:
        return 'No devices selected.'
    
    # Fetch and display the device states
    device_states = []
    for device in selected_devices:
        state = mb.get_device_state(device_name=device)
        state_str = json.dumps(state, indent=4)  # Convert the dict to a JSON-like string

        device_states.append(html.Pre(f'{device} State:\n{state_str}'))  # Using html.Pre for preformatted text
    
    return device_states

@app.callback(
    Output('output-message', 'children'),
    [Input('submit-button', 'n_clicks')],
    [dash.dependencies.State('uuid-input', 'value')]
)
def update_output(n_clicks, uuid_value):
    if n_clicks is None:
        # Button has not been clicked yet
        return 'Enter UUID and click the button to validate.'
    
    if check_uuid_format(uuid_value):
        return 'The UUID is in the correct format.'
    else:
        return 'The UUID is NOT in the correct format. Please check and try again.'


@app.callback(
    Output('start-output-div', 'children'),
    [Input('start-button', 'n_clicks'),
     State('device-dropdown', 'value'),
     State('uuid-input', 'value')]
)
def handle_start_end_button(clicks, selected_devices, uuid_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, start, online=True) #can be togglable later
        #start(uuid_value, selected_devices)
        return 'Started devices with given UUID'
    return dash.no_update

@app.callback(
    Output('end-output-div', 'children'),
    [Input('end-button', 'n_clicks'),
     State('device-dropdown', 'value'),
     State('uuid-input', 'value')]
)
def handle_end_button(clicks, selected_devices, uuid_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, end, online=True) #can be togglable later
        #end(uuid_value, selected_devices)
        return 'Ended devices with given UUID'
    return dash.no_update


@app.callback(
    Output('ping-output-div', 'children'),
    [Input('ping-button', 'n_clicks')],
    [State('device-dropdown', 'value'),
     State('uuid-input', 'value')]
)
def handle_ping_button(clicks, selected_devices, uuid_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, ping, online=True) #can be togglable later
        #ping(uuid_value, selected_devices)
        return 'Pinged selected devices on the UUID: ' + uuid_value
    return dash.no_update


@app.callback(
    Output('status-output-div', 'children'),
    [Input('status-button', 'n_clicks')],
    [State('device-dropdown', 'value'),
     State('uuid-input', 'value')]
)
def handle_status_button(clicks, selected_devices, uuid_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, status, online=True) #can be togglable later
        #status(uuid_value, selected_devices)
        return 'Requested status selected devices on the UUID: ' + uuid_value
    return dash.no_update



@app.callback(
    Output('pause-output-div', 'children'),
    [Input('pause-button', 'n_clicks')],
    [State('device-dropdown', 'value'),
     State('uuid-input', 'value'), 
     State('seconds-input', 'value')]
)
def handle_pause_button(clicks, selected_devices, uuid_value, seconds_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, pause, seconds_value, online=True) #can be togglable later
        #pause(uuid_value, selected_devices, seconds_value)
        return 'Pausing devices for ' + seconds_value
    return dash.no_update



@app.callback(
    Output('resume-output-div', 'children'),
    [Input('resume-button', 'n_clicks')],
    [State('device-dropdown', 'value'),
     State('uuid-input', 'value'), ]
)
def handle_resume_button(clicks, selected_devices, uuid_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, resume, online=True) #can be togglable later
        #resume(uuid_value, selected_devices)
        return 'Resuming devices'
    return dash.no_update


@app.callback(
    Output('stop-output-div', 'children'),
    [Input('stop-button', 'n_clicks')],
    [State('device-dropdown', 'value'),
     State('uuid-input', 'value'), ]
)
def handle_stop_button(clicks, selected_devices, uuid_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, stop, online=True) #can be togglable later
        #stop(uuid_value, selected_devices)
        return 'Stopping devices'
    return dash.no_update




@app.callback(
    Output('sched-clear-output-div', 'children'),
    [Input('sched-clear-button', 'n_clicks')],
    [State('device-dropdown', 'value'),
     State('uuid-input', 'value'), 
     State('tag-input', 'value'),]
)
def handle_sched_clear_button(clicks, selected_devices, uuid_value, tag):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, sched_clear, tag, online=True) #can be togglable later
        #sched_clear(uuid_value, selected_devices, tag)
        return 'Clearing schedules'
    return dash.no_update


@app.callback(
    Output('sched-add-output-div', 'children'),
    [Input('sched-add-button', 'n_clicks')],
    [State('device-dropdown', 'value'),
     State('uuid-input', 'value'), 
     State('time-selector', 'value'),
     State('time-inverval-input', 'value'),
     State('at-input', 'value'),
     State('command-input', 'value'),
     State('run-once-checklist', 'value')]
)
def handle_sched_add_button(clicks, selected_devices, uuid_value, interval_value, schdule_time_value, at_value, command_value, run_once_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, sched_add, interval_value, schdule_time_value, at_value, command_value,run_once_value, online=True) #can be togglable later
        #sched_add(uuid_value, selected_devices, interval_value, schdule_time_value, at_value, command_value,run_once_value)
        return 'Adding schedule'
    return dash.no_update


@app.callback(
    Output('command-output-div', 'children'),
    [Input('command-button', 'n_clicks')],
    [State('device-dropdown', 'value'),
     State('uuid-input', 'value'),
     State('command-input', 'value') ]
)
def handle_command_button(clicks, selected_devices, uuid_value, command_value):
    if clicks:
        send_to_all_teammates(uuid_value, selected_devices, command, command_value, online=True) #can be togglable later
        #command(uuid_value, selected_devices, command_value)
        return 'Sent command'
    return dash.no_update


@app.callback(
    Output('live-time-display', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_time(n):
    # Get the current time in UTC
    time_now = datetime.now().strftime('%H:%M:%S')
    return f"Current Time: {time_now}"


# Callback to update the variable based on radio item selection
@app.callback(
    Output('schedule-time-output-div', 'children'),
    [Input('time-selector', 'value')]
)
def update_value(selected_value):
    if selected_value == 'EVERY_X_SECONDS':
        return ''
    elif selected_value == 'EVERY_X_MINUTES':
        return ''
    if selected_value == 'EVERY_X_HOURS':
        return ''
    elif selected_value == 'EVERY_X_DAYS':
        return ''
    else:
        return 'Please select a time: Seconds, Minutes, Hours, or Days!'



if __name__ == '__main__':
    #app.run(debug=True, port=8051)
    app.run(
        host='0.0.0.0',
        port=8055,
        ssl_context=(
            '/etc/nginx/certs/slack-bridge.braingeneers.gi.ucsc.edu/cert.pem',
            '/etc/nginx/certs/slack-bridge.braingeneers.gi.ucsc.edu/key.pem'
        )
    )

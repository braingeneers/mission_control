#import braingeneers.utils.messaging as messaging
import braingeneers.iot.messaging as messaging
import braingeneers.iot.shadows as shadows

from github import Github
import datetime
import time
# from Experiment_Metadata_SQL import *
from users import PISCOPE_BOT_TOKEN
from dash.dependencies import Input, Output, State
import json
from dash import html
import pytz
import re
from Experiment_Metadata_SQL import *
from dotenv import load_dotenv
import os

load_dotenv()
endpoint =  os.getenv('SHADOWS_ENDPOINT')
if endpoint:
    print( "endpoint override")
    print( endpoint )
shadows_api_key = os.getenv('SHADOWS_API_KEY')
if shadows_api_key:
    print( "shadows_api_key override")

db_interactor = shadows.DatabaseInteractor(overwrite_endpoint=os.getenv('SHADOWS_ENDPOINT'), overwrite_api_key=os.getenv('SHADOWS_API_KEY'))
brokerString = "piscope-control-console-"+str(time.time())
mb=messaging.MessageBroker(brokerString)
gh = Github(PISCOPE_BOT_TOKEN)
repo = gh.get_repo("braingeneers/internal")

# def db_interactor.list_objects_with_name_and_id("experiments"):
#     # todo: make value the numerical id of the experiment in the database
#     return [{'label': d, 'value': d} for d in db_interactor.list_experiments() if d is not None]

def get_callbacks(app):
    @app.callback(
        Output("no-device-alert-fade", "is_open"),
        [Input("start-button", "n_clicks")],
        [State('picroscope-dropdown', 'value')]
        )
    def show_alert(clicked, device_name):
        if clicked and device_name is None:
            return True
        return False


    @app.callback(
        Output('raspistill-params', 'value'),
        Input('raspistill-param-presets', 'value'))
    def fill_param_box(value):
        return value


    """
     def populate_device_dropdown() 

     This function populates the device dropdown with the devices that are currently identified in the database.
    """
    @app.callback(
        output= Output('picroscope-dropdown', 'options'),
        inputs = [Input('picroscope-dropdown', 'search_value')])
    def populate_device_dropdown(options):
        # Get list of devices
        # online_devices=mb.list_devices_by_type(thingTypeName = "picroscope")
        online_devices = db_interactor.list_devices_by_type("BioPlateScope")
        # ret_val=[{'label': d, 'value': d} for d in online_devices if d != 'test']
        # return ret_val
        return online_devices

    """
     def populate_dropdowns() 

     This function populates the experiment and plate dropdowns with the experiments that are currently identified in the database.
    """
    @app.callback(
        Output('experiment-dropdown', 'options'),
        Output('plate-dropdown', 'options'),
        Input('refresh-dropdowns', 'n_clicks'))
    def populate_dropdowns(trigger):
        experiments = db_interactor.list_objects_with_name_and_id("experiments")
        plates = db_interactor.list_objects_with_name_and_id("plates")

        return experiments, plates

    # """
    #  def populate_experiment_dropdown() 

    #  This function populates the experiment dropdown with the experiments that are currently identified in the database.
    # """
    # @app.callback(
    #     output= Output('experiment-dropdown', 'options', allow_duplicate=True),
    #     inputs = [Input('experiment-dropdown', 'search_value')],
    #     prevent_initial_call=True )
    # def populate_experiment_dropdown(trigger):
    #     experiments = db_interactor.list_objects_with_name_and_id("experiments")

    #     return experiments

    # """
    #  def populate_plate_dropdown() 

    #  This function populates the plate dropdown with the plates that are currently identified in the database.
    # """
    # @app.callback(
    #     output= Output('plate-dropdown', 'options', allow_duplicate=True),
    #     inputs = [Input('plate-dropdown', 'search_value')],
    #     prevent_initial_call=True )
    # def populate_plate_dropdown(trigger):
    #     plates = db_interactor.list_objects_with_name_and_id("plates")

    #     return plates 

    """
    def display_relayout_data()

    Reads device shadow information from the database and displays it on the page.
    """
    @app.callback(
        Output("relayout-data", "children"),
        Output("device-name-display", "children"),
        Output("group-id-text", "children"),
        Output("last-connected", "children"),
        Output("uuid-display", "children"),
        Output('camera-dropdown', 'options'),
       # Output('plate-dropdown', 'options'),
       # Output('plate-dropdown', 'value'),
        Output('scope-name-header', "children"),
        Input('picroscope-dropdown', 'value'),
        Input('refresh-state', 'n_clicks')
    )
    def display_relayout_data(device_id, refresh):
        state_data = {}
        try:
            #plates = db_interactor.list_objects_with_name_and_id("plates", "?filters[interaction_things][id][$eq]={}".format(device_id))
            # plates = db_interactor.list_objects_with_name_and_id("plates","?filters[active][$eq]=true")
            # state_data = mb.get_device_state(device_name)
            #still labelled as device_name but it's now actually device_id
            state_data = db_interactor.get_device_state(device_id)
            name = db_interactor.get_device(device_id).attributes["name"]
            name = f'Selected Device: {name}'
            group_id_text = f'Group id: {state_data.get("group-id", "unset")}'
            uuid_text = f'UUID: {state_data.get("uuid", "unset")}'
            timestamp = state_data.get("connected", "error")
            cams = state_data.get("active_cameras", ["none"])
            cams_list=[{'label': d, 'value': d} for d in cams]
            datetimeObj = datetime.datetime.fromtimestamp(int(timestamp)/1000)
            initial_timezone = pytz.timezone('UTC')
            datetimeObj = initial_timezone.localize(datetimeObj)
            with_timezone = datetimeObj.astimezone(pytz.timezone('US/Pacific'))
            last_connected = f'Last Connected: {with_timezone.strftime("%Y-%m-%d %H:%M:%S")} PST'
        except(Exception):
            print("Exception in display_relayout_data")

            #print exception details
            
            # state_data = {}
            plates = [{"label": "select device to see plates", "value": "none"}]
            name = f'Selected Device:'
            group_id_text = f'Group id: unset'
            last_connected = f'Last Connected:'
            uuid_text = 'UUID: '
            cams_list = [{'label' :'test','value':'test1'}]
        return json.dumps(state_data, indent=4), name, group_id_text, last_connected, uuid_text, cams_list, name or None

    """"
    # callback: display_confirm
    # Summon experiment confirmation window when user clicks start button
    """
    @app.callback(
        Output('confirm-start', 'displayed'),
        Output('confirm-start', 'message'),
        inputs=[Input('start-button', 'n_clicks'),
                (State('picroscope-dropdown', 'value'),
                State('uuid-input', 'value'),
                State('interval-input', 'value'),
                State('stack-size-input', 'value'),
                State('step-offset-input', 'value'),
                State('step-size-input', 'value'),
                State('raspistill-params', 'value'),
                State('light-type', 'value'),
                State('group-id-text', 'children'))])
    def display_confirm(value, params):
        if value != 0 and params[0] is not None:
            message = """Confirm Experiment Parameters:
            Device: {}
            UUID: {}
            Interval: every {} hours
            Stack Size: {} layers
            Stack Offset: {} steps
            Layer Size: {} steps
            Raspistill API Parameters: {}
            Illumination Source: {}
            http://braingeneers.gi.ucsc.edu/images/{}/{}""".format(params[0],params[1],params[2],params[3],params[4],params[5],params[6],params[7],params[1],re.search('.$', params[8]).group())

            return True, message
        return False, "boof"



    """
    # callback: display_confirm_stop
    # Summon confirmation window when user clicks stop button
    """
    @app.callback(
        Output('confirm-stop', 'displayed'),
        Output('confirm-stop', 'message'),
        inputs=[Input('stop-button', 'n_clicks'),
                State('picroscope-dropdown', 'value')])
    def display_confirm_stop(value, piscope):
        if value != 0 and piscope is not None:
            message = """Are you sure you want to stop Picroscope {}""".format(piscope)

            return True, message
        return False, "boof"
        # return True


    """
    callback launch_experiment
    launch experiment when confirmation window button is hit
    """
    @app.callback(Output('experiment-launch-alert', 'is_open'),
                inputs=[Input('confirm-start', 'submit_n_clicks'),
                        (State('picroscope-dropdown', 'value'),
                        State('uuid-input', 'value'),
                        State('interval-input', 'value'),
                        State('stack-size-input', 'value'),
                        State('step-offset-input', 'value'),
                        State('step-size-input', 'value'),
                        State('raspistill-params', 'value'),
                        State('light-type', 'value'),
                        State('group-id-text', 'children'),
                        State('experiment-dropdown','value'),
                        State('plate-dropdown','value')),
                        State('github-checkbox','value')])
    def launch_experiment(submit, params, issue):
        if submit:
            packet = {}
            packet["uuid"] = params[1]
            packet["params"]={}
            packet["params"]["interval"]=params[2]
            packet["params"]["stack_size"]=params[3]
            packet["params"]["stack_offset"]=params[4]
            packet["params"]["step_size"]=params[5]
            packet["params"]["camera_params"]=params[6]
            packet["params"]["light_mode"]=params[7]
            packet = json.dumps(packet)


            '''
            Here we have all the strapi object related commands, connecting the experiment, plate and device to each other
            '''
            device = db_interactor.get_device(params[0])
            exp = db_interactor.get_experiment(params[9])
            plate = db_interactor.get_plate(params[10])
            exp.add_plate(plate)
            device.set_current_experiment(exp)
            device.set_current_plate(plate)
            db_interactor.start_image_capture(device,params[1])


            mb.publish_message("imaging/"+device.attributes["name"]+"/start",packet)
            #create uuid object here and insert into database
            # insert_uuid(UUID(params[1],params[9], repr(Thing("Picroscope",params[0])), packet))
            try:
                if issue[0] == 'generate':
                    # >>> repo = g.get_repo("PyGithub/PyGithub")
                    # >>> issue = repo.get_issue(number=874)
                    # >>> issue.create_comment("Test")
                    #     IssueComment(user=NamedUser(login="user"), id=36763078)
                    repo.create_issue(title=f'Batch: {params[1]}',
                            body = """{}
                            Device: {}
                            UUID: {}
                            Interval: every {} hours
                            Stack Size: {} layers
                            Stack Offset: {} steps
                            Layer Size: {} steps
                            Raspistill API Parameters: {}
                            Illumination Source: {}
                            http://braingeneers.gi.ucsc.edu:8055/images/{}/{}

                            This issue was generated by a bot, contact pvbaudin@ucsc.edu if there are problems""".format(device.attributes["name"],params[0],params[1],params[2],params[3],params[4],params[5],params[6],params[7],params[1],re.search('.$', params[8]).group())
                    )
            except IndexError:
                pass
                #hack because when checkbox not selected issue is empty
            return True
        #    mb.update_device_state('Forky', {"uuid": "test-blahblahblah", "notes": [value, "the frog liked to eat"]})
        # Console.log(value)
        return False

    """
    callback stop_experiment
    stop experiment when confirmation window button is hit
    
    sample packet to start picscope experiment
    andy/start/{
      "uuid": "2022-01-13",
      "params": {
        "interval": 2,
        "stack_size": 5,
        "stack_offset": 500,
        "step_size": 100,
        "camera_params": "-t 4000 -awb off -awbg 1,1 -o",
        "light_mode": "white"
      }
    }
    """
    @app.callback(Output('experiment-stop-alert', 'is_open'),
                inputs=[Input('confirm-stop', 'submit_n_clicks'),
                        State('picroscope-dropdown', 'value')])
    def stop_experiment(submit, piscope):
        if submit:
            device = db_interactor.get_device(piscope)
            mb.publish_message("imaging/"+device.attributes["name"] +"/stop","{}")
            return True
        #    mb.update_device_state('Forky', {"uuid": "test-blahblahblah", "notes": [value, "the frog liked to eat"]})
        return False


    @app.callback(Output('move-up', 'n_clicks'),
                Output('reset-focus','n_clicks'),
                Output('x-right', 'n_clicks'),
                Output('x-left', 'n_clicks'),
                Output('y-up', 'n_clicks'),
                Output('y-down', 'n_clicks'),
                Output('l-above', 'n_clicks'),
                Output('l-below', 'n_clicks'),
                Output('l-off', 'n_clicks'),
                Output('stop-stream', 'n_clicks'), #reset clicks for logic to work
                inputs=[(Input('move-up', 'n_clicks'),
                        Input('reset-focus', 'n_clicks'),
                        Input('x-right', 'n_clicks'),
                        Input('x-left', 'n_clicks'),
                        Input('y-up', 'n_clicks'),
                        Input('y-down', 'n_clicks'),
                        Input('l-above', 'n_clicks'),
                        Input('l-below', 'n_clicks'),
                        Input('l-off', 'n_clicks'),
                        Input('stop-stream', 'n_clicks')),
                        (State('picroscope-dropdown', 'value'),
                        State('camera-dropdown', 'value'))])
    def move_motors(buttons, params):
        if any(buttons):
            packet = {}
            packet["camera"] = params[1]
            packet = json.dumps(packet)
            button_list = ["z100","reset","xRight100","xLeft100","yUp100","yDown100","lAbove","lBelow","lOff","sOff"]
            for i in range(len(buttons)):
                if buttons[i]:
                    try:
                        name = db_interactor.get_device(params[0]).attributes["name"] or None
                    except:
                        name = None
                    mb.publish_message("imaging/"+name +"/" + button_list[i], packet)
                    break
            # if buttons[0]:
            #     mb.publish_message(params[0] +"/move100",packet)
            # if up != 0:
            #     mb.publish_message(params[0] +"/move100",packet)
            #
            # else:
            #     mb.publish_message(params[0] +"/reset",packet)
            return 0,0,0,0,0,0,0,0,0,0
        return 0,0,0,0,0,0,0,0,0,0

    ##
    # callback switch_stream_source
    # pass message to hub pi to change source of livestream, also reload iframe, which probably wont work since it will take time to switch the stream
    ##
    @app.callback(Output('iframe-src','children'),
                Output('show-cam-panel', 'n_clicks'),
                inputs=[Input('camera-dropdown', 'value'),
                        Input('show-cam-panel', 'n_clicks'),
                        State('picroscope-dropdown', 'value'),
                        State('group-id-text', 'children'),])
    def switch_stream_source(camera, show_full_panel, hub, gid):
        try:
            hub = db_interactor.get_device(hub).attributes["name"]
        except:
            hub = None
        if (show_full_panel):
            frame = html.Iframe(id=str(show_full_panel + 2222), src=os.getenv('LIVESTREAM_ENDPOINT')+hub.lower()+"stream/camera"+gid[-1]+str(camera)+"/",
                            style={"height": "640px", "width": "640px"})
        elif(camera):
            mb.publish_message("imaging/"+hub +"/switch",camera)
            frame = html.Iframe(id=str(hub)+str(camera), src=os.getenv('LIVESTREAM_ENDPOINT')+hub.lower()+"stream/camera"+gid[-1]+str(camera)+"/min.php",
                            style={"height": "640px", "width": "640px"})
        else:
            frame = html.Iframe(id="first", src=os.getenv('LIVESTREAM_ENDPOINT')+"livestream/min.php",
                            style={"height": "640px", "width": "640px"})

        return frame, 0

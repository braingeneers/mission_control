from braingeneers.iot import messaging
import uuid
from datetime import datetime
import json
import re
import os
#import smartopen from braingeneers
import braingeneers.utils.smart_open_braingeneers as smart_open

ROOT_TOPIC = "telemetry"
logging_token = "log" #for message logging job container to parse and write to csv 

# Global message broker - will be initialized when needed
mb = messaging.MessageBroker("dashboard-" + str(uuid.uuid4()))

def generate_topic(uuid, device="", cmnd="", message_type=""):
    """Generate MQTT topic string"""
    if device:
        return f'{ROOT_TOPIC}/{uuid}/{logging_token}/{device}/{cmnd}/{message_type}'
    return f'{ROOT_TOPIC}/{uuid}/{logging_token}/{cmnd}/{message_type}'

def send_message(uuid, device, message, cmnd="", message_type="", online=True):
    """Send message to a single teammate or return message data if offline"""
    topic = generate_topic(uuid, device, cmnd, message_type) if device else generate_topic(uuid, cmnd=cmnd, message_type=message_type)
    
    if online:
        mb.publish_message(topic, message)
        return None
    return (topic, message)

def start(uuid, device, online=True):
    """Send start command for a single teammate"""
    topic = generate_topic("NONE", device, cmnd="START", message_type="REQUEST")
    message = {
        "COMMAND": "START-REQUEST",
        "UUID": uuid,
        "TEAMMATES": []  # Teammates list should be populated by caller
    }
    if online:
        mb.publish_message(topic, message)
        return None
    return (topic, message)

def end(uuid, device, online=True):
    """Send end command"""
    message = {"COMMAND": "END-REQUEST"}
    return send_message(uuid, device, message, cmnd="END", message_type="REQUEST", online=online)

def ping(uuid, device, online=True):
    """Send ping command"""
    message = {"COMMAND": "PING-REQUEST"}
    return send_message(uuid, device, message, cmnd="PING", message_type="REQUEST", online=online)

def status(uuid, device, online=True):
    """Send status request"""
    message = {"COMMAND": "STATUS-REQUEST"}
    return send_message(uuid, device, message, cmnd="STATUS", message_type="REQUEST", online=online)

def pause(uuid, device, seconds, online=True):
    """Send pause command"""
    message = {"COMMAND": "PAUSE-REQUEST", "SECONDS": seconds, "FROM": "dashboard"}
    return send_message(uuid, device, message, cmnd="PAUSE", message_type="REQUEST", online=online)

def resume(uuid, device, online=True):
    """Send resume command"""
    message = {"COMMAND": "RESUME-REQUEST", "FROM": "dashboard"}
    return send_message(uuid, device, message, cmnd="RESUME", message_type="REQUEST", online=online)

def stop(uuid, device, online=True):
    """Send stop command"""
    message = {"COMMAND": "STOP-REQUEST", "FROM": "dashboard"}
    return send_message(uuid, device, message, cmnd="STOP", message_type="REQUEST", online=online)

def sched_clear(uuid, device, tag, online=True):
    """Clear scheduled tasks"""
    message = {
        "COMMAND": "SCHEDULE-REQUEST",
        "TYPE": "CLEAR",
        "TAG": tag,
        "FROM": "dashboard"
    }
    return send_message(uuid, device, message, cmnd="SCHEDULE", message_type="REQUEST", online=online)

def sched_add(uuid, device, interval, schedule_time, at, command_value, run_once_value, online=True):
    """Add scheduled task"""
    message = {
        "COMMAND": "SCHEDULE-REQUEST",
        "TYPE": "ADD",
        interval: schedule_time,
        "AT": at,
        "DO": json.loads(command_value),
        "FROM": "dashboard"
    }
    if run_once_value:
        message["FLAGS"] = "ONCE"
    return send_message(uuid, device, message, cmnd="SCHEDULE", message_type="REQUEST", online=online)

def command(uuid, device, command_value, online=True):
    """Send custom command for a single teammate
    Args:
        uuid (str): Experiment UUID
        device (str): Teammate device
        command_value (str): JSON string containing command (handles various quote types)
        online (bool): Whether to send message or return data
    """
    # Handle different quote characters by replacing them with standard quotes
    command_value = command_value.replace('"', '"').replace('"', '"')  # Smart quotes
    command_value = command_value.replace("'", '"').replace('`', '"')  # Single and backticks
    command_value = command_value.replace('＂', '"').replace('＇', '"')  # Full-width quotes
    
    try:
        parsed_command = json.loads(command_value)
    except json.JSONDecodeError:
        # If JSON parsing fails, try cleaning the string further
        command_value = ''.join(c for c in command_value if ord(c) < 128)  # Remove non-ASCII chars
        try:
            parsed_command = json.loads(command_value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid command format: {e}. Command must be valid JSON.")

    try:
        cmnd, message_type = parsed_command["COMMAND"].split("-")
    except (KeyError, ValueError):
        raise ValueError("Command must contain 'COMMAND' key with format 'COMMAND-TYPE'")
    
    return send_message(uuid, device, command_value, cmnd, message_type, online=online)

# Example usage:
def send_to_all_teammates(uuid, teammates, command_func, *args, online=True):
    results = []
    for device in teammates:
        result = command_func(uuid, device, *args, online=online)
        if not online and result:
            results.append(result)
    return results if not online else None

# Utility functions
def create_uuid(experiment_type, experiment_name):
    """Create a UUID for an experiment"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    return f"{date_str}-{experiment_type}-{experiment_name}"

def check_uuid_format(uuid_string):
    """Validate UUID format"""
    pattern = r'^\d{4}-\d{2}-\d{2}-[efi]+-([\w-]+)$'
    return bool(re.match(pattern, uuid_string))

def s3_basepath(UUID):
    """Get S3 base path for experiment type"""
    base_path = 's3://braingeneers/'
    if UUID == "NONE": return base_path + 'integrated/'
    match = re.search(r'-[a-z]*-', UUID)
    if not match: return base_path + 'integrated/'
    type_mapping = {
        "-e-": "ephys/",
        "-f-": "fluidics/",
        "-i-": "imaging/",
    }
    return base_path + type_mapping.get(match.group(0), 'integrated/')

# def update_output(n_clicks, uuid, maxwell_chip_id):
#     if n_clicks is None:
#         return 'Enter metadata and click the button.'
#     else:
#         # Prepare and save metadata
#         data = {}  # Initialize your data dictionary
#         data['uuid'] = uuid
#         data['notes'] = {"biology": {'maxwell_chip_id': maxwell_chip_id}}
#         # Populate other fields similarly

#         path_to_file = './metadata.json'

#         # Save to file
#         try:
#             with open(path_to_file, 'w') as file:
#                 json.dump(data, file, indent=4)
#         except FileNotFoundError:
#             return "File not found."

#         # Upload to S3
#         s3_path = os.path.join(s3_basepath(uuid), uuid, 'metadata.json')
#         try:
#             with open(path_to_file, 'rb') as source_file:
#                 file_data = source_file.read()
#             with smart_open.open(s3_path, 'wb') as dest_file:
#                 dest_file.write(file_data)
#             return 'Metadata saved and uploaded successfully.'
#         except Exception as e:
#             return f"Error uploading file: {e}"
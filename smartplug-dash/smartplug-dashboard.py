# run as:
# streamlit run smartplug-dashbaord.py 
import streamlit as st
from braingeneers.iot import messaging
from braingeneers.iot import *
import time

# Import other necessary modules
#st.set_page_config(layout="wide")


# Sidebar layout
st.sidebar.title("Smartplug Dashboard")


if 'message_broker' not in st.session_state:
    st.session_state.message_broker = messaging.MessageBroker("mqtt-logger-" + str(uuid.uuid4()))
    st.session_state.q = messaging.CallableQueue()


if 'smartplug_role_call' not in st.session_state:   
    st.session_state.smartplug_role_call = []
    st.session_state.message_broker.subscribe_message(topic=f"smartplug/telemetry/+/stat/RESULT", callback=st.session_state.q)
    st.session_state.message_broker.publish_message(topic=f"smartplug/telemetry/tasmotas/cmnd/POWER", message="" )  # turn on smart plug
    time.sleep(1)
    while not st.session_state.q.empty():
        topic, message = st.session_state.q.get()
        st.session_state.smartplug_role_call.append(topic.split("/")[2])
    formatted_smartplugs = ", ".join(st.session_state.smartplug_role_call)
    st.toast(f"Found smartplugs: \n { formatted_smartplugs }")
    st.session_state.message_broker.unsubscribe_message(topic=f"smartplug/telemetry/+/stat/RESULT")


smartplugs_list = st.session_state.smartplug_role_call #["lovelace", "mcclintock", "coleman", "vaughan", "blackburn", "cori", "nile_plug", "congo_plug", "zambezi_plug", "riogrande_plug"]
smartplug = st.sidebar.multiselect("Choose smartplug(s) to toggle:", smartplugs_list)


st.title("")


def toggle_smartplugs(action):
    if not smartplug:
        st.error("Please select a smartplug")
        return

    for smartplug_instance in smartplug:
        st.session_state.message_broker.subscribe_message(topic=f"smartplug/telemetry/{smartplug_instance}/stat/RESULT", callback=st.session_state.q)
        st.session_state.message_broker.publish_message(topic=f"smartplug/telemetry/{smartplug_instance}/cmnd/POWER", message=action)
        

        start_time = time.time()
        while (time.time() - start_time) < 5 and st.session_state.q.empty():
            time.sleep(1)
        
        if st.session_state.q.empty():
            st.toast("No response from smartplug. Please check the connection.")
        
        while not st.session_state.q.empty():
            topic, message = st.session_state.q.get()
            st.toast(f"Received message on topic {topic}: {message}")
            if "POWER" in message.keys():
                if message["POWER"] == "ON":
                    st.toast(f"🟢 {smartplug_instance} is ON")
                    st.balloons()

                else: #OFF
                    st.toast(f"🔵 {smartplug_instance} is OFF")
                    st.snow()

            else:
                st.toast(f"{smartplug_instance} uncategorized message received: {message}")

if st.button('ON'):
    toggle_smartplugs("ON")

if st.button('OFF'):
    toggle_smartplugs("OFF")

if st.button(f"STATUS"):
    toggle_smartplugs("")



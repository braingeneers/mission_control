#!/bin/bash

mosquitto_pub -h mqtt.braingeneers.gi.ucsc.edu -t "services/mqtt_job_listener/REFRESH" -m "{}" -u braingeneers -P $(awk '/profile-key/ {print $NF}' ~/.aws/credentials)

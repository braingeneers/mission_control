#!/bin/bash

ENDPOINT=${ENDPOINT:-https://s3-west.nrp-nautilus.io}

aws --endpoint ${ENDPOINT} s3 cp jobs.csv s3://braingeneers/services/mqtt_job_listener/jobs.csv

mosquitto_pub -h mqtt.braingeneers.gi.ucsc.edu -t "services/mqtt_job_listener/REFRESH" -m "{}" -u braingeneers -P $(awk '/profile-key/ {print $NF}' ~/.aws/credentials)

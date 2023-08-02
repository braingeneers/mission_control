#!/bin/bash

aws --endpoint ${ENDPOINT} s3 cp src/jobs.csv s3://braingeneers/services/mqtt_job_listener/jobs.csv

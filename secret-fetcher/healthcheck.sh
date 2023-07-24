#!/bin/bash

if [ -f /tmp/SECRET_FETCHER_COMPLETE_TOKEN ]; then
    exit 0
else
    exit 1
fi

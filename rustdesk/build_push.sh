#!/bin/bash

docker build -f Dockerfile -t braingeneers/rustdesk-server:latest .
docker push braingeneers/rustdesk-server:latest

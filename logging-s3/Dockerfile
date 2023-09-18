FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -q -y update && \
    apt-get -q -y upgrade && \
    apt-get -q -y install \
        make git software-properties-common build-essential virtualenv libssl-dev libffi-dev \
        libncurses5-dev curl zip unzip cmake wget docker.io python3-pip python3-virtualenv \
        npm nodejs tzdata jq nano awscli && \
    apt-get clean

RUN python3 -m pip install --force-reinstall git+https://github.com/braingeneers/braingeneerspy.git#egg=braingeneerspy[iot,analysis,data]

COPY log.py /tmp/log.py

ENTRYPOINT python3 /tmp/log.py

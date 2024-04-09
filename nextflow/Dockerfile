# Long Running Docker Image that listens to an MQTT topic like "start/workflow"
# to trigger launching nextflow workflows.
#
# To build this image, run (in this directory):
#
#   docker build . -t quay.io/ucsc_cgl/nextflow-launcher:latest
#
# To push this image, run:
#
#   docker push quay.io/ucsc_cgl/nextflow-launcher:latest
#
FROM nextflow/nextflow:latest

RUN yum install python3 epel openssl11-devel zlib-devel bzip2-devel libffi-devel sqlite-devel git wget tar make gcc -y
# manually install python3.11 because we're on centos
RUN cd /tmp && wget https://www.python.org/ftp/python/3.11.5/Python-3.11.5.tgz && tar -xzf Python-3.11.5.tgz && cd Python-3.11.5 && ./configure --enable-optimizations && make altinstall
RUN python3.11 -m pip install pip --upgrade
RUN pip3.11 install --upgrade pip
RUN python3.11 -m pip install awscli diskcache
# always install the bleeding edge of braingeneerspy
RUN python3.11 -m pip install git+https://github.com/braingeneers/braingeneerspy.git@master
RUN yum install curl -y
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

COPY run.py /usr/local/bin/run.py

ENTRYPOINT python3.11 /usr/local/bin/run.py

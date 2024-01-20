#"""
#'docker run --rm -t '
#                               '--volume ~/.aws/:/root/.aws/ --volume ~/.kube/:/root/.kube/ --volume ~/.local/bin/:/usr/local/sbin/ '
#                               'nextflow/nextflow:latest '
#"""
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /tmp

RUN apt-get -q -y update && \
    apt-get -q -y upgrade && \
    apt-get -q -y install \
        make git software-properties-common build-essential virtualenv libssl-dev libffi-dev \
        libncurses5-dev curl zip unzip cmake wget docker.io python3-pip python3-virtualenv \
        npm nodejs tzdata jq nano awscli && \
    apt-get clean

RUN cd /usr/local/bin && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && chmod 1777 kubectl
RUN python3 -m pip install git+https://github.com/braingeneers/braingeneerspy.git docker

COPY run.py /tmp/run.py
COPY workflows/demo/nextflow.config /tmp/nextflow.config
RUN cd /tmp && wget https://raw.githubusercontent.com/DailyDreaming/k8-nextflow/master/nextflow.config
RUN cd /usr/local/bin && wget https://github.com/nextflow-io/nextflow/releases/download/v23.10.1/nextflow && chmod 1777 nextflow
RUN apt install default-jre -y
RUN which nextflow
RUN echo $PATH
RUN nextflow kuberun https://github.com/DailyDreaming/k8-nextflow -v whimvol:/workspace -head-cpus 1 -head-memory 256Mi --xyz zyx || true

ENTRYPOINT python3 /tmp/run.py

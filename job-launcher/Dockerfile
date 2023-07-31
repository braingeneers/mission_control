FROM braingeneers/braingeneers:latest

RUN python -m pip install --no-cache-dir --upgrade pip \
    kubernetes

RUN sudo apt-get update && sudo apt-get install -y \
    iputils-ping \
    dnsutils

COPY src/run.sh /app/run.sh
COPY src/k8s_job_creator.py /app/k8s_job_creator.py

# set working directory
WORKDIR /app

ENTRYPOINT ["/app/run.sh"]

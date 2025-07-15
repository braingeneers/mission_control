FROM braingeneers/braingeneers:latest

# apt installs
USER root
RUN apt-get update && \
    apt-get install -y jq curl && \
    curl -L https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 \
         -o /usr/local/bin/yq && \
    chmod +x /usr/local/bin/yq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
USER jovyan

WORKDIR /data_lifecycle
COPY . /data_lifecycle

FROM braingeneers/braingeneers:latest

LABEL org.opencontainers.image.source="https://github.com/braingeneers/mission_control/tree/main/data-lifecycle" \
      org.opencontainers.image.description="Braingeneers data lifecycle backup and retention report runtime"

# apt installs
USER root
RUN apt-get update && \
    apt-get install -y jq curl && \
    curl -L https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 \
         -o /usr/local/bin/yq && \
    chmod +x /usr/local/bin/yq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get remove -y rclone && \
    sudo -v ; curl https://rclone.org/install.sh | sudo bash

RUN touch /etc/mtab
USER jovyan

WORKDIR /data_lifecycle
COPY . /data_lifecycle

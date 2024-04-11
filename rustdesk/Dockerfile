FROM rustdesk/rustdesk-server:1.1.9-amd64

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    awscli

COPY hbbr_entrypoint.sh /root/hbbr_entrypoint.sh

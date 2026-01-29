FROM rustdesk/rustdesk-server:1.1.15-amd64 AS rustdesk

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    awscli \
 && rm -rf /var/lib/apt/lists/*

COPY --from=rustdesk /usr/bin/hbbs /usr/bin/hbbs
COPY --from=rustdesk /usr/bin/hbbr /usr/bin/hbbr

COPY hbbr_entrypoint.sh /root/hbbr_entrypoint.sh
RUN chmod +x /root/hbbr_entrypoint.sh

WORKDIR /root

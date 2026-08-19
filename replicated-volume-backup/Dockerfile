FROM alpine:3.22

ARG SUPERCRONIC_VERSION=v0.2.48
ARG SUPERCRONIC_SHA1=016b7c9aebfc8d9fd9526e8ba33b191fc524485f

RUN apk add --no-cache \
        aws-cli \
        ca-certificates \
        su-exec \
        tzdata \
        util-linux \
    && wget -q \
        "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64" \
        -O /usr/local/bin/supercronic \
    && echo "${SUPERCRONIC_SHA1}  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod 0755 /usr/local/bin/supercronic \
    && addgroup -g 1000 backup \
    && adduser -D -u 1000 -G backup backup

COPY crontab /etc/replicated-volume-backup/crontab
COPY replicated-volume-backup /usr/local/bin/replicated-volume-backup
COPY sync-replicated-volume /usr/local/bin/sync-replicated-volume
COPY sync-replicated-volume-once /usr/local/libexec/sync-replicated-volume-once
COPY healthcheck /usr/local/bin/replicated-volume-backup-healthcheck

RUN chmod 0644 /etc/replicated-volume-backup/crontab \
    && chmod 0755 \
        /usr/local/bin/replicated-volume-backup \
        /usr/local/bin/sync-replicated-volume \
        /usr/local/libexec/sync-replicated-volume-once \
        /usr/local/bin/replicated-volume-backup-healthcheck

ENV AWS_SHARED_CREDENTIALS_FILE=/secrets/prp-s3-credentials/credentials \
    REPLICATED_SYNC_DESTINATION=s3://braingeneersdev/services/replicated/ \
    REPLICATED_SYNC_SOURCE=/replicated \
    REPLICATED_SYNC_STATE_DIR=/local/replicated-volume-backup \
    TZ=America/Los_Angeles

HEALTHCHECK --interval=5m --timeout=10s --retries=3 \
    CMD ["replicated-volume-backup-healthcheck"]

ENTRYPOINT ["replicated-volume-backup"]
CMD ["schedule"]

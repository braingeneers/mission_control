FROM docker:29.9.3-cli@sha256:2357639ad1ea7d0194134bf3292622fd4e562483966ed674e5d7c945b5f3b28d

RUN apk add --no-cache python3
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/braingeneers/mission_control" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
COPY maintenance.py /app/maintenance.py
HEALTHCHECK --interval=5m --timeout=10s --start-period=3m --retries=1 \
    CMD ["python3", "/app/maintenance.py", "healthcheck"]
ENTRYPOINT ["python3", "/app/maintenance.py"]
CMD ["run"]

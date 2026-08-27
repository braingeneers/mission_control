# syntax=docker/dockerfile:1.7

FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171 AS tools

ARG TARGETARCH=amd64
ARG AWS_CLI_VERSION=2.36.32
ARG AWS_CLI_SHA256=ddd7a5aabf363f5b82085ef732c806d4fe73ad0d10e35cffedd5c3560f56a641
ARG RCLONE_VERSION=v1.75.0
ARG RCLONE_SHA256=aa2804e08f48250e71009c727124b6341cd0288465804a9a09d14663cabafbaa
ARG YQ_VERSION=v4.53.6
ARG YQ_SHA256=c5f056448f973ae7d39b5401949648a78f2dc1947d6a8eb65be60d5c504b9385

RUN test "${TARGETARCH}" = "amd64" && \
    apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl unzip && \
    curl --fail --location --show-error \
      "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-${AWS_CLI_VERSION}.zip" \
      --output /tmp/awscliv2.zip && \
    echo "${AWS_CLI_SHA256}  /tmp/awscliv2.zip" | sha256sum --check --strict && \
    unzip -q /tmp/awscliv2.zip -d /tmp/awscliv2 && \
    /tmp/awscliv2/aws/install --install-dir /opt/aws-cli --bin-dir /opt/bin && \
    curl --fail --location --show-error \
      "https://downloads.rclone.org/${RCLONE_VERSION}/rclone-${RCLONE_VERSION}-linux-amd64.zip" \
      --output /tmp/rclone.zip && \
    echo "${RCLONE_SHA256}  /tmp/rclone.zip" | sha256sum --check --strict && \
    unzip -p /tmp/rclone.zip "rclone-${RCLONE_VERSION}-linux-amd64/rclone" > /tmp/rclone && \
    install -m 0755 /tmp/rclone /opt/bin/rclone && \
    curl --fail --location --show-error \
      "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
      --output /tmp/yq && \
    echo "${YQ_SHA256}  /tmp/yq" | sha256sum --check --strict && \
    install -m 0755 /tmp/yq /opt/bin/yq


FROM python:3.11.16-slim-bookworm@sha256:0bee7276f83efd4a1ee05bbbf4281d95ed28e079220a9457f25a93e3f1e3c31b

LABEL org.opencontainers.image.source="https://github.com/braingeneers/mission_control/tree/main/data-lifecycle" \
      org.opencontainers.image.description="Braingeneers data lifecycle backup and retention report runtime"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      coreutils \
      findutils \
      gawk \
      grep \
      gzip \
      jq \
      procps \
      sed && \
    apt-get clean && \
    find /var/lib/apt/lists -type f -delete && \
    useradd --uid 1000 --gid 100 --create-home --shell /bin/bash jovyan

COPY --from=tools /opt/aws-cli /opt/aws-cli
COPY --from=tools /opt/bin/rclone /usr/local/bin/rclone
COPY --from=tools /opt/bin/yq /usr/local/bin/yq
COPY requirements.txt /tmp/requirements.txt

RUN python -m pip install --no-cache-dir --requirement /tmp/requirements.txt && \
    find /tmp -mindepth 1 -delete

ENV AWS_PAGER="" \
    HOME=/home/jovyan \
    MPLCONFIGDIR=/tmp/matplotlib \
    PATH="/opt/aws-cli/v2/current/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR /data_lifecycle
COPY --chown=1000:100 . /data_lifecycle

USER jovyan

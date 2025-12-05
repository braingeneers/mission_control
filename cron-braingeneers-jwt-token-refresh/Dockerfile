# All braingeneers services require authentication via Auth0->CILogon (integrates with UCSC authentication)
# A service account token can be obtained in braingeneerspy after successful autentication. This token is automatically
# refreshed once a week as long as the code is used at least once a month.
# A service account token is also stored in the NRP kubernetes secrets, this is needed for jobs run on the NRP.
# Jobs being run on the NRP require user authentication, so keeping the token in kubernetes secrets is secured.
# This cron task updates the service account token in the NRP/kubernetes/secrets daily.
FROM debian:12-slim

# Install dependencies + kubectl
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        unzip && \
    curl -fsSLo /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x /usr/local/bin/kubectl && \
    rm -rf /var/lib/apt/lists/*

# Install kubectl oidc-login plugin (kubelogin) from GitHub releases
RUN set -eux; \
    arch="$(uname -m)"; \
    case "$arch" in \
      x86_64)  kubelogin_arch=amd64 ;; \
      aarch64) kubelogin_arch=arm64 ;; \
      *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSLo /tmp/kubelogin.zip \
      "https://github.com/int128/kubelogin/releases/latest/download/kubelogin_linux_${kubelogin_arch}.zip"; \
    cd /usr/local/bin; \
    unzip /tmp/kubelogin.zip; \
    # kubectl discovers plugins by the kubectl-* naming convention
    mv kubelogin kubectl-oidc_login; \
    chmod +x kubectl-oidc_login; \
    rm /tmp/kubelogin.zip

COPY refresh-braingeneers-jwt-service-account-token.sh /
ENTRYPOINT ["/refresh-braingeneers-jwt-service-account-token.sh"]

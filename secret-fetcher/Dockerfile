# The secret-fetcher container retrieves all secrets in the `braingeneers` namespace on kubernetes.
# The files are saved to a shared volume typically mounted at `/secrets`. So for example, the AWS credentials
# file would be found at `/secrets/prp-s3-credentials/credentials`.
# The secret-fetcher container is typically a dependency of other containers that need access to the secrets.
FROM bitnami/kubectl:latest

COPY download-secrets.sh /
COPY healthcheck.sh /

ENTRYPOINT ["/download-secrets.sh"]

FROM quay.io/oauth2-proxy/oauth2-proxy

# Copy the run script and the CA certificate into the Docker image
COPY run.sh /run.sh
COPY cilogon-basic.pem /tmp/
COPY cilogon-openid.pem /tmp/

# Switch to the root user
USER root

# Update the package list and install the ca-certificates and openssl packages
RUN apk update && apk add --no-cache ca-certificates openssl && \
    cat /tmp/cilogon-basic.pem >> /etc/ssl/certs/ca-certificates.crt && \
    cat /tmp/cilogon-openid.pem >> /etc/ssl/certs/ca-certificates.crt

ENTRYPOINT ["/bin/sh"]
CMD ["/run.sh"]

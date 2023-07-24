FROM emqx/emqx:latest

# Custom ACL file enables listening on all topics with topic string '#'
COPY acl.conf /opt/emqx/etc/acl.conf
COPY emqx.conf /opt/emqx/etc/emqx.conf

FROM jwilder/nginx-proxy:latest

# Create directory for vhost.d if it does not exist
RUN mkdir -p /etc/nginx/vhost.d

# Add custom configuration file
COPY vhost_location /etc/nginx/vhost.d/default_location
COPY static.conf /etc/nginx/conf.d/static.conf
COPY static_https.conf /app/static_https.conf

# Custom start script which creates a self-signed cert if one does not exist so nginx can start
COPY run.sh /app/run.sh
ENTRYPOINT ["/app/run.sh"]
CMD ["forego", "start", "-r"]

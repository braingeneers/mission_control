FROM jwilder/nginx-proxy:latest

# Create directory for vhost.d if it does not exist
RUN mkdir -p /etc/nginx/vhost.d

# Add custom configuration file
COPY vhost_location /etc/nginx/vhost.d/default_location

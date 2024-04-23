#
# Dockerfile for tinc
#

FROM alpine
#MAINTAINER kev <noreply@easypi.pro>

#FROM nginx

RUN apk add --no-cache iptables tinc nginx


RUN apk --update add --no-cache openssh bash \
  && sed -i s/#PermitRootLogin.*/PermitRootLogin\ yes/ /etc/ssh/sshd_config \
  && echo "root:root" | chpasswd \
  && rm -rf /var/cache/apk/* \
  && sed -ie 's/#Port 22/Port 22/g' /etc/ssh/sshd_config \
  && sed -ri 's/#HostKey \/etc\/ssh\/ssh_host_key/HostKey \/etc\/ssh\/ssh_host_key/g' /etc/ssh/sshd_config \
  && sed -ir 's/#HostKey \/etc\/ssh\/ssh_host_rsa_key/HostKey \/etc\/ssh\/ssh_host_rsa_key/g' /etc/ssh/sshd_config \
  && sed -ir 's/#HostKey \/etc\/ssh\/ssh_host_dsa_key/HostKey \/etc\/ssh\/ssh_host_dsa_key/g' /etc/ssh/sshd_config \
  && sed -ir 's/#HostKey \/etc\/ssh\/ssh_host_ecdsa_key/HostKey \/etc\/ssh\/ssh_host_ecdsa_key/g' /etc/ssh/sshd_config \
  && sed -ir 's/#HostKey \/etc\/ssh\/ssh_host_ed25519_key/HostKey \/etc\/ssh\/ssh_host_ed25519_key/g' /etc/ssh/sshd_config \
  && /usr/bin/ssh-keygen -A \
  && ssh-keygen -t rsa -b 4096 -f  /etc/ssh/ssh_host_key

#enable ssh
#CMD ["/usr/sbin/sshd","-d"]

COPY init.sh /init.sh
COPY docker-entrypoint.sh /entrypoint.sh
COPY peer.sh /usr/local/bin/peer.sh

#VOLUME /etc/tinc
#VOLUME $(pwd)/tinc

ENV NETNAME=netname \
    KEYSIZE=4096    \
    VERBOSE=2

# IP_ADDR=1.2.3.4       \
ENV IP_ADDR=128.114.198.51 \
    ADDRESS=10.20.30.1    \
    NETMASK=255.255.255.0 \
    NETWORK=10.20.30.0/24 \
    RUNMODE=server

EXPOSE 655/tcp 655/udp

ENTRYPOINT ["/entrypoint.sh"]

# These files were originally defined as volumes in the docker-compose.yml file
# The credentials were removed and accessible via secret-fetcher service
COPY picroscope-videostream/tinc/ /etc/tinc/
COPY picroscope-videostream/nginx-stuff/default.conf /etc/nginx/http.d/default.conf

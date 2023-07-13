# MQTT Service

The Braingeneers MQTT service is started and stopped via the `docker-compose.yaml` file in the root.

We have a custom MQTT image `braingeneers/mqtt:latest` which extends `emqx/emqx:latest` as seen in this Dockerfile.

Use the Makefile in the root to build and push our version of the image:

```bash
make mqtt-build  # build the image
make mqtt-push   # push the image to docker hub
make mqtt-shell  # open a shell in the image
```

The primary change to the base image is a change to the `auth.conf` file to allow
`#` MQTT topics.


## Debugging tips:

Use this command to print all MQTT messages to the console (linux based, should work in mac & WSL):

```bash
sudo apt-get install mosquitto-clients  # mac will be different

mosquitto_sub -h mqtt.braingeneers.gi.ucsc.edu -t "#" -v -u braingeneers -P <profile-key-from-credentials-file-mqtt-section>
```
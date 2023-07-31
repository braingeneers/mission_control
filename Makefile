# default target runs all build and push operations
all: build-braingeneers-image push-braingeneers-image build-h5repack push-h5repack build-nginx push-nginx build-oauth2 push-oauth2 build-mqtt push-mqtt build-slack-bridge push-slack-bridge build-secret-fetcher push-secret-fetcher build-job-launcher push-job-launcher

#
# Starts the full braingeneers stack of services, this is typically run
# on the braingeneers server, wherever that is hosted. These services include
# MQTT, website, listeners and other tools. This depends on docker-compose
# being installed.
#
start-services:
	docker compose pull; docker compose up -d

# Stops the full braingeneers stack of services.
stop-services:
	docker compose down

#
# Builds the braingeneers docker image
#
build-braingeneers-image:
	docker build -f braingeneers_docker_image/Dockerfile -t braingeneers/braingeneers:latest .

push-braingeneers-image:
	docker push braingeneers/braingeneers:latest

shell-braingeneers-image:
	docker run --rm -it braingeneers/braingeneers:latest bash

#
# job-h5repack
#
build-h5repack:
	docker build -f job-h5repack/Dockerfile -t braingeneers/job-h5repack:latest .

push-h5repack:
	docker push braingeneers/job-h5repack:latest

shell-h5repack:
	docker run --rm -it braingeneers/job-h5repack:latest bash

#
# nginx-proxy
#
build-nginx:
	docker build -f nginx-reverse-proxy/Dockerfile -t braingeneers/nginx-proxy:latest nginx-reverse-proxy

push-nginx:
	docker push braingeneers/nginx-proxy:latest

shell-nginx:
	docker run --rm -it --entrypoint bash braingeneers/nginx-proxy:latest

#
# oauth2-proxy
#
build-oauth2:
	docker build -f oauth2-proxy/Dockerfile -t braingeneers/oauth2-proxy:latest oauth2-proxy

push-oauth2:
	docker push braingeneers/oauth2-proxy:latest

shell-oauth2:
	docker run --rm -it braingeneers/oauth2-proxy:latest bash

#
# MQTT Service
#
build-mqtt:
	docker build -f mqtt/Dockerfile -t braingeneers/mqtt:latest mqtt

push-mqtt:
	docker push braingeneers/mqtt:latest

shell-mqtt:
	docker run --rm -it braingeneers/mqtt:latest bash

#
# Slack Bridge
#
build-slack-bridge:
	docker build -f slack-bridge/docker/Dockerfile -t braingeneers/service-slack-bridge:latest slack-bridge

push-slack-bridge:
	docker push braingeneers/service-slack-bridge:latest

shell-slack-bridge:
	docker run --rm -it braingeneers/service-slack-bridge:latest bash

#
# Secret Fetcher
#
build-secret-fetcher:
	docker build -f secret-fetcher/Dockerfile -t braingeneers/secret-fetcher:latest secret-fetcher

push-secret-fetcher:
	docker push braingeneers/secret-fetcher:latest

shell-secret-fetcher:
	docker run --rm -it braingeneers/secret-fetcher:latest bash

#
# job-launcher service listens to MQTT and launches NRP kubernetes jobs
#
build-job-launcher:
	docker build -f job-launcher/Dockerfile -t braingeneers/job-launcher:latest job-launcher

push-job-launcher:
	docker push braingeneers/job-launcher:latest

shell-job-launcher:
	docker run --rm -it --entrypoint bash braingeneers/job-launcher:latest

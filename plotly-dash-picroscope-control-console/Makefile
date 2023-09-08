CONTAINER = "braingeneers/piscope-console:latest"
RELEASE_CONTAINER ?= "braingeneers/piscope-console:v1.1"
NEXT_RELEASE_CONTAINER ?= "braingeneers/piscope-console:v1.2"


build:
	docker build -f Dockerfile -t $(CONTAINER) .

build-and-test:
	docker build -f Dockerfile -t $(CONTAINER) .
	docker run -v ~/.aws/credentials:/root/.aws/credentials:ro -v  $(PWD)/users.py:/console/users.py --rm -it -p 8056:8050 $(CONTAINER)

push:
	docker push $(CONTAINER)

echo:
	echo \
		CONTAINER=${CONTAINER} \
		RELEASE_CONTAINER=${RELEASE_CONTAINER}

shell:
	docker run -v ~/.aws/credentials:/root/.aws/credentials:ro -v  $(PWD)/users.py:/console/users.py --rm -it --entrypoint /bin/bash $(CONTAINER)

run:	   	# run locally
	docker run -v ~/.aws/credentials:/root/.aws/credentials:ro -v $(PWD)/users.py:/console/users.py --rm -it -p 8050:8050 $(CONTAINER)

run-prod:  	# run in production on gi server
	docker run -d -v ~/.aws/credentials:/root/.aws/credentials:ro -v $(PWD)/users.py:/console/users.py -p 127.0.0.1:8063:8050 $(CONTAINER)

run-test:   # run in parallel on production gi server on a different port (8056)
	docker run -d -v ~/.aws/credentials:/root/.aws/credentials:ro -v $(PWD)/users.py:/console/users.py -p 0.0.0.0:8056:8050 $(CONTAINER)


# Creates a versioned tag from :latest, uses the version number in $NEXT_RELEASE_CONTAINER defined above
# Also updates the default production tag to the latest (this tag is used to start the latest production container on boot)
release:
	docker tag $(CONTAINER) $(NEXT_RELEASE_CONTAINER) && \
	docker push $(NEXT_RELEASE_CONTAINER) && \
	docker tag $(NEXT_RELEASE_CONTAINER) "braingeneers/piscope-control:prod" && \
	docker push "braingeneers/piscope-console:prod"


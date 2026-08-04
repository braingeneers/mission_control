.DEFAULT_GOAL := help

IMAGE_DATE ?= $(shell date +%Y%m%d)
IMAGE_SHA ?= $(shell git rev-parse --short=12 HEAD)
SQL_DB_IMAGE ?= braingeneers/sql-db
SQL_DB_TAG ?= $(IMAGE_DATE)-$(IMAGE_SHA)

.PHONY: help test compose-validate service-proxy-test uploader-compose-test uploader-deployment-verifier-test workflows-compose-test verify-uploader-deployment sql-db-build sql-db-push sql-db-shell sql-db-test-backup

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make test' \
		'  make compose-validate' \
		'  make service-proxy-test' \
		'  make uploader-compose-test' \
		'  make uploader-deployment-verifier-test' \
		'  make workflows-compose-test' \
		'  make verify-uploader-deployment SERVICE=uploader|uploader-dev' \
		'  make sql-db-build' \
		'  make sql-db-push' \
		'  make sql-db-shell' \
		'  make sql-db-test-backup'

compose-validate:
	docker compose -f docker-compose.yaml config -q

test: compose-validate service-proxy-test uploader-compose-test uploader-deployment-verifier-test workflows-compose-test

service-proxy-test:
	./service-proxy/test-default-auth-config.sh

uploader-compose-test:
	./scripts/test-uploader-compose-contract.sh

uploader-deployment-verifier-test:
	./scripts/test-verify-uploader-deployment.sh

workflows-compose-test:
	./scripts/test-workflows-compose-contract.sh

verify-uploader-deployment:
	@test -n "$(SERVICE)" || { echo "SERVICE=uploader or SERVICE=uploader-dev is required" >&2; exit 2; }
	./scripts/verify-uploader-deployment.sh "$(SERVICE)"

sql-db-build:
	docker build -t $(SQL_DB_IMAGE):$(SQL_DB_TAG) -t $(SQL_DB_IMAGE):latest sql-db

sql-db-push: sql-db-build
	docker push $(SQL_DB_IMAGE):$(SQL_DB_TAG)
	docker push $(SQL_DB_IMAGE):latest

sql-db-shell:
	docker run --rm -it $(SQL_DB_IMAGE):$(SQL_DB_TAG) /bin/sh

sql-db-test-backup: sql-db-build
	./sql-db/test-sql-db.sh $(SQL_DB_IMAGE):$(SQL_DB_TAG)

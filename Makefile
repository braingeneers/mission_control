.DEFAULT_GOAL := help

IMAGE_DATE ?= $(shell date +%Y%m%d)
IMAGE_SHA ?= $(shell git rev-parse --short=12 HEAD)
SQL_DB_IMAGE ?= braingeneers/sql-db
SQL_DB_TAG ?= $(IMAGE_DATE)-$(IMAGE_SHA)

.PHONY: help compose-validate sql-db-build sql-db-push sql-db-shell sql-db-test-backup

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make compose-validate' \
		'  make sql-db-build' \
		'  make sql-db-push' \
		'  make sql-db-shell' \
		'  make sql-db-test-backup'

compose-validate:
	docker compose -f docker-compose.yaml config -q

sql-db-build:
	docker build -t $(SQL_DB_IMAGE):$(SQL_DB_TAG) -t $(SQL_DB_IMAGE):latest sql-db

sql-db-push: sql-db-build
	docker push $(SQL_DB_IMAGE):$(SQL_DB_TAG)
	docker push $(SQL_DB_IMAGE):latest

sql-db-shell:
	docker run --rm -it $(SQL_DB_IMAGE):$(SQL_DB_TAG) /bin/sh

sql-db-test-backup: sql-db-build
	./sql-db/test-sql-db.sh $(SQL_DB_IMAGE):$(SQL_DB_TAG)

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
	docker network create sql-db-test >/dev/null
	docker volume create sql-db-test-local >/dev/null
	docker volume create sql-db-test-replicated >/dev/null
	docker run -d --name sql-db-test --network sql-db-test \
		-e PGDATA=/local/sql-db/postgres/pgdata \
		-e POSTGRES_DB=services \
		-e POSTGRES_USER=services \
		-e POSTGRES_PASSWORD=services \
		-v sql-db-test-local:/local \
		-v sql-db-test-replicated:/replicated \
		$(SQL_DB_IMAGE):$(SQL_DB_TAG)
	docker run --rm --network sql-db-test -e PGPASSWORD=services postgres:16-alpine \
		sh -lc 'until pg_isready -h sql-db-test -U services -d services; do sleep 1; done'
	docker exec sql-db-test /usr/local/bin/backup-sql-db.sh
	docker exec sql-db-test /usr/local/bin/backup-sql-db.sh
	docker run --rm -v sql-db-test-replicated:/replicated postgres:16-alpine \
		sh -lc 'test "$$(find /replicated/sql-db/postgres -maxdepth 1 -type f | wc -l)" -eq 2'
	docker run --rm -v sql-db-test-replicated:/replicated postgres:16-alpine \
		sh -lc 'test "$$(find /replicated/sql-db/postgres -maxdepth 1 -type f -name "*.tmp" | wc -l)" -eq 0'
	docker run --rm -v sql-db-test-replicated:/replicated postgres:16-alpine \
		sh -lc 'test "$$(find /replicated/sql-db/postgres -maxdepth 1 -type f -name ".*" | wc -l)" -eq 0'
	docker run --rm -v sql-db-test-replicated:/replicated postgres:16-alpine \
		sh -lc 'pg_restore -l "$$(find /replicated/sql-db/postgres -name "*.dump" | head -n 1)" >/dev/null'
	docker container rm -f sql-db-test >/dev/null
	docker network rm sql-db-test >/dev/null
	docker volume rm sql-db-test-local sql-db-test-replicated >/dev/null

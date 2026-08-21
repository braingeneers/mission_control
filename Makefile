.DEFAULT_GOAL := help

IMAGE_DATE ?= $(shell date +%Y%m%d)
IMAGE_SHA ?= $(shell git rev-parse --short=12 HEAD)
SQL_DB_IMAGE ?= braingeneers/sql-db
SQL_DB_TAG ?= $(IMAGE_DATE)-$(IMAGE_SHA)
REPLICATED_VOLUME_BACKUP_IMAGE ?= braingeneers/replicated-volume-backup
REPLICATED_VOLUME_BACKUP_TAG ?= $(IMAGE_DATE)-$(IMAGE_SHA)
DATA_LIFECYCLE_IMAGE ?= braingeneers/data-lifecycle
DATA_LIFECYCLE_VERSION ?= $(shell cat data-lifecycle/VERSION)
DATA_LIFECYCLE_TAG ?= v$(DATA_LIFECYCLE_VERSION)
DATA_LIFECYCLE_STAGE4_POC_UPLOADER ?= smart-open
DATA_LIFECYCLE_STAGE4_POC_MULTIPART_UPLOAD ?= true
DATA_LIFECYCLE_STAGE4_POC_AWS_PROFILE ?= aws-braingeneers-backups
DATA_LIFECYCLE_STAGE4_POC_AWS_REGION ?= us-east-1
DATA_LIFECYCLE_STAGE4_POC_SOURCE_FILE ?= /tmp/HET3-6.raw.h5
DATA_LIFECYCLE_STAGE4_POC_DESTINATION_PREFIX ?= s3://braingeneers-backups-dev/stage4-debug/
DATA_LIFECYCLE_STAGE4_POC_PART_SIZE_MIB ?= 64
DATA_LIFECYCLE_STAGE4_POC_COPY_CHUNK_MIB ?= 64
DATA_LIFECYCLE_STAGE4_POC_RCLONE_USE_PRESIGNED_REQUEST ?= unset
DATA_LIFECYCLE_STAGE4_POC_RCLONE_USE_UNSIGNED_PAYLOAD ?= unset
DATA_LIFECYCLE_STAGE4_POC_RCLONE_DISABLE_CHECKSUM ?= false
DATA_LIFECYCLE_STAGE4_POC_RCLONE_CHUNK_SIZE_MIB ?= 0
DATA_LIFECYCLE_STAGE4_POC_RCLONE_UPLOAD_CONCURRENCY ?= 0
DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL ?= $(DATA_LIFECYCLE_STAGE4_POC_DESTINATION_PREFIX)$(notdir $(DATA_LIFECYCLE_STAGE4_POC_SOURCE_FILE))

.PHONY: help test compose-validate service-proxy-test notification-service-compose-test data-explorer-compose-test uploader-compose-test uploader-deployment-verifier-test workflows-compose-test replicated-volume-backup-compose-test verify-uploader-deployment sql-db-build sql-db-push sql-db-shell sql-db-test-backup replicated-volume-backup-build replicated-volume-backup-push replicated-volume-backup-shell replicated-volume-backup-test data-lifecycle-build data-lifecycle-test data-lifecycle-push data-lifecycle-shell data-lifecycle-run-local data-lifecycle-stage4-upload-repro

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make test' \
		'  make compose-validate' \
		'  make service-proxy-test' \
		'  make notification-service-compose-test' \
		'  make data-explorer-compose-test' \
		'  make uploader-compose-test' \
		'  make uploader-deployment-verifier-test' \
		'  make workflows-compose-test' \
		'  make replicated-volume-backup-compose-test' \
		'  make verify-uploader-deployment SERVICE=uploader|uploader-dev' \
		'  make sql-db-build' \
		'  make sql-db-push' \
		'  make sql-db-shell' \
		'  make sql-db-test-backup' \
		'  make replicated-volume-backup-build' \
		'  make replicated-volume-backup-push' \
		'  make replicated-volume-backup-shell' \
		'  make replicated-volume-backup-test' \
		'  make data-lifecycle-build' \
		'  make data-lifecycle-test' \
		'  make data-lifecycle-push' \
		'  make data-lifecycle-shell' \
		'  make data-lifecycle-run-local' \
		'  make data-lifecycle-stage4-upload-repro'

compose-validate:
	docker compose -f docker-compose.yaml config -q

test: compose-validate service-proxy-test notification-service-compose-test data-explorer-compose-test uploader-compose-test uploader-deployment-verifier-test workflows-compose-test replicated-volume-backup-compose-test

service-proxy-test:
	./service-proxy/test-default-auth-config.sh

notification-service-compose-test:
	./scripts/test-notification-service-compose-contract.sh

data-explorer-compose-test:
	./scripts/test-data-explorer-compose-contract.sh

uploader-compose-test:
	./scripts/test-uploader-compose-contract.sh

uploader-deployment-verifier-test:
	./scripts/test-verify-uploader-deployment.sh

workflows-compose-test:
	./scripts/test-workflows-compose-contract.sh

replicated-volume-backup-compose-test:
	./scripts/test-replicated-volume-backup-compose-contract.sh

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

replicated-volume-backup-build:
	docker build \
		-t $(REPLICATED_VOLUME_BACKUP_IMAGE):$(REPLICATED_VOLUME_BACKUP_TAG) \
		-t $(REPLICATED_VOLUME_BACKUP_IMAGE):latest \
		replicated-volume-backup

replicated-volume-backup-push: replicated-volume-backup-build
	docker push $(REPLICATED_VOLUME_BACKUP_IMAGE):$(REPLICATED_VOLUME_BACKUP_TAG)
	docker push $(REPLICATED_VOLUME_BACKUP_IMAGE):latest

replicated-volume-backup-shell:
	docker run --rm -it --entrypoint /bin/sh \
		$(REPLICATED_VOLUME_BACKUP_IMAGE):$(REPLICATED_VOLUME_BACKUP_TAG)

replicated-volume-backup-test: replicated-volume-backup-build
	./replicated-volume-backup/test-replicated-volume-backup.sh
	docker run --rm \
		$(REPLICATED_VOLUME_BACKUP_IMAGE):$(REPLICATED_VOLUME_BACKUP_TAG) validate
	docker run --rm \
		--tmpfs /local \
		--tmpfs /replicated \
		-e AWS_CLI=/bin/true \
		$(REPLICATED_VOLUME_BACKUP_IMAGE):$(REPLICATED_VOLUME_BACKUP_TAG) sync

data-lifecycle-build:
	@test -n "$(DATA_LIFECYCLE_VERSION)" || { echo 'data-lifecycle/VERSION is empty' >&2; exit 2; }
	docker build \
		-f data-lifecycle/docker/Dockerfile \
		-t $(DATA_LIFECYCLE_IMAGE):$(DATA_LIFECYCLE_TAG) \
		-t $(DATA_LIFECYCLE_IMAGE):latest \
		data-lifecycle

data-lifecycle-test: data-lifecycle-build
	docker run --rm \
		$(DATA_LIFECYCLE_IMAGE):$(DATA_LIFECYCLE_TAG) \
		python -m unittest \
			src.generate_puts_deletes_test \
			tests.test_generate_cleanup_report

data-lifecycle-push: data-lifecycle-build
	docker push $(DATA_LIFECYCLE_IMAGE):$(DATA_LIFECYCLE_TAG)
	docker push $(DATA_LIFECYCLE_IMAGE):latest

data-lifecycle-shell:
	docker run --rm -it \
		-v "$(HOME)/.config/rclone:/home/jovyan/.config/rclone:ro" \
		-v "$(HOME)/.aws:/home/jovyan/.aws:ro" \
		$(DATA_LIFECYCLE_IMAGE):$(DATA_LIFECYCLE_TAG) bash

data-lifecycle-run-local:
	docker run --rm -it \
		-v "$(HOME)/.config/rclone:/home/jovyan/.config/rclone:ro" \
		-v "$(HOME)/.aws:/home/jovyan/.aws:ro" \
		$(DATA_LIFECYCLE_IMAGE):$(DATA_LIFECYCLE_TAG) \
		src/run_data_lifecycle.sh

data-lifecycle-stage4-upload-repro: data-lifecycle-build
	@test -r "$(DATA_LIFECYCLE_STAGE4_POC_SOURCE_FILE)" || { echo "DATA_LIFECYCLE_STAGE4_POC_SOURCE_FILE is not readable: $(DATA_LIFECYCLE_STAGE4_POC_SOURCE_FILE)" >&2; exit 2; }
	@test -n "$(DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL)" || { echo 'DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL is empty' >&2; exit 2; }
	docker run --rm -t \
		-v /tmp:/tmp \
		-v "$(HOME)/.aws:/home/jovyan/.aws:ro" \
		$(DATA_LIFECYCLE_IMAGE):$(DATA_LIFECYCLE_TAG) \
		python src/stage4_upload_poc.py \
			--uploader "$(DATA_LIFECYCLE_STAGE4_POC_UPLOADER)" \
			--multipart-upload "$(DATA_LIFECYCLE_STAGE4_POC_MULTIPART_UPLOAD)" \
			--aws-profile "$(DATA_LIFECYCLE_STAGE4_POC_AWS_PROFILE)" \
			--aws-region "$(DATA_LIFECYCLE_STAGE4_POC_AWS_REGION)" \
			--part-size-mib "$(DATA_LIFECYCLE_STAGE4_POC_PART_SIZE_MIB)" \
			--copy-chunk-mib "$(DATA_LIFECYCLE_STAGE4_POC_COPY_CHUNK_MIB)" \
			--rclone-use-presigned-request "$(DATA_LIFECYCLE_STAGE4_POC_RCLONE_USE_PRESIGNED_REQUEST)" \
			--rclone-use-unsigned-payload "$(DATA_LIFECYCLE_STAGE4_POC_RCLONE_USE_UNSIGNED_PAYLOAD)" \
			--rclone-disable-checksum "$(DATA_LIFECYCLE_STAGE4_POC_RCLONE_DISABLE_CHECKSUM)" \
			--rclone-chunk-size-mib "$(DATA_LIFECYCLE_STAGE4_POC_RCLONE_CHUNK_SIZE_MIB)" \
			--rclone-upload-concurrency "$(DATA_LIFECYCLE_STAGE4_POC_RCLONE_UPLOAD_CONCURRENCY)" \
			--source-file "$(DATA_LIFECYCLE_STAGE4_POC_SOURCE_FILE)" \
			--destination-url "$(DATA_LIFECYCLE_STAGE4_POC_DESTINATION_URL)"

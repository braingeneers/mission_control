.DEFAULT_GOAL := help

.PHONY: help compose-validate

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make compose-validate'

compose-validate:
	docker compose -f docker-compose.yaml config -q

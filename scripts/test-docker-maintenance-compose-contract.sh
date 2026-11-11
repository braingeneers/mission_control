#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker compose -f "${repo_dir}/docker-compose.yaml" config --format json | python3 -c '
import json, re, sys
service = json.load(sys.stdin)["services"]["docker-maintenance"]
assert re.fullmatch(r"braingeneers/docker-maintenance:[0-9]{8}-[0-9a-f]{12}", service["image"])
assert service["container_name"] == "docker-maintenance"
assert service["restart"] == "unless-stopped"
assert not service.get("build")
assert not service.get("ports") and not service.get("expose")
assert not service.get("depends_on"), "No database, Workflows, or notification startup dependency"
assert set(service["networks"]) == {"braingeneers-net"}
assert service["environment"] == {"MAINTENANCE_SERVER": "braingeneers.gi.ucsc.edu",
                                 "MAINTENANCE_SLACK_CHANNEL_ID": "C08NSDULLR1"}
mounts = {item["target"]: item for item in service["volumes"]}
assert set(mounts) == {"/var/run/docker.sock", "/local"}, "No secret or application source mounts"
assert mounts["/var/run/docker.sock"]["source"] == "/var/run/docker.sock"
assert mounts["/var/run/docker.sock"]["read_only"]
assert not mounts["/var/run/docker.sock"]["bind"]["create_host_path"]
assert mounts["/local"]["source"] == "local"
assert mounts["/local"]["type"] == "volume"
assert service["logging"] == {"driver": "json-file", "options": {"max-size": "10m", "max-file": "3"}}
print("Docker maintenance Compose contracts are valid.")
'
# Health is owned by the image, with no Compose override disabling it.
rg -Fq '"healthcheck"' "${repo_dir}/docker-maintenance/Dockerfile"

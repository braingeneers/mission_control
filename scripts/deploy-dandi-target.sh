#!/usr/bin/env bash
# Operator-only: run on braingeneers.gi.ucsc.edu from this Mission Control checkout.
set -euo pipefail
cd "$(dirname "$0")/.."
base=(-f docker-compose.yaml)
transition=(-f docker-compose.yaml -f docs/dandi-target-transition.compose.yaml)

# Record the actual running image, rather than assuming the old Compose pin was deployed.
rollback_dir=$(mktemp -d /tmp/dandi-target-rollout.XXXXXX)
previous_explorer=$(docker inspect --format '{{.Config.Image}}' "$(docker compose "${base[@]}" ps -q data-explorer)")
printf 'services:\n  data-explorer:\n    image: %s\n' "$previous_explorer" > "$rollback_dir/data-explorer-before.compose.yaml"
docker inspect --format '{{.Name}} {{.Config.Image}} {{.Image}}' \
    "$(docker compose "${base[@]}" ps -q workflows-backend)" \
    "$(docker compose "${base[@]}" ps -q workflows)" \
    "$(docker compose "${base[@]}" ps -q data-explorer)" > "$rollback_dir/images-before.txt"
echo "Pre-rollout images and Data Explorer rollback override: $rollback_dir"

verify_images() {
    local layout=$1
    shift
    local -a files=("${base[@]}")
    if [[ "$layout" == transition ]]; then files=("${transition[@]}"); fi
    local config service expected container wanted observed
    config=$(docker compose "${files[@]}" config --format json)
    for service in "$@"; do
        expected=$(jq -r --arg service "$service" '.services[$service].image' <<<"$config")
        container=$(docker compose "${files[@]}" ps -q "$service")
        test -n "$container"
        wanted=$(docker image inspect --format '{{.Id}}' "$expected")
        observed=$(docker inspect --format '{{.Image}}' "$container")
        if [[ "$wanted" != "$observed" ]]; then
            echo "$service does not run the intended image $expected" >&2; exit 1
        fi
        echo "Verified $service: $expected"
    done
}

verify_catalog() {
    docker compose "${base[@]}" exec -T workflows-backend python - "$1" <<'PY'
import json, sys, urllib.error, urllib.request
phase = sys.argv[1]
base = 'http://127.0.0.1:8000'
def get(path):
    with urllib.request.urlopen(base + path, timeout=30) as response:
        return json.load(response)
catalog = {item['id']: item for item in get('/api/workflows')}
workflow = catalog['dandi-publication']
assert workflow['version'] == '0.5.12', 'Unexpected DANDI source version'
definition = get('/api/workflows/dandi-publication')['definition_json']
target = next(field for field in definition['form']['fields'] if field['name'] == 'target')
assert target['default'] == 'sandbox'
assert target['validation']['allowed_values'] == ['sandbox', 'production']
assert definition['nextflow']['params']['target'] == '{form.target}'
if phase == 'transition':
    assert 'dandi-publication-production' in catalog, 'Missing transition entry'
    legacy = get('/api/workflows/dandi-publication-production')['definition_json']
    assert legacy['nextflow']['params']['target'] == 'production'
else:
    assert 'dandi-publication-production' not in catalog, 'Production entry was not retired'
    for archived in ('false', 'true'):
        history = get('/api/runs?workflow_id=dandi-publication-production&archived=' + archived)
        for old in history[:1]:
            run = get('/api/runs/' + old['id'])
            assert run['workflow_name'] == old['workflow_name']
            assert run['workflow_version'] == old['workflow_version']
            try:
                request = urllib.request.Request(base + '/api/runs/' + old['id'] + '/clone', method='POST')
                with urllib.request.urlopen(request, timeout=30):
                    raise AssertionError('A retired workflow unexpectedly cloned')
            except urllib.error.HTTPError as exc:
                assert exc.code == 404
                assert json.load(exc)['error']['code'] == 'WORKFLOW_UNAVAILABLE'
            print('Verified historical run remains readable:', old['id'])
print('Verified DANDI catalog:', phase)
PY
}

verify_data_explorer() {
    docker compose "${base[@]}" exec -T data-explorer python - <<'PY'
import json, urllib.request
from data_explorer.config import Settings
from data_explorer.publication_environments import environment_settings
settings = Settings()
for target in ('sandbox', 'production'):
    chosen = environment_settings(settings, target)
    assert chosen.publication_workflow_id == 'dandi-publication'
    assert chosen.dandi_instance == target
    assert chosen.publication_manifest_prefix.endswith('/' + target + '/')
with urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=30) as response:
    health = json.load(response)
database = health['publication_database']
assert database['verified'] and database['migration_revision'] == '0005_general_dandi_collections'
print('Verified Data Explorer routing for both targets and unchanged database head')
PY
}

echo 'Stage 1: combined workflow with the temporary production entry'
docker compose "${transition[@]}" pull workflows-backend workflows
docker compose "${transition[@]}" up -d --no-deps --force-recreate --wait workflows-backend workflows
verify_images transition workflows-backend workflows
verify_catalog transition

echo 'Stage 2: Data Explorer sends the target to the combined workflow'
docker compose "${base[@]}" pull data-explorer
docker compose "${base[@]}" up -d --no-deps --force-recreate --wait data-explorer
verify_images final data-explorer
verify_data_explorer

echo 'Stage 3: retire the production-only entry'
docker compose "${base[@]}" pull workflows-backend workflows
docker compose "${base[@]}" up -d --no-deps --force-recreate --wait workflows-backend workflows
verify_images final workflows-backend workflows
verify_catalog final
docker compose "${base[@]}" ps workflows-backend workflows data-explorer
echo 'Service rollout verified. Check the hosted target selector and an archived run in your browser.'

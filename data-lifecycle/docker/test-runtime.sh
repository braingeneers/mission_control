#!/bin/bash
set -euo pipefail

test "$(id -u)" = "1000"
test "$(id -g)" = "100"
test "$(pwd)" = "/data_lifecycle"

for command_name in aws jq ps rclone yq; do
  command -v "${command_name}" >/dev/null
done

aws --version
rclone version
yq --version
jq --version
ps --version | head -n 1
rclone help flags | grep -F -- '--s3-list-url-encode' >/dev/null

python - <<'PY'
import importlib.util

import boto3
import matplotlib
import pandas
import smart_open
import yaml

assert importlib.util.find_spec("braingeneers") is None
print(
    "python dependencies:",
    f"boto3={boto3.__version__}",
    f"matplotlib={matplotlib.__version__}",
    f"pandas={pandas.__version__}",
    f"smart_open={smart_open.__version__}",
    f"pyyaml={yaml.__version__}",
)
PY

python -m py_compile src/*.py tests/*.py
bash -n src/*.sh

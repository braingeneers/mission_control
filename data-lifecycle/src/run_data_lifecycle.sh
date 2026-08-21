#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

usage() {
  cat <<'USAGE'
Usage: ./src/run_data_lifecycle.sh [options] [stage4 args...]

Options:
  --workers N           Set Stage 2 shard workers (alias for --stage2-workers)
  --stage2-workers N    Set Stage 2 shard workers (RCLONE_SHARD_JOBS)
  --stage4-workers N    Set Stage 4 upload workers (maps to stage4 --workers)
  -h, --help            Show this help and exit

Defaults:
  Stage 2 shard workers default to 8 unless RCLONE_SHARD_JOBS is already set.

All other arguments are forwarded to stage4_process_puts_deletes.py.
USAGE
}

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

DEFAULT_STAGE2_WORKERS=8
stage2_workers=""
stage4_workers=""
stage4_args=()

EXIT_STAGE0_FAILED=10
EXIT_STAGE1_FAILED=11
EXIT_STAGE2_FAILED=12
EXIT_STAGE3_FAILED=13
EXIT_STAGE4_FAILED=14
EXIT_SYNTAX_VALIDATION_FAILED=15

validate_bash_script() {
  local script_path="$1"

  if bash -n "${script_path}"; then
    return 0
  else
    local cmd_exit_code=$?
    echo "ERROR: Bash syntax validation failed for ${script_path} (exit ${cmd_exit_code})." >&2
    exit "${EXIT_SYNTAX_VALIDATION_FAILED}"
  fi
}

run_stage_command() {
  local stage_label="$1"
  local wrapper_exit_code="$2"
  shift 2

  if "$@"; then
    return 0
  else
    local cmd_exit_code=$?
    echo "ERROR: ${stage_label} failed with exit code ${cmd_exit_code}. Wrapper exiting with ${wrapper_exit_code}." >&2
    exit "${wrapper_exit_code}"
  fi
}

run_stage_source_script() {
  local stage_label="$1"
  local wrapper_exit_code="$2"
  local script_path="$3"

  if source "${script_path}"; then
    return 0
  else
    local cmd_exit_code=$?
    echo "ERROR: ${stage_label} failed with exit code ${cmd_exit_code}. Wrapper exiting with ${wrapper_exit_code}." >&2
    exit "${wrapper_exit_code}"
  fi
}

while (($#)); do
  case "$1" in
    --workers|--stage2-workers)
      if (($# < 2)); then
        echo "Error: $1 requires a value." >&2
        exit 1
      fi
      if ! is_positive_int "$2"; then
        echo "Error: $1 must be a positive integer." >&2
        exit 1
      fi
      stage2_workers="$2"
      shift 2
      ;;
    --workers=*|--stage2-workers=*)
      value="${1#*=}"
      if ! is_positive_int "$value"; then
        echo "Error: ${1%%=*} must be a positive integer." >&2
        exit 1
      fi
      stage2_workers="$value"
      shift
      ;;
    --stage4-workers)
      if (($# < 2)); then
        echo "Error: --stage4-workers requires a value." >&2
        exit 1
      fi
      if ! is_positive_int "$2"; then
        echo "Error: --stage4-workers must be a positive integer." >&2
        exit 1
      fi
      stage4_workers="$2"
      shift 2
      ;;
    --stage4-workers=*)
      value="${1#*=}"
      if ! is_positive_int "$value"; then
        echo "Error: --stage4-workers must be a positive integer." >&2
        exit 1
      fi
      stage4_workers="$value"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      stage4_args+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$stage2_workers" ]]; then
  export RCLONE_SHARD_JOBS="$stage2_workers"
elif [[ -z "${RCLONE_SHARD_JOBS:-}" ]]; then
  export RCLONE_SHARD_JOBS="$DEFAULT_STAGE2_WORKERS"
fi

if [[ -n "$stage4_workers" ]]; then
  stage4_args+=("--workers" "$stage4_workers")
fi

validate_bash_script stage0_prep_environment_vars.sh
validate_bash_script stage1_prep_inventory_files.sh
validate_bash_script stage2_generate_nrp_inventory.sh
validate_bash_script stage3_generate_puts_deletes.sh

run_stage_source_script "Stage 0 (environment setup)" "${EXIT_STAGE0_FAILED}" stage0_prep_environment_vars.sh
run_stage_command "Stage 1 (inventory prep)" "${EXIT_STAGE1_FAILED}" ./stage1_prep_inventory_files.sh
run_stage_command "Stage 2 (NRP inventory generation)" "${EXIT_STAGE2_FAILED}" ./stage2_generate_nrp_inventory.sh
run_stage_command "Stage 3 (puts/deletes generation)" "${EXIT_STAGE3_FAILED}" ./stage3_generate_puts_deletes.sh

echo ""
echo "#"
echo "# Stage 4: Process PUTS and upload to cold storage."
echo "#"
if python stage4_process_puts_deletes.py "${stage4_args[@]}"; then
  :
else
  stage4_exit_code=$?
  if (( stage4_exit_code >= 40 && stage4_exit_code <= 49 )); then
    echo "ERROR: Stage 4 failed with stage4-specific exit code ${stage4_exit_code}." >&2
    exit "${stage4_exit_code}"
  fi
  echo "ERROR: Stage 4 failed with exit code ${stage4_exit_code}. Wrapper exiting with ${EXIT_STAGE4_FAILED}." >&2
  exit "${EXIT_STAGE4_FAILED}"
fi

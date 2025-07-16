#!/usr/bin/env bash
set -e
set -o pipefail

source stage0_prep_environment_vars.sh
source stage1_prep_inventory_files.sh
source stage2_generate_nrp_inventory.sh
source stage3_generate_puts_deletes.sh
source stage4_process_puts_deletes.py


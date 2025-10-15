#!/usr/bin/env bash
set -e
set -o pipefail

source stage0_prep_environment_vars.sh
./stage1_prep_inventory_files.sh
./stage2_generate_nrp_inventory.sh
./stage3_generate_puts_deletes.sh
python stage4_process_puts_deletes.py


#!/usr/bin/env bash

#####################################################################################
## Stage 3:
## Run python script to generate PUTS and DELETES based on the two inventory files.
#####################################################################################

echo ""
echo "#"
echo "# Stage 3: Generate PUTS, DELETES, and NOTIFICATIONS."
echo "#"
python generate_puts_deletes.py \
  --config ./data-lifecycle.yaml \
  --prp-inventory ${LOCAL_SCRATCH_DIR}/local_inventory.csv \
  --aws-inventory ${LOCAL_SCRATCH_DIR}/glacier_inventory.csv \
  --puts-output ${LOCAL_SCRATCH_DIR}/puts.txt \
  --deletes-output ${LOCAL_SCRATCH_DIR}/deletes.txt \
  --notifications-output ${LOCAL_SCRATCH_DIR}/notifications.txt


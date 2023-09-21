# Data Lifecycle Management Documentation

This document provides an overview of the data lifecycle management scripts and configuration file used in the Braingeneers data lifecycle process. The process consists of three main components:

1. A Bash script (`run_data_lifecycle.sh`) that handles the main operations of copying files, generating inventory, and running the data lifecycle Python script.

2. A Python script (`generate_puts_deletes.py`) that generates lists of files to be PUT and DELETE based on the inventories of PRP/S3 and AWS/Glacier/S3.

3. A YAML configuration file (`data-lifecycle.yaml`) that holds various parameters and paths used in the process.

## run_data_lifecycle.sh

This Bash script is responsible for performing the data lifecycle process. It primarily does the following:

1. Copies configuration and AWS inventory files locally and to PRP/S3.

2. Generates a local inventory of files from PRP/S3 using `aws` command-line and copies the generated inventory file to PRP/S3.

3. Invokes `generate_puts_deletes.py` Python script to generate lists of files for PUT and DELETE operations based on the local and AWS inventories.

4. Processes PUT and DELETE operations using `awscli`.

## generate_puts_deletes.py

This Python script generates lists of files for PUT and DELETE operations based on the provided PRP/S3 and AWS/Glacier/S3 inventory files. The script:

1. Loads the configuration file and inventory files.

2. Applies last modified date updates based on the configuration.

3. Determines the expiration date for files based on the configuration.

4. Generates PUT and DELETE lists based on inventories and the expiration date.

5. Outputs the PUT and DELETE lists.

## data-lifecycle.yaml

This YAML file stores the configuration used in the data lifecycle management process. It includes:

1. AWS S3 Glacier configuration: Contains the AWS S3 Glacier bucket name and inventory file path.

2. Deletion parameters: Contains the length of time (in days) before files are deleted by default.

3. Backup parameters: Contains paths to include in the backup, directories for atomic operations, and paths for extending the delete date.

## Flowchart

The flow of the data lifecycle process is as follows:

```mermaid
graph LR
A[run_data_lifecycle.sh] --> B[Copy Config & Inventory Files]
B --> C[Generate PRP/S3 Inventory]
C --> D[Run generate_puts_deletes.py]
D --> E[Process PUTs & DELETEs]
```

1. `run_data_lifecycle.sh`: Initiates the process.

2. Copy Config & Inventory Files: Copies configuration and AWS inventory files both locally and to PRP/S3.

3. Generate PRP/S3 Inventory: Generates a local inventory of the files in PRP/S3 and copies the result back to PRP/S3.

4. Run `generate_puts_deletes.py`: The Python script is invoked to generate lists of files for PUT and DELETE operations based on the local and AWS inventories.

5. Process PUTs & DELETEs: The PUT and DELETE operations are processed using `awscli`.

Remember that any change in the base scripts or configuration file might affect the data lifecycle process, so they should be updated with caution.

This document provides a general understanding of how the data lifecycle management process is performed. For more specific information, please refer to the comments in the scripts and configuration file.
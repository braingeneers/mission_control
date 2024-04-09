## Nextflow Workflow Service

Runs nextflow workflows triggered from the "/workflow/start" MQTT topic.

### Running a Workflow

First, create or find a nextflow workflow on github.

If you're writing a nextflow workflow for the first time, a tutorial is here: https://www.nextflow.io/docs/latest/getstarted.html#your-first-script

The github URL for this workflow is the "url" param, for example:

    {"url": "https://github.com/DailyDreaming/k8-nextflow.git"}

Note: Infra has another readme with a more detailed credentials setup (one-time only), as this uses a special service account created especially to run nextflow.

### Instructions for running a toy nextflow workflow on the [NRP kubernetes cluster](https://portal.nrp-nautilus.io) (examples use the `braingeneers` namespace; this should be changed to the relevant namespace for your org in both the commands below and the contents of the yml files included).

### SETUP (note: this only needs to be done once and is here as a record)

### RUNNING A WORKFLOW

## Nextflow Workflow Service

Runs nextflow workflows triggered from the "workflow/start" MQTT topic.

### Running a Workflow

First, create or find a nextflow workflow on github.

If you're writing a nextflow workflow for the first time, a tutorial is here: https://www.nextflow.io/docs/latest/getstarted.html#your-first-script

The github URL for this workflow is the "url" param.  This can also include any additional params the workflow might need.  The following is an example of a worfklow at "url" with an input param "bucket_slash_uuid":

    {"url": "https://github.com/DailyDreaming/convert_to_nwb", "bucket_slash_uuid": "braingeneersdev/test"}

If this input is a file called example-params.json, we can trigger a workflow by publishing an MQTT topic of "workflow/start", for example:

    mosquitto_pub -h mqtt.braingeneers.gi.ucsc.edu -t "workflow/start" -u braingeneers -P $(awk '/profile-key/ {print $NF}' ~/.aws/credentials) -f example-params.json

Note: The infra/ dir has another readme with a more detailed credentials setup (one-time only), as this uses a special service account created especially to run nextflow.

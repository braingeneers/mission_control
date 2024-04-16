## Nextflow Workflow Service

Runs nextflow workflows triggered from the "workflow/start" MQTT topic.

### Running a Workflow

All workflows must be written in Nextflow and have their own github repository.

If you're writing a nextflow workflow for the first time, a tutorial is here: https://www.nextflow.io/docs/latest/getstarted.html#your-first-script

Working Examples:
 - https://github.com/DailyDreaming/k8-nextflow
   - Toy workflow for testing.
 - https://github.com/DailyDreaming/convert_to_nwb
   - Converts raw maxwell files to NWB format.

NOTE: Full s3:// paths need to be defined at the "workflow" level for workers to properly import input s3 files (currently).  Workers themselves do not currently inherit access to s3.

### Composing an MQTT message to trigger a workflow

Once you have a workflow, a JSON message can be published to the "workflow/start" MQTT topic whenever you wish to run it on the NRP/PRP.

The only required parameter in the JSON is the "url" key, which must be a link to a valid nextflow workflow github repository.

All other JSON parameters are workflow specific and are passed on to the nextflow workflow as arguments.  This can also include any additional params the workflow might need.  The following is an example of a worfklow at "url" with an input param "bucket_slash_uuid":

```json
{
    "url": "https://github.com/DailyDreaming/convert_to_nwb",
    "bucket_slash_uuid": "braingeneersdev/test"
}
```

If this input is a file called example-params.json, we can trigger a workflow by publishing an MQTT topic of "workflow/start", for example:

```bash
mosquitto_pub -h mqtt.braingeneers.gi.ucsc.edu \
              -t "workflow/start" \
              -u braingeneers \
              -P $(awk '/profile-key/ {print $NF}' ~/.aws/credentials) \
              -f example-params.json
```

### Checking Workflow Status

All workflow stdout/stderr is logged to its own file in the `/workflows` directory.

Find your workflow log file by title and timestamp:

```bash
lblauvel@braingeneers 12:35 PM ~$ ls /workflows

convert_to_nwb.2024-04-16_19-35-22.log
convert_to_nwb.2024-04-16_19-35-23.log
```

File contents should be connected via pipe, so reading the log file is a live update of the workflow's status.

```bash
lblauvel@braingeneers 12:35 PM ~$ cat /workflows/convert_to_nwb.2024-04-16_19-35-23.log

Job started: angry-bhaskara
Nextflow 24.03.0-edge is available - Please consider updating your version to it
N E X T F L O W  ~  version 23.11.0-edge
Launching `https://github.com/DailyDreaming/convert_to_nwb` [angry-bhaskara] DSL2 - revision: df125024929e2fc5458361954fea1cb1d1995cd9
Downloading plugin nf-amazon@2.2.0
[bd/aa6c5f] Submitted process > convert_to_nwb
/workspace/root/work/bd/aa6c5f6fecf9c02f36d5c39f86c4af/debug_0p20_1.raw.h5.nwb
Job running: angry-bhaskara ... waiting for job to stop running
Job angry-bhaskara has changed from running state [terminated:[exitCode:0, reason:Completed, startedAt:2024-04-16T19:35:53Z, finishedAt:2024-04-16T19:37:45Z, containerID:containerd://dd201d76b61b8dc2960ea17837402c64ab59be491bf81a303e0dbd79a0ddc402]]
```

### Other Resources

This is not likely to be used often, but this repository's `infra/` dir has another readme with a more detailed credentials setup for the service account that was created specifically for the nextflow run service (which needed to be set up one-time only).

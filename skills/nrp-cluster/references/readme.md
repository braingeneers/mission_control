# NRP Kubernetes pipeline template

The lab template downloads from S3, runs the pipeline inside a Linux/amd64
image, writes results to S3, and optionally logs metrics to W&B. See
[lab setup](nrp_setup.md) for data paths and credentials.

| File | Role |
|---|---|
| `Dockerfile`, `requirements.txt`, `.dockerignore` | Image, dependencies, and build context |
| `Makefile` | Optional build, push, and local container shortcuts |
| `run_job.sh`, `jobdefinition.yaml` | Job settings and manifest template |
| `run_pipeline_local.sh` | Container pipeline entry point |
| `download.py`, `upload.py`, `s3_utils.py` | Input and output transfer with retry and pagination |

Customize the pipeline, S3 paths, image, Job name (`<user>-<purpose>`), and
measured resource settings before following the [deploy workflow](../.agent/workflows/deploy-job.md).
For generic Kubernetes templates, use the upstream `nrp` and `kubernetes` skills.

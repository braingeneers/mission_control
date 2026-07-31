# NRP Kubernetes Template

> A reusable template for deploying compute pipelines on the [NRP Nautilus](https://nrp.ai/) Kubernetes cluster with S3 data storage and W&B observability.

## Quick Start

```bash
# 1. Build & push the Docker image
docker buildx build --platform=linux/amd64 -t hitpunch/nrp_template:latest .
docker push hitpunch/nrp_template:latest

# 2. Set credentials (one-time)
#    Store AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, WANDB_API_KEY
#    as environment variables (see NRP_SETUP.md for details)

# 3. Deploy a Kubernetes job
bash run_job.sh

# 4. Monitor
kubectl get pods
kubectl logs -f <pod-name>
```

## Using This Template (Git Submodule)

Add this repo as a subfolder in any project:

```bash
# Add the template as a submodule
git submodule add https://github.com/JohnMinnick/NRP_Template.git nrp/

# When cloning a project that uses this submodule
git clone --recurse-submodules <your-project-url>

# Update the template to latest version
git submodule update --remote nrp/
```

Customize these files for your pipeline:

| File | What to Change |
|---|---|
| `requirements.txt` | Add your Python dependencies |
| `download.py` | Point to your S3 input data |
| `upload.py` | Configure where output data goes |
| `run_pipeline_local.sh` | Your actual compute pipeline logic |
| `run_job.sh` | Job name, resource requests/limits |
| `Makefile` | Docker user/image names |

## Architecture

```
┌── LOCAL ─────────────────────────────────────────────┐
│  Source → Docker Build (linux/amd64) → Docker Hub    │
│  kubectl → submit Job via jobdefinition.yaml         │
└──────────────────────────────────────────────────────┘
         │                           │
┌── NRP NAUTILUS CLUSTER ────────────┼──────────────────┐
│  K8s Job (Pod)  ←── pulls image   │                  │
│    ├── download.py  ← S3 (Ceph)                     │
│    ├── run_pipeline_local.sh                         │
│    ├── upload.py    → S3 (Ceph)                      │
│    └── wandb.log()  → W&B cloud                     │
└──────────────────────────────────────────────────────┘
```

## Pipeline Flow

1. **Download** — `download.py` pulls input data from S3 (`braingeneersdev` bucket)
2. **Compute** — `run_pipeline_local.sh` runs your processing pipeline
3. **Upload** — `upload.py` pushes results back to S3
4. **Observe** — W&B logs metrics/artifacts to the cloud in real-time

## Repository Structure

```
├── Makefile                   # Docker build/push shortcuts
├── Dockerfile                 # Container image (Python 3.10-slim + deps)
├── requirements.txt           # Python dependencies (allensdk, boto3, wandb)
├── .dockerignore              # Excluded from Docker context
├── .env                       # Credentials (gitignored — never committed)
├── .gitignore                 # Blocks .env, *.secret, *.credentials
│
├── jobdefinition.yaml         # K8s Job template (envsubst variables)
├── run_job.sh                 # Sets env vars + submits job via kubectl
├── run_pipeline_local.sh      # Main pipeline script (runs inside container)
│
├── download.py                # S3 → local data download
├── upload.py                  # Local results → S3 upload
├── s3_utils.py                # S3 client with retry/backoff logic
├── scripts/                   # Utility scripts
│
├── NRP_SETUP.md               # Full infrastructure & policy reference
├── CLAUDE.md                  # Agent context for AI-assisted development
└── README.md                  # This file
```

## NRP Cluster Policies (Key Rules)

> ⚠️ **Read the full policies** in [NRP_SETUP.md](NRP_SETUP.md) and the [official NRP docs](https://nrp.ai/documentation/userdocs/start/policies/).

| Rule | Details |
|---|---|
| **No `sleep` in jobs** | Using `sleep infinity` in batch jobs **will get you banned** |
| **Resource limits** | Must be within 20% of requests |
| **GPU utilization** | Must be >40% or you get flagged |
| **A100 GPUs** | Require reservation at [nrp.ai/reservations](https://nrp.ai/reservations) |
| **No protected data** | No HIPAA, PII, FERPA, or FISMA data |
| **Workload purging** | Deployments purged after 2 weeks |

## Documentation

- **[NRP_SETUP.md](NRP_SETUP.md)** — Full setup guide: Docker, kubectl, S3, W&B, policies
- **[NRP Official Docs](https://nrp.ai/documentation/)** — Cluster access, tutorials, FAQ
- **[NRP Dashboard](https://dash.nrp-nautilus.io/)** — Cluster utilization monitoring

## Credentials

All secrets are stored in `.env` (gitignored) and as OS environment variables. **Never commit credentials.** See [NRP_SETUP.md](NRP_SETUP.md#credential-storage) for details.

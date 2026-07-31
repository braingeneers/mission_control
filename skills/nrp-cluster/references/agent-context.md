# CLAUDE.md

This file provides project context to AI coding agents (Claude Code, Antigravity, etc.) when working with this repository.

## Project Overview

Reusable pipeline template for cloud computing on the NRP Nautilus Kubernetes cluster. Designed to be pulled into other projects as a subfolder for S3 data storage, GPU compute, and W&B observability.

**Tech Stack:** Python 3.10, Docker, Kubernetes, AWS S3 (Ceph-backed), Weights & Biases

## Agent Workflows

| Slash Command | Description |
|---|---|
| `/build-push` | Build Docker image and push to Docker Hub |
| `/deploy-job` | Deploy a Kubernetes job to NRP (with pre-flight checks) |
| `/monitor-job` | Monitor running jobs — status, logs, troubleshooting |

## Common Commands

### Docker Build & Deployment
```bash
make build          # Build Docker image for linux/amd64
make push           # Push to Docker Hub
make go             # Build and push combined
make run            # Run container interactively
```

### Run Pipeline Locally (inside container)
```bash
bash run_pipeline_local.sh
```

### Submit Kubernetes Job
```bash
bash run_job.sh                                         # Full deployment
NAME=myrun envsubst < jobdefinition.yaml | kubectl apply -f -  # Manual
```

## Architecture

### Pipeline Flow
```
Download (S3) → Compute (run_pipeline_local.sh) → Upload (S3) → Log (W&B)
```

### Key Files
- `run_job.sh` — Sets env vars and deploys K8s job
- `jobdefinition.yaml` — K8s Job template (envsubst variables)
- `s3_utils.py` — S3 client with exponential backoff retry logic
- `download.py` / `upload.py` — S3 data transfer scripts
- `NRP_SETUP.md` — Full infrastructure & NRP policy reference

### Identity & Configuration
| Setting | Value |
|---|---|
| Docker Hub User | `hitpunch` |
| Image | `hitpunch/nrp_template:latest` |
| K8s Namespace | `braingeneers` |
| S3 Bucket | `braingeneersdev` |
| S3 Prefix | `jrm/` |
| S3 Endpoint (internal) | `http://rook-ceph-rgw-nautiluss3.rook` |
| S3 Endpoint (external) | `https://s3-west.nrp-nautilus.io` |
| Job Prefix | `jrm` |

### NRP Policy Quick Reference

**Critical rules — violating these can get accounts banned:**
- **No `sleep` in batch jobs** (use Jobs, not bare Pods)
- Resource **limits within 20%** of requests
- GPU utilization must be **>40%**
- No HIPAA/PII/FERPA data
- A100s require reservation at nrp.ai/reservations
- Max 400 concurrent jobs

See `NRP_SETUP.md` for complete policy documentation.

### Credentials & Secrets

All credentials stored in `.env` (gitignored) and as Windows user environment variables. **Never hardcode credentials.**

Required: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `WANDB_API_KEY`

### S3 Integration

The `s3_utils.py` module handles all S3 operations with:
- Adaptive retry mode (10 attempts max)
- Exponential backoff with jitter for SlowDown/transient errors
- Pagination for listing large directories
- Internal endpoint: `http://rook-ceph-rgw-nautiluss3.rook` (in-cluster, fast)
- External endpoint: `https://s3-west.nrp-nautilus.io` (local testing)

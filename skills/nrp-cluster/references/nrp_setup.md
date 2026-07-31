# NRP Kubernetes Setup & Deployment Guide

> **Last Updated:** 2026-02-20
> **Platform:** Windows 11 + WSL 2
> **Cluster:** NRP Nautilus (National Research Platform)

---

## Table of Contents

1. [Infrastructure Overview](#infrastructure-overview)
2. [Prerequisites & Installed Tools](#prerequisites--installed-tools)
3. [Docker Configuration](#docker-configuration)
4. [S3 Storage & Credentials](#s3-storage-ceph-backed)
5. [Weights & Biases](#weights--biases-wb)
6. [Kubernetes Configuration](#kubernetes-configuration)
7. [NRP Cluster Policies](#nrp-cluster-policies)
8. [GPU Configuration](#gpu-configuration)
9. [S3 Endpoints](#s3-endpoints)
10. [Monitoring & Dashboards](#monitoring--dashboards)
11. [Repository File Reference](#repository-file-reference)
12. [Deployment Workflow](#deployment-workflow)
13. [Useful Commands](#useful-commands)
14. [Troubleshooting](#troubleshooting)
15. [External References](#external-references)

---

## Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOCAL (Windows + WSL 2)                                            │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────────────────┐ │
│  │  Source Code  │────▶│ Docker Build │────▶│  Docker Hub (push)  │ │
│  │  + Makefile   │     │ linux/amd64  │     │  hitpunch/nrp_...   │ │
│  └──────────────┘     └──────────────┘     └─────────┬───────────┘ │
│                                                       │             │
│  ┌──────────────────────────────────────────┐         │             │
│  │  kubectl + kubelogin (OIDC auth)         │         │             │
│  │  → submits Job via jobdefinition.yaml    │─────────┼─────────┐  │
│  └──────────────────────────────────────────┘         │         │  │
└───────────────────────────────────────────────────────┼─────────┼──┘
                                                        │         │
┌───────────────────────────────────────────────────────┼─────────┼──┐
│  NRP NAUTILUS CLUSTER                                 │         │  │
│                                                       ▼         ▼  │
│  ┌─────────────────────────┐     ┌───────────────────────────┐    │
│  │  Kubernetes Job (Pod)   │◀────│  Pulls image from Docker  │    │
│  │  runs run_pipeline_     │     │  Hub at job start          │    │
│  │  local.sh inside        │     └───────────────────────────┘    │
│  └──────────┬──────────────┘                                      │
│             │                                                      │
│             ▼                                                      │
│  ┌─────────────────────────┐                                      │
│  │  S3 (Ceph-backed)       │                                      │
│  │  download.py / upload.py│                                      │
│  └─────────────────────────┘                                      │
└───────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites & Installed Tools

### Docker Desktop
- **Version:** Docker 29.2.1
- **Engine:** WSL 2 backend (linux)
- **Install:** [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- **Settings:** Ensure "Use WSL 2 based engine" is enabled
- **WSL Integration:** Enable for your distro in Settings → Resources → WSL Integration

### kubectl
- **Version:** v1.34.1
- **Location:** `C:\Program Files\Docker\Docker\resources\bin\kubectl.exe`
- **Source:** Bundled with Docker Desktop (no separate install needed)

### kubelogin (OIDC plugin)
- **Version:** v1.32.2
- **Location:** `C:\Users\97min\.kube\bin\kubectl-oidc_login.exe`
- **PATH entry:** `C:\Users\97min\.kube\bin` (added to user PATH permanently)
- **Source:** [github.com/int128/kubelogin](https://github.com/int128/kubelogin/releases)
- **Purpose:** Handles OIDC browser-based authentication to the NRP cluster
- **Install method:**
```powershell
# Download and extract
Invoke-WebRequest -Uri "https://github.com/int128/kubelogin/releases/download/v1.32.2/kubelogin_windows_amd64.zip" -OutFile "$env:TEMP\kubelogin.zip"
Expand-Archive -Path "$env:TEMP\kubelogin.zip" -DestinationPath "$env:TEMP\kubelogin" -Force

# Install to user-accessible location
New-Item -ItemType Directory -Force "$HOME\.kube\bin" | Out-Null
Copy-Item "$env:TEMP\kubelogin\kubelogin.exe" "$HOME\.kube\bin\kubectl-oidc_login.exe" -Force

# Add to PATH permanently
$kubeBin = "$HOME\.kube\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
[Environment]::SetEnvironmentVariable("Path", "$currentPath;$kubeBin", "User")
```

### make (NOT installed)
- PowerShell doesn't have `make` by default
- **Workaround:** Run docker commands directly, or install via `choco install make`
- All Makefile targets can be run manually (see [Useful Commands](#useful-commands))

---

## Docker Configuration

### Identity
| Variable | Value |
|---|---|
| Docker Hub User | `hitpunch` |
| Image Name | `hitpunch/nrp_template` |
| Tag | `latest` |
| Container Name | `nrp_template` |

### Dockerfile Summary
- **Base image:** `python:3.10-slim`
- **System deps:** git, build-essential, gfortran, pkg-config, libhdf5-dev, libcurl4-openssl-dev, libssl-dev, libxml2-dev
- **Python deps:** from `requirements.txt`
- **Workdir:** `/workspace`
- **Platform:** `linux/amd64` (required for NRP cluster nodes)

### .dockerignore
Excludes unnecessary files from the build context — check `.dockerignore` for specifics.

### S3 Storage (Ceph-backed)
| Setting | Value |
|---|---|
| Endpoint | `http://rook-ceph-rgw-nautiluss3.rook` |
| Bucket | `braingeneersdev` |
| Path Prefix | `jrm/` |

### Credential Storage
Credentials are stored in **three places** — none of them in git:

1. **`.env` file** (local, gitignored) — single source of truth for credentials
2. **Windows user environment variables** — set via `[Environment]::SetEnvironmentVariable()` for local use
3. **`run_job.sh`** — reads from env vars at deploy time, passes to Kubernetes pods

> **IMPORTANT:** The `.env` file is gitignored. Never commit credentials to the repo. If you need to share credentials, use a secure channel.

To reload credentials in a new terminal:
```powershell
# Credentials are already set as persistent user env vars
# They'll be available in any new terminal window automatically
echo $env:AWS_ACCESS_KEY_ID
```

### Weights & Biases (W&B)
- **Package:** `wandb` (added to `requirements.txt`)
- **API Key:** Stored in `.env` and Windows user env vars (never hardcoded in code)
- **Project:** Set per-repo (e.g. `SpikeProphecy`) — configure via `WANDB_PROJECT` env var
- **Pipeline integration:** `WANDB_API_KEY` is passed through `run_job.sh` → `jobdefinition.yaml` → pod env

To use W&B in your training scripts:
```python
import wandb
# wandb.login() is automatic when WANDB_API_KEY env var is set
wandb.init(project="your-project-name")
```

---

## Kubernetes Configuration

### Kubeconfig
- **File location:** `C:\Users\97min\.kube\config`
- **Context:** `nautilus`
- **Namespace:** `braingeneers`
- **Source:** Downloaded from [nrp.ai/config](https://nrp.ai/config)
- **Auth method:** OIDC via kubelogin (opens browser on first `kubectl` command)

### Setting Default Namespace
```powershell
kubectl config set-context --current --namespace=braingeneers
```
All subsequent `kubectl` commands will target `braingeneers` without needing `-n braingeneers`.

### Authentication Flow
1. Run any `kubectl` command (e.g., `kubectl get pods`)
2. kubelogin automatically opens a browser window
3. Authenticate with your NRP credentials
4. Token is cached locally — subsequent commands won't require re-auth (until token expires)

---

## NRP Cluster Policies

> **Source:** [nrp.ai/documentation/userdocs/start/policies/](https://nrp.ai/documentation/userdocs/start/policies/)

### Critical Rules

| Rule | Details | Consequence |
|---|---|---|
| **No `sleep` in batch jobs** | `sleep infinity` or scripts ending with `sleep` are banned | **Account banned** |
| **Resource limits ≈ requests** | Limits must be within 20% of requests | Pod killed or flagged |
| **GPU utilization >40%** | Check [GPU dashboard](https://grafana.nrp-nautilus.io/d/dRG9q0Ymz/k8s-compute-resources-namespace-gpus) | Violation flagged at [nrp.ai/userinfo](https://nrp.ai/userinfo) |
| **No protected data** | No HIPAA, PII, FERPA, or FISMA data on NRP | Policy violation |
| **Don't waste resources** | Consistently underutilized namespaces risk being banned | Namespace disabled |

### Resource Allocation Rules
- **Requests** = minimum guaranteed resources (used for scheduling)
- **Limits** = maximum allowed (pod killed if exceeded for memory, throttled for CPU)
- Aim for requests ≈ average usage, limits ≈ peak usage
- For >100 concurrent pods/jobs: **limits must equal requests**
- Use [monitoring](https://nrp.ai/documentation/userdocs/running/monitoring/) to fine-tune

### Batch Jobs (Kubernetes Jobs)
- Always use `Job` (not bare `Pod`) for compute workloads
- **Never** use `sleep infinity` — this will get you banned
- Don't submit more than 400 jobs at once
- Delete broken jobs immediately (they keep creating pods)
- Set `backoffLimit: 0` to prevent infinite retries on failure
- Set `restartPolicy: Never` for single-attempt runs

### Interactive Pods
- Destroyed after **6 hours** unless using a workload controller
- Limited to **2 GPUs, 32 GB RAM, 16 CPU cores**
- `sleep` is okay in interactive pods (but not in Jobs)

### GPU Policies
- Only request GPUs you can actually use (utilization must be >40%)
- Max **2 GPUs** per interactive pod, up to **8 per Job**
- **A100 GPUs** require a reservation: [nrp.ai/reservations](https://nrp.ai/reservations)
- For large jobs (>50 GPUs), present a plan in [Matrix chat](https://nrp.ai/contact)

### Data & Storage
- Purge unused data regularly — NRP is not archival storage
- Volumes unused for 6 months can be purged without notice
- Workloads (Deployments) are automatically deleted after 2 weeks

---

## GPU Configuration

### Requesting a GPU
Add to your `jobdefinition.yaml` resources section:
```yaml
resources:
  limits:
    nvidia.com/gpu: 1       # Number of GPUs (1-8 for Jobs)
  requests:
    nvidia.com/gpu: 1
```

### Choosing GPU Type (Node Affinity)
```yaml
# List available GPU types:
# kubectl get nodes -L nvidia.com/gpu.product

spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: nvidia.com/gpu.product
            operator: In
            values:
            - NVIDIA-A40            # or NVIDIA-GeForce-RTX-3090, etc.
```

### Requesting A100s (Special Resource)
```yaml
# A100s use a different resource name AND require a reservation
resources:
  limits:
    nvidia.com/a100: 1
  requests:
    nvidia.com/a100: 1
```
> Request access at [nrp.ai/reservations](https://nrp.ai/reservations)

### Shared Memory (shm)
Required for multi-worker data loading (e.g. PyTorch `num_workers > 0`):
```yaml
volumeMounts:
- mountPath: /dev/shm
  name: dshm
volumes:
- name: dshm
  emptyDir:
    medium: Memory
    sizeLimit: 2Gi    # Optional, defaults to half of memory request
```
> Without this, `/dev/shm` defaults to **64 MB**, which will crash PyTorch DataLoaders.

---

## S3 Endpoints

| Context | Endpoint | Protocol |
|---|---|---|
| **Inside cluster** (pods) | `http://rook-ceph-rgw-nautiluss3.rook` | HTTP |
| **Outside cluster** (local testing) | `https://s3-west.nrp-nautilus.io` | HTTPS |

> Use the internal endpoint in production for maximum throughput (bypasses load balancer). Use the external endpoint for local development and testing.

### S3 Regions
| Region | Internal | External |
|---|---|---|
| West | `http://rook-ceph-rgw-nautiluss3.rook` | `https://s3-west.nrp-nautilus.io` |
| Central | `http://rook-ceph-rgw-centrals3.rook-central` | `https://s3-central.nrp-nautilus.io` |
| East | `http://rook-ceph-rgw-easts3.rook-east` | `https://s3-east.nrp-nautilus.io` |

---

## Monitoring & Dashboards

- **[NRP Dashboard](https://dash.nrp-nautilus.io/)** — Overall cluster status
- **[GPU Dashboard](https://grafana.nrp-nautilus.io/d/dRG9q0Ymz/k8s-compute-resources-namespace-gpus)** — GPU utilization per namespace
- **[Violations](https://nrp.ai/userinfo)** — Check if your pods violate usage policies
- **[Cluster Map](https://traceroute.nrp-nautilus.io)** — Live cluster topology
- **[Resources](https://nrp.ai/viz/resources)** — Available GPU types and nodes

---

## Repository File Reference

| File | Purpose |
|---|---|
| `Makefile` | Docker build/push/run shortcuts. Defines `DOCKER_USER`, `IMAGE_NAME`, `TAG`, `CONTAINER_NAME` |
| `Dockerfile` | Container image definition — Python 3.10-slim + system libraries + pip deps |
| `requirements.txt` | Python package dependencies (allensdk, boto3, wandb) |
| `.dockerignore` | Files excluded from Docker build context |
| `.env` | **Gitignored** — stores S3 and W&B credentials locally |
| `jobdefinition.yaml` | Kubernetes Job template — uses `envsubst` for variable substitution from `run_job.sh` |
| `run_job.sh` | Job deployment script — sets all env vars (S3, W&B) and submits job via `kubectl apply` |
| `run_pipeline_local.sh` | Main pipeline orchestrator — runs inside the container |
| `download.py` | Downloads data from S3 (prefix: `jrm/`) |
| `upload.py` | Uploads results to S3 (prefix: `jrm/`) |
| `s3_utils.py` | S3 client with retry logic, exponential backoff, and pagination |
| `NRP_SETUP.md` | This document — full infrastructure & policy reference |
| `CLAUDE.md` | Agent context file for working with this repo |

---

## Deployment Workflow

### Step 1: Build the Docker Image
```powershell
# Using Makefile (requires make installed)
make build

# Or directly
docker buildx build --platform=linux/amd64 -t hitpunch/nrp_template:latest .
```

### Step 2: Push to Docker Hub
```powershell
# Login if not already
docker login

# Push
docker push hitpunch/nrp_template:latest

# Or build + push combined
make go
```

### Step 3: Configure run_job.sh
Edit `run_job.sh` to set:
- `NAME` — unique job identifier for this run
- `JOB_PREFIX` — prefix for Kubernetes job naming (currently `jrm`)
- Resource limits (memory, CPU, storage) as needed

> Credentials (`AWS_*`, `WANDB_API_KEY`) are read automatically from your environment variables — no need to edit them in the script.

### Step 4: Submit Kubernetes Job
```bash
# From WSL or a bash-capable terminal
bash run_job.sh
```

Or manually with envsubst:
```bash
NAME=myrun envsubst < jobdefinition.yaml | kubectl apply -f -
```

### Step 5: Monitor Job
```powershell
# List jobs
kubectl get jobs

# List pods
kubectl get pods

# Stream logs from a running pod
kubectl logs -f <pod-name>

# Describe job for debugging
kubectl describe job <job-name>
```

---

## Useful Commands

### Docker (PowerShell)
```powershell
# Build image
docker buildx build --platform=linux/amd64 -t hitpunch/nrp_template:latest .

# Run container interactively (for testing)
docker run --rm -it --name nrp_template hitpunch/nrp_template:latest

# Push to Docker Hub
docker push hitpunch/nrp_template:latest

# Clean up unused images/containers
docker system prune -f

# List local images
docker images | findstr nrp_template
```

### Kubernetes (PowerShell)
```powershell
# Check cluster connection
kubectl cluster-info

# List namespaces you have access to
kubectl get namespaces

# List running pods
kubectl get pods

# List jobs
kubectl get jobs

# Get pod logs
kubectl logs <pod-name>

# Stream pod logs in real time
kubectl logs -f <pod-name>

# Delete a job
kubectl delete job <job-name>

# Describe a pod (for debugging scheduling/pull issues)
kubectl describe pod <pod-name>

# Check current context
kubectl config current-context
```

### S3 Operations (inside container)
```bash
# Download data
python download.py

# Upload results
python upload.py
```

---

## Troubleshooting

### "make is not recognized"
PowerShell doesn't ship with `make`. Either:
- Run docker commands directly (see above)
- Install via: `choco install make`

### "kubectl: current-context is not set"
Kubeconfig is missing or misconfigured:
```powershell
# Re-download and install
Invoke-WebRequest -Uri "https://nrp.ai/config" -OutFile "$HOME\.kube\config"
kubectl config current-context  # Should output: nautilus
```

### Docker build fails with platform errors
Ensure you're building for the correct platform:
```powershell
docker buildx build --platform=linux/amd64 -t hitpunch/nrp_template:latest .
```

### OIDC authentication issues
If kubelogin fails to authenticate:
```powershell
# Verify plugin is accessible
& "$HOME\.kube\bin\kubectl-oidc_login.exe" --version

# Clear cached tokens and re-authenticate
Remove-Item "$HOME\.kube\cache" -Recurse -Force
kubectl get pods  # Will trigger fresh OIDC login
```

### Image pull errors in Kubernetes
If pods show `ImagePullBackOff`:
1. Ensure image was pushed: `docker push hitpunch/nrp_template:latest`
2. Ensure image name in `run_job.sh` matches exactly
3. Check if Docker Hub repo is public (NRP nodes need to pull without auth)

---

## External References

- **[NRP Documentation](https://nrp.ai/documentation/)** — Official NRP docs covering cluster access, namespaces, storage, GPU scheduling, and more.
- **[NRP Kubeconfig](https://nrp.ai/config)** — Download your kubeconfig file for cluster access
- **[kubelogin (OIDC plugin)](https://github.com/int128/kubelogin)** — GitHub repo for the kubectl OIDC authentication plugin
- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** — Docker for Windows with WSL 2 backend

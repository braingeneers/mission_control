---
description: Deploy a Kubernetes job to the NRP Nautilus cluster
---

# Deploy Job to NRP

## Pre-flight Checks

1. Verify the Docker image is up to date. Ask the user if they want to rebuild:
   - If yes, run the `/build-push` workflow first
   - If no, continue

2. Verify credentials are set:
```powershell
echo $env:AWS_ACCESS_KEY_ID
echo $env:WANDB_API_KEY
```
If either is missing, remind the user to set them (see NRP_SETUP.md).

3. Verify cluster connectivity:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl cluster-info 2>&1
```

## Configure the Job

4. Ask the user for:
   - **Job name** (the `NAME` variable in run_job.sh) — should be descriptive of this run
   - **Resource requirements** — memory, CPU, storage (defaults: 400Gi, 16 CPU, 400Gi)
   - **GPU needs** — if GPUs are needed, how many and what type

5. Update `run_job.sh` with the user's configuration.

6. If GPUs are requested, uncomment the GPU lines in `jobdefinition.yaml`.

## Deploy

7. Submit the job (requires WSL or bash):
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; bash run_job.sh 2>&1
```

If `bash` is not available, use envsubst manually:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; $env:NAME = "the-job-name"; kubectl apply -f (envsubst < jobdefinition.yaml) 2>&1
```

## Post-Deploy

8. Verify the job was created:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl get jobs -n braingeneers 2>&1
```

9. Check pod status:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl get pods -n braingeneers 2>&1
```

10. Report back with pod name and status. Offer to run `/monitor-job` to track progress.

## NRP Policy Reminders
- Resource limits must be within 20% of requests
- No `sleep infinity` in batch jobs (bannable offense)
- GPU utilization must be >40%
- A100s require a reservation at nrp.ai/reservations
- Max 400 concurrent jobs

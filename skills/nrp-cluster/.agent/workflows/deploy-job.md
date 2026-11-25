---
description: Deploy a Kubernetes job to the NRP Nautilus cluster
---

# Deploy Job to NRP

## Pre-flight Checks

1. Verify the Docker image is up to date. Ask the user if they want to rebuild:
   - If yes, run the `/build-push` workflow first
   - If no, continue

2. Check that credentials required by this Job are available without printing
   them. Use existing Kubernetes Secrets for credentials consumed by the pod
   (see [NRP setup](../../references/nrp_setup.md)).

3. Verify cluster connectivity:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl cluster-info 2>&1
```

## Configure the Job

4. Ask the user for:
   - **Job name** (the `NAME` variable in run_job.sh) — should be descriptive of this run
   - **Resource requirements** — memory, CPU, storage (defaults: 400Gi, 16 CPU, 400Gi)
   - **GPU needs** — if GPUs are needed, how many and what type

5. Export the variables required by `jobdefinition.yaml` using the intended values from `run_job.sh`.

6. If GPUs are requested, uncomment the GPU lines in `jobdefinition.yaml`.

## Deploy

7. Render and inspect the Job manifest. Use an image for code or pull a versioned
   bundle from S3 at startup. Put model weights, data, and large artifacts in S3
   or on a PVC (CephFS for shared access). If there is a legitimate small
   ConfigMap, check its rendered manifest too and verify its cleanup plan.
8. From Bash or WSL, run the [NRP preflight](https://nrp.ai/documentation/userdocs/ai/coding-agents/)
   and a server-side dry run on the exact manifest you will apply. Set
   `NRP_PREFLIGHT_SCRIPT` to the installed `nrp_preflight.py` path first.
   Inspect preflight and dry-run output and fix warnings before applying.

```bash
job_manifest=$(envsubst < jobdefinition.yaml)
python3 "${NRP_PREFLIGHT_SCRIPT:?Set the path to nrp_preflight.py}" <(printf '%s\n' "$job_manifest") &&
printf '%s\n' "$job_manifest" | kubectl --context=nautilus -n braingeneers apply --dry-run=server -f -
```

   Apply the same manifest after both checks pass.

```bash
printf '%s\n' "$job_manifest" | kubectl --context=nautilus -n braingeneers apply -f -
```

## Post-Deploy

9. Verify the job was created:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl get jobs -n braingeneers 2>&1
```

10. Check pod status:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl get pods -n braingeneers 2>&1
```

11. Report back with pod name and status. Offer to run `/monitor-job` to track progress.

## NRP Policy Reminders
- Resource limits must be within 20% of requests
- No `sleep infinity` in batch jobs (bannable offense)
- Run `kubectl apply --dry-run=server -f <manifest>` before the real apply; never `kubectl delete --force --grace-period=0`
- GPU utilization must be >40%
- A100s require a reservation at nrp.ai/reservations
- Max 400 concurrent jobs

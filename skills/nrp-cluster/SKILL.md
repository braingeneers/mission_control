---
name: nrp-cluster
description: Build, deploy, and monitor Kubernetes batch jobs on the NRP Nautilus cluster. Use this skill for pipeline execution workflows, S3/W&B setup checks, and job-level troubleshooting.
---

# NRP Cluster Management

Use this skill when working on compute pipelines that run as Kubernetes jobs on the NRP Nautilus cluster.

## Start Here

1. Read these required references before making recommendations:
   - `references/agent-context.md`
   - `references/readme.md`
   - `references/nrp_setup.md`
2. Confirm you have credentials/environment available for:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `WANDB_API_KEY` (optional for runs that use W&B)
   - `kubelogin` plugin and valid kubeconfig for NRP cluster access (PowerShell/WSL path differs by environment).
3. Confirm user intent:
   - Build/push image
   - Update job config
   - Deploy job
   - Monitor job state
   - Troubleshoot and cleanup
4. Choose a workflow before editing commands:
   - `/.agent/workflows/build-push.md` for image publishing.
   - `/.agent/workflows/deploy-job.md` for job creation and initial validation.
   - `/.agent/workflows/monitor-job.md` for pod/job monitoring and cleanup.
5. Treat all credentials as ephemeral environment values. Never request or print raw secret contents.

## What this skill covers

- Container image build and push with Linux/amd64 target for NRP.
- K8s Job submission using `envsubst` and a templated `jobdefinition.yaml`.
- Runtime-aware job policy checks (resource limits, GPU policy, sleep bans).
- Pod/job status checks, log retrieval, and failed-job cleanup.
- Template-level customization guidance (pipeline scripts, S3 prefixes, command entrypoint).

## Policy Reminders (high priority)

- No `sleep infinity` in batch jobs.
- Resource limits should track requests within policy boundaries.
- GPU utilization should stay above 40% on GPU jobs.
- Max concurrent jobs should not exceed 400.
- `backoffLimit` and `restartPolicy` policy choices should reflect single-attempt jobs.

## Reference Loading

Read only the files needed for your task:

- `references/nrp_setup.md` for platform setup, prerequisites, and troubleshooting.
- `references/readme.md` for the template architecture and quick start.
- `references/agent-context.md` for agent-specific command patterns.
- `/.agent/workflows/build-push.md` to build/publish.
- `/.agent/workflows/deploy-job.md` to submit jobs.
- `/.agent/workflows/monitor-job.md` to inspect and clean up jobs/pods.

## Workflow

### 1) Build and push image

If image freshness is unknown, run `turbo` workflow:

- `/.agent/workflows/build-push.md`

### 2) Configure job intent

Before submission, ask for or confirm:

- Job name (`NAME`)
- Job prefix (`JOB_PREFIX`)
- Resource requests and limits
- GPU count/type if required
- Optional run command override

### 3) Deploy

- Use `/.agent/workflows/deploy-job.md`.
- Verify image and credentials are available before submission.
- Confirm `kubectl` access and cluster context are valid.

### 4) Monitor and debug

- Use `/.agent/workflows/monitor-job.md`.
- Capture job/pod status and recent logs after submission.
- Delete finished/failed jobs when requested.

## Escalation

Escalate for issues that are clearly out-of-repo:

- Kubeconfig or OIDC token acquisition failures.
- NRP quota/policy enforcement questions.
- Persistent cluster scheduling failures unrelated to job YAML.
- Registry permission errors preventing image push.


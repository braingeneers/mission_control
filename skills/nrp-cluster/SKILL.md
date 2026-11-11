---
name: nrp-cluster
description: Build, deploy, and monitor Kubernetes batch jobs on the NRP Nautilus cluster. Use this skill for pipeline execution workflows, S3/W&B setup checks, jobs that call NRP-hosted open-weight LLMs or Brave Search through managed credentials, and job-level troubleshooting.
---

# NRP Cluster Management

Use this skill when working on compute pipelines that run as Kubernetes jobs on the NRP Nautilus cluster.

## Start Here

1. Read these required references before making recommendations:
   - `references/agent-context.md`
   - `references/readme.md`
   - `references/nrp_setup.md`
   - For a job that calls an NRP-hosted LLM, also read `references/hosted-llms.md` and verify the current official NRP documentation linked there.
   - For a job that calls Brave Search, also read `references/brave-search.md` and verify the current official API and pricing documentation linked there.
2. Confirm the credentials required by the workload are available without printing them:
   - `kubelogin` plugin and a valid kubeconfig for NRP cluster access (PowerShell/WSL path differs by environment).
   - `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` only when the job uses S3.
   - `WANDB_API_KEY` only when the run uses W&B.
   - The existing `nrp-llm-api-key/nrp_llm_api_key` Kubernetes Secret key only when the job calls the NRP-hosted LLM API.
   - The existing `brave-search-api/brave-search-api` Kubernetes Secret key only when the job calls the Brave Search API.
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
- OpenAI-compatible NRP-hosted LLM calls, model discovery, Kubernetes Secret injection, cache isolation, and retry/resume design.
- Brave Search calls, task-scoped Kubernetes Secret injection, and shared-quota request budgeting.

## Policy Reminders (high priority)

- No `sleep infinity` in batch jobs.
- Resource limits should track requests within policy boundaries.
- GPU utilization should stay above 40% on GPU jobs.
- Max concurrent jobs should not exceed 400.
- `backoffLimit` and `restartPolicy` policy choices should reflect single-attempt jobs.

## Resource sizing and utilization

The rules above, as numbers a monitor can check, are also in [references/utilization-policy.json](references/utilization-policy.json);
the two must agree:

- GPU utilization stays above 40% of the request on GPU jobs.
- Resource limits stay within 20% of requests.
- No more than 400 concurrent jobs.

A monitor (for example `nrp-util-check`, or the `nrp-monitor` skill built on it) reads that file and checks the GPU floor and the
job cap; the 20% limit rule is documented only; the monitor does not check it. Utilization is a
fraction of the pod's **request**, averaged over the last 10 minutes of NRP's own metrics.

A person or lab may add stricter rules in an optional local override that is never part of this repo (see the monitor's
`references/utilization.md`); a local file can add checks or lower these numbers, not loosen them.

## Reference Loading

Read only the files needed for your task:

- `references/nrp_setup.md` for platform setup, prerequisites, and troubleshooting.
- `references/readme.md` for the template architecture and quick start.
- `references/agent-context.md` for agent-specific command patterns.
- `references/hosted-llms.md` for jobs that call NRP-hosted open-weight models.
- `references/brave-search.md` for jobs and workflows that call Brave Search.
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
- NRP-hosted LLM model and request policy if the job calls the managed API; discover active model IDs instead of assuming a stale model name.
- An explicit per-run Brave request budget if the job calls Brave Search; include retries and pagination in the shared monthly usage estimate.

### 3) Deploy

- Use `/.agent/workflows/deploy-job.md`.
- Verify image and credentials are available before submission.
- Confirm `kubectl` access and cluster context are valid.
- For hosted LLM use, inject the existing API key with `secretKeyRef`; never retrieve its value into the submission command or request a GPU solely for remote inference.
- For Brave Search use, inject the existing API key only into calling tasks with `secretKeyRef`; never retrieve its value from the secrets repository into a submission command.

### 4) Monitor and debug

- Use `/.agent/workflows/monitor-job.md`.
- For approved work that will run unattended, register it with the `nrp-monitor` skill (when installed) instead of polling. A model never waits or polls: a script (Tier 0) tracks states, markers and utilization against these rules and applies fixed repairs; what it cannot classify goes to Tier 1 triage judge (the user's chosen runner; CLOSE or ESCALATE only), then a Tier 2 fixer (also chosen by the user), then Tier 3, a wake of the task's own coordinator chat in Claude Code, Codex or T3 (one wake per plan step, plus escalations). The owner is told only when that chat runs `task needs-owner`; a timeout never pages directly. `task add` needs an origin (the coordinator chat), and the registering agent writes this ladder into its handoff. `nrp-monitor setup` chooses the backend for each tier.
- Capture job/pod status and recent logs after submission.
- Delete finished/failed jobs when requested.

## Escalation

Escalate for issues that are clearly out-of-repo:

- Kubeconfig or OIDC token acquisition failures.
- NRP quota/policy enforcement questions.
- Persistent cluster scheduling failures unrelated to job YAML.
- Registry permission errors preventing image push.

## Smoke/profile sizing

The script never chooses or launches a full fan-out on its own after profiling. Register a few representative
smoke/profile jobs, including the largest/longest item. Mark stages `purpose: "smoke"` or `purpose: "profile"`
(boolean `smoke`/`profile` also accepted). Registration refuses Job `spec.parallelism` or `spec.completions`
above `smoke_max_jobs` in nrp-cluster's shared utilization-policy.json (default 3). Select inputs before registration;
the script cannot infer the largest input. After a successful profile, the Tier 2 fixer or coordinator chat decides
the full size within the plan's approved limits and explicitly registers it. Do not register speculative full fan-outs
behind profile stages.

## Memory LOW review

A utilization flag alone never fails or holds a healthy running task stage. For memory (20–150% of request), skip LOW review during ramp-up: 25% of measured stage runtime, or 30 minutes without history. Use whole-life per-pod Thanos peaks and recorded OOM limits: need is their maximum, right is ceil(need*1.25) Gi. A request <=1.2*right is sized correctly. Otherwise the fixer updates the manifest for retries/later runs; resubmit running work only when resumable and more than two measured hours remain. A max/median peak spread >3 with completed low pods below 20% throughout their lives calls for input size groups. The triage judge receives all numbers and returns CLOSE or ESCALATE; only the fixer changes anything. Missing peaks require review. Example: 12Gi request, peaks 4.5–7.7Gi, earlier OOM at 6Gi => need 7.7, right 10Gi, sized correctly; a 1.2Gi mean at 17 minutes is still ramp-up.

- `nrp-monitor` asks the coordinator after six hours unschedulable for GPU stages (`queue_wait_ceiling` overrides it); the Job stays queued, resume doubles the ceiling, and CPU fallback requires an explicit coordinator choice.

---
name: nrp-cluster
description: Build, deploy, and monitor Kubernetes batch jobs submitted directly to NRP Nautilus. Covers cluster setup, S3/W&B, hosted LLM and Brave Search credentials, and job-level troubleshooting. For hosted Workflows runs and Recipes, use workflow-authoring.
---

# NRP Cluster Management

Use this skill for compute pipelines submitted directly as Kubernetes jobs on
NRP Nautilus. For an existing Workflows run or Recipe, use `workflow-authoring`
and its bundled run waiter. Bring in this skill when the run investigation
needs cluster diagnostics. Nextflow owns submission and retries of its workers.

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

- **ConfigMaps and Secrets are not storage.** They live in the cluster's shared etcd, and a full etcd stops the whole
  cluster. A ConfigMap holds configuration of a few KB (settings, a short entrypoint script); a Secret holds credentials.
  Never put code bundles, archives (`.tgz`, `.zip`), source trees, data, notebooks, results, logs or checkpoints in either,
  and never base64-encode or split a file to fit. Code goes into the container image, or is shipped as a tarball to S3 and
  fetched when the Job starts (`nrp-task ship`, from the `nrp-monitor` skill; there is no `nrp-task configmap`). One
  ConfigMap per Job, run or fix (`code-fix1`, `code-fix2`) is the failure to avoid: update one object in place, and delete any
  ConfigMap you create when its Job finishes. Check the namespace total (see "ConfigMaps, Secrets and etcd" in
  `references/nrp_setup.md`). Why this is here: etcd filled up and took the cluster down on 2026-11-14, and on 2026-11-24 NRP
  blocked pod creation in `braingeneers` because agents had stored 590 ConfigMaps (140 MB, nearly all `code.tgz` tarballs, one per
  job or fix, never deleted) there.
- No `sleep infinity` in batch jobs (or any command that never ends, such as `tail -f /dev/null`).
- Every container sets CPU, memory and ephemeral-storage requests and limits; resource limits should track requests within policy boundaries.
- GPU utilization should stay above 40% on GPU jobs.
- Max concurrent jobs should not exceed 400. Do not flood the cluster with short pods: pack many small tasks into each pod of one Indexed Job with a `parallelism` cap, never loop `kubectl create job`, and keep pods running at once under the namespace's pod quota (many allow 200).
- `backoffLimit` and `restartPolicy` policy choices should reflect single-attempt jobs.
- Never `kubectl delete --force --grace-period=0`. A pod stuck `Terminating` goes to NRP support (https://nrp.ai/contact/).
- Move more than a couple of MB with S3 or `rclone`, not `kubectl cp` or `kubectl exec ... tar`: both go through the API server, whose link every user shares.
- Tolerations only by key and only for taints NRP approved for you (never `nautilus.io/system` or `nautilus.io/issue`); `priorityClassName` unset or `opportunistic`/`opportunistic2`; never set `CUDA_VISIBLE_DEVICES`. Admission rejects the rest.
- Before every apply, run `kubectl apply --dry-run=server -f <manifest>` and fix denials and `Warning:` lines. Never rephrase, split or change the verb of a rejected command to get past a check.
- Delete what you create for your own use (test pods, helper pods, scratch PVCs) when the work ends; compare `kubectl get pods,jobs,pvc,cm -n braingeneers` with what the task needs.

## NRP's own agent tooling

NRP publishes agent skills that teach an agent the cluster's rules, plus a preflight check that reads a manifest or `kubectl` command and reports what policy forbids without creating anything. Source: https://nrp.ai/documentation/userdocs/ai/coding-agents/ (page dated 2026-11-24); repository https://github.com/nrp-nautilus/sdsc-marketplace (plugin `nrp-nautilus`: skills `nrp`, `nrp-run`, `nrp-llm`, `kubernetes`; `skills/nrp/scripts/nrp_preflight.py`; in Claude Code it also runs as a hook before each `kubectl` command sent to the context named `nautilus`; set `NRP_PREFLIGHT_CONTEXTS` for another name). Not installed here, and NRP's `main` branch may still be 0.2.0 without the preflight (0.3.0 was on branch `nrp-nautilus-0.3.0` on 2026-11-24). Ask before installing; when it is installed, run the preflight on each manifest before `--dry-run=server`. NRP's machine-readable rules for any agent: https://nrp.ai/llms.txt. Read-only usage questions (top namespaces, per-namespace trends): NRP Accounting MCP server, `https://nrp-accounting-mcp.nrp-nautilus.io/` (details: https://nrp.ai/documentation/userdocs/ai/accounting-mcp/).

## Resource sizing and utilization

Before fan-out, measure cgroup true memory peaks on the expected heaviest inputs; see
Smoke/profile sizing below. Size memory as ceil(max(true peaks, recorded OOM limits) * 1.5) Gi.
Sampled metrics alone can miss transient loading spikes.

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

**If NRP refuses a submit** (admission webhook `job.nrp-nautilus.io`: "Your pods resources utilization is too
low", or a submit, patch or build Job that is denied or BLOCKED), stop and check utilization across the whole
namespace before retrying. Include pods you did not launch (Workflows/Flowforge `workflows-*` drivers, `nf-*`
task pods, other workstreams). Run `kubectl get pods` for every Running pod, then pass all their prefixes to
`nrp-util-check`; the account check only counts pods annotated with your username. Report each pod outside the
bands with its owner and usage. Fix or delete your own pods. Ask the owner before deleting anyone else's pods.
Never work around the webhook or retry in a loop. nrp-monitor treats this as an account RED ALERT: it holds every
task's submits until NRP's server-side dry-run accepts again, wakes the owners of the low pods, and alerts Hunter.
If woken, act now: resize (request = ceil(Thanos working-set peak x 1.5), limit within 20%) or delete your low pods,
and hand pods that are not yours to their real owner (`t3 thread send`); "no change" does not clear the alert.

## Reference Loading

Read only the files needed for your task:

- `references/nrp_setup.md` for platform setup, prerequisites, and troubleshooting; its "ConfigMaps, Secrets and etcd" section before any step that moves code or files into a Job.
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
- For approved direct jobs that will run unattended, register them with the
  `nrp-monitor` skill when installed. Follow that skill's instructions for
  verifying the scheduler, registering the coordinator chat, and recording
  the escalation path in the handoff.
- Capture job/pod status and recent logs after submission.
- Delete finished/failed jobs when requested.

## Escalation

Escalate for issues that are clearly out-of-repo:

- Kubeconfig or OIDC token acquisition failures.
- NRP quota/policy enforcement questions.
- Persistent cluster scheduling failures unrelated to job YAML.
- Registry permission errors preventing image push.

## Smoke/profile sizing

The script never chooses or launches a full fan-out on its own after profiling. Profile 2–3 items expected to be heaviest by input size, unit count or duration, using the real
configuration. Each profile must report its cgroup true memory peak with
[memory_peak.py](references/memory_peak.py). Size memory from the maximum
true peak (and any recorded OOM limit): ceil(need * 1.5) Gi. RSS is only a fallback diagnostic;
without a cgroup peak, investigate before fan-out. This 50% headroom rule also applies to later memory LOW review. Mark stages `purpose: "smoke"` or `purpose: "profile"`
(boolean `smoke`/`profile` also accepted). Registration refuses Job `spec.parallelism` or `spec.completions`
above `smoke_max_jobs` in nrp-cluster's shared utilization-policy.json (default 3). Select inputs before registration;
the script cannot infer the largest input. After a successful profile, the Tier 2 fixer or coordinator chat decides
the full size within the plan's approved limits and explicitly registers it. Do not register speculative full fan-outs
behind profile stages.

## Memory LOW review

A utilization flag alone never fails or holds a healthy running task stage. For memory (20–150% of request), skip LOW review during ramp-up: 25% of measured stage runtime, or 30 minutes without history (this is the review rule; nrp-monitor's action on an NRP-band flag waits at most 15 minutes, 10 without history). Prefer reported cgroup true peaks; also retain whole-life per-pod Thanos peaks and recorded OOM limits: need is their maximum, right is ceil(need*1.5) Gi. A request <=1.2*right is sized correctly. Otherwise the fixer updates the manifest for retries/later runs; resubmit running work only when resumable and more than two measured hours remain. A max/median peak spread >3 with completed low pods below 20% throughout their lives calls for input size groups. The triage judge receives all numbers and returns CLOSE or ESCALATE; only the fixer changes anything. Missing peaks require review. Example: 12Gi request, peaks 4.5–7.7Gi, earlier OOM at 6Gi => need 7.7, right 12Gi, sized correctly; a 1.2Gi mean at 17 minutes is still ramp-up.

- `nrp-monitor` asks the coordinator after six hours unschedulable for GPU stages (`queue_wait_ceiling` overrides it); the Job stays queued, resume doubles the ceiling, and CPU fallback requires an explicit coordinator choice.

### Reporting memory peaks

Copy `references/memory_peak.py` into the job image/code bundle and wrap the workload:
`python memory_peak.py --container CONTAINER --done-json LOCAL_MARKER -- COMMAND ...`.
Omit `--done-json` when there is no local JSON success marker. It updates an existing marker only
on success; upload that marker after the wrapper returns. Keep the `NRP_MEMORY_PEAK {...}` line
in stdout. `--container` must match the manifest container name; omit it only for single-container Jobs.
The helper reads cgroup v2 `memory.peak`, then v1 `memory.max_usage_in_bytes`, then child-process
`ru_maxrss` (explicitly marked as a fallback, not a true container peak; it excludes page cache).
Run it in a fresh job cgroup so the peak belongs to that run. An OOM can kill the wrapper before
it reports: no line is not evidence of low usage. The monitor reads saved log lines; markers are
for provenance, not an alternative success check. For multi-container Jobs report each container separately.
The 1.3x Tier 0 repair factor is a bounded recovery rule; deliberate profile/review sizing uses 1.5x.

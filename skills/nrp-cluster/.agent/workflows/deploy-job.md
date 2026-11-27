---
description: Render, validate, and submit a Braingeneers Kubernetes Job on Nautilus
---

# Deploy a Job to NRP

1. Verify connectivity with `kubectl --context=nautilus -n braingeneers cluster-info`.
2. Use the intended `<user>-<purpose>` name with your NRP username, a [pinned image](build-push.md),
   [measured resources](../../SKILL.md#smokeprofile-sizing), and the
   [lab rules](../../SKILL.md#stricter-lab-rules). Confirm required Secret keys
   exist without printing values. Set `activeDeadlineSeconds` from measured
   runtime with queue margin. Extend the existing Job's deadline if needed
   to retain its place in the queue.
3. From Bash, export the intended template variables, then render using the project's `run_job.sh` settings and
   `jobdefinition.yaml`. Pass only the template's non-secret variables to
   `envsubst`. For example, when the template uses `NAME` and `IMAGE`:

```bash
job_dir=$(mktemp -d) &&
  job_manifest="$job_dir/job.yaml" &&
  envsubst '${NAME} ${IMAGE}' < jobdefinition.yaml > "$job_manifest"
```

4. Inspect the file, then follow upstream `nrp-run` → Check, show, submit.
   Set `NRP_PREFLIGHT_SCRIPT` to the approved plugin’s
   `skills/nrp/scripts/nrp_preflight.py`. The example below uses the local
   marketplace checkout from the [plugin installation instructions](../../SKILL.md#nrps-own-agent-tooling).
   For a cached plugin or a different checkout, export the actual absolute
   script path first. An exported `NRP_PREFLIGHT_PATH` serves both this workflow
   and `nrp-monitor task add`. Preflight any legitimate small ConfigMap too and verify
   its cleanup path. Repeat validation on the final render after any change.

```bash
local_preflight="$HOME/.local/share/nrp-nautilus/sdsc-marketplace/plugins/nrp-nautilus/skills/nrp/scripts/nrp_preflight.py"
NRP_PREFLIGHT_SCRIPT="${NRP_PREFLIGHT_SCRIPT:-${NRP_PREFLIGHT_PATH:-$local_preflight}}"
if [[ -n "${NRP_PREFLIGHT_SCRIPT:-}" && -r "$NRP_PREFLIGHT_SCRIPT" ]]; then
  python3 "$NRP_PREFLIGHT_SCRIPT" "$job_manifest"
else
  printf '%s\n' "NRP preflight skipped: script unavailable" >&2
fi &&
  kubectl --context=nautilus -n braingeneers apply --dry-run=server -f "$job_manifest"
```

5. Fix blocks, denials, and warnings. Show the manifest and its pod count,
   requests, GPUs, and deadline. Apply the same file after approval:

```bash
kubectl --context=nautilus -n braingeneers apply -f "$job_manifest"
kubectl --context=nautilus -n braingeneers get job "$NAME"
kubectl --context=nautilus -n braingeneers get pods -l "job-name=$NAME"
```

6. Report Job and pod status. Use [Monitor Job](monitor-job.md) for inspection
   and [nrp-monitor](../../../nrp-monitor/SKILL.md) for unattended work.

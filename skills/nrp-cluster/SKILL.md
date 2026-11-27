---
name: nrp-cluster
description: Braingeneers setup, stricter lab rules, and troubleshooting for Kubernetes Jobs submitted directly to NRP Nautilus. Covers S3, pinned images, W&B, and lab LLM and Brave Search credentials. Use workflow-authoring for hosted Workflows runs.
---

Load NRP's `nrp-nautilus` plugin skills first (`nrp`, `nrp-run`, `kubernetes`); this skill adds Braingeneers setup and stricter lab rules.

## NRP's own agent tooling

Ask before installing. As of 2026-11-25, the default marketplace branch has
0.2.0. The reviewed 0.3.0 commit is `98bc617` on `nrp-nautilus-0.3.0`.
[Claude Code v2.1.324+ accepts a full commit SHA as the marketplace ref](https://code.claude.com/docs/en/plugins/marketplace-reference#fields-by-type).

```bash
claude plugin marketplace add 'nrp-nautilus/sdsc-marketplace#98bc6170d1b38b0d7f318b0d4a9cbe589a9d00a9'
claude plugin install nrp-nautilus@sdsc-marketplace
```

For older Claude Code versions, register a local checkout at the same commit:

```bash
marketplace_dir="$HOME/.local/share/nrp-nautilus/sdsc-marketplace"
mkdir -p "$(dirname "$marketplace_dir")" &&
  git clone --branch nrp-nautilus-0.3.0 https://github.com/nrp-nautilus/sdsc-marketplace.git "$marketplace_dir" &&
  git -C "$marketplace_dir" checkout --detach 98bc6170d1b38b0d7f318b0d4a9cbe589a9d00a9 &&
  claude plugin marketplace add "$marketplace_dir" &&
  claude plugin install nrp-nautilus@sdsc-marketplace
```

If `sdsc-marketplace` is already registered from another source, review its
installed plugins before replacing the registration. Removing a marketplace
also uninstalls its plugins.

The Mission Control maintainer owns the pin. Once 0.3.0 is merged into
upstream `main` and verified there, remove the pinned or local registration
and reinstall from `main`:

```bash
claude plugin marketplace remove sdsc-marketplace &&
  claude plugin marketplace add 'nrp-nautilus/sdsc-marketplace#main' &&
  claude plugin install nrp-nautilus@sdsc-marketplace
```

The [NRP coding-agent guide](https://nrp.ai/documentation/userdocs/ai/coding-agents/)
gives these Codex commands for the default marketplace:

```bash
codex plugin marketplace add nrp-nautilus/sdsc-marketplace
codex plugin add nrp-nautilus@sdsc-marketplace
```

Codex and other agents without the plugin, including hosts on 0.2.0 without the
needed skills, read the [2026-11-25 fallback digest](references/nrp_rules_digest.md).
NRP's plugin and [llms.txt](https://nrp.ai/llms.txt) govern cluster rules. Apply
the stricter rule where sources differ and flag discrepancies to the Mission Control maintainer.

Use `nrp` → Hard rules, Access, Usage policies, GPUs, and Storage for cluster
policy and setup. Use `nrp-run` → Check, show, submit for preflight and approval,
and its watch and cleanup sections for routine operations. Use `kubernetes`
for generic manifests and `nrp-llm` for managed inference.

## Braingeneers setup

Use context `nautilus` and namespace `braingeneers` explicitly. Start Job names
with the submitting person’s NRP username, using `<user>-<purpose>` (for example,
`alex-sortbench`). Select an authorized S3 prefix for the workstream.

- [Lab setup](references/nrp_setup.md) gives S3 endpoints, W&B setup, and ConfigMap cleanup.
- [Template layout](references/readme.md) and [agent commands](references/agent-context.md) cover `run_job.sh` and `jobdefinition.yaml`.
- [Build and push](.agent/workflows/build-push.md) publishes a Linux/amd64 image pinned by tag and digest.
- [Deploy](.agent/workflows/deploy-job.md) covers manifest review and namespace-specific checks.
- [Monitor](.agent/workflows/monitor-job.md) covers status, logs, and lab troubleshooting.
- [Hosted LLMs](references/hosted-llms.md) and [Brave Search](references/brave-search.md) cover the lab's Secret contracts and request budgeting.

For hosted Workflows and Recipes, use `workflow-authoring` and its run waiter.
Nextflow owns the submission and retries of its workers. Subagents that touch
NRP load both layers, use Jobs for batch work, and audit their Jobs at handoff.

## Stricter lab rules

- **One attempt per Job.** Use `backoffLimit: 0` and `restartPolicy: Never`. Omit per-index retries when adapting sweep templates. The upstream retries can hide the original failure and duplicate the monitor's bounded recovery.
- **Set ephemeral-storage requests and limits on every container**, including init containers. This accounts for scratch before eviction and follows `llms.txt` even below the plugin's 50 GiB guidance.
- **Use S3 for Job code bundles and bulk data.** Keep runnable code in a pinned image, use a pinned Git revision in an init container, or fetch a versioned, checksum-verified S3 tarball at startup. The S3 tarball is a lab build artifact: provenance lives in git (the monitor pushes and tags the exact commit), and the bundle is only transport. NRP's docs prefer git or an image; the bundle is a lab exception that breaks no NRP rule and avoids per-pod clones and repo tokens. Keep code and data out of ConfigMaps and Secrets because they fill shared etcd. Authenticated lab users are trusted. Store bundles, including those from private repos, in `braingeneerscache`, the S3 bucket Workflows also uses.
- **Transfer bulk data via S3 from inside the cluster.** Above a couple of MB use S3 or `rclone`. The plugin's `kubectl cp` guidance applies only to PVCs. The lab moves data through S3 and does not normally use PVCs.
- **Inject credentials only through `secretKeyRef` to existing lab Secrets.** Job manifests are visible to other users. Keep secret values out of `envsubst` and logs. The plugin's user-created LLM Secret is replaced here by the operator-owned lab Secret.
- **Give per-Job settings a cleanup path.** Use a Job owner reference or explicit cleanup for a few KB of settings, then verify removal after completion, cancellation, or launch failure. Shared etcd filled on 2026-11-14. On 2026-11-24, 590 per-Job or per-fix ConfigMaps blocked pod creation. See [ConfigMaps, Secrets and etcd](references/nrp_setup.md#configmaps-secrets-and-etcd).
- **Use explicit Job TTL and persist required logs.** The cluster defaults to a one-day TTL, which can remove logs before the monitor or coordinator reviews them. Clean up your failed Jobs, test pods, helper pods, scratch PVCs, and per-Job settings when done. Leave other owners’ resources to them.

Run `nrp_preflight.py` explicitly on the rendered manifest in Codex and for
Python submitters. The Claude Bash hook returns quickly and silently for
unrelated commands. It misses variable paths such as `kubectl apply -f "$var"`,
piped manifests, wrapped commands such as `env`, `timeout`, and `bash -c`, and
submissions through `nrp-task`, `nrp-monitor`, or the launchd monitor.
`nrp-monitor task add` runs its own preflight on registered manifests when
the script is available. For a local plugin checkout, export its script path
as `NRP_PREFLIGHT_PATH` for the monitor. Leave `NRP_PREFLIGHT_ALLOW` unset.
If the script is unavailable, report the gap and always use server-side dry-run. Follow [Deploy](.agent/workflows/deploy-job.md)
for script setup and the check order.

## Resource sizing and utilization

Before fan-out, smoke test the code and profile full-size heavy inputs. Size
memory as `ceil(max(true peaks, recorded OOM limits) * 1.5)` GiB. Sampled metrics
can miss transient loading spikes. See [Smoke/profile sizing](#smokeprofile-sizing).

NRP uses GPU above 40%, CPU 20–200%, and memory 20–150% of the request.

**GPU Jobs are designed for the floor before they are submitted, not fixed after.** Target at least 60% GPU so normal variation
never drops under 40%. A GPU pod only runs GPU work: S3 staging, decoding, preprocessing and writing go to a prior CPU stage or to
parallel prefetch workers that keep the GPU fed; batch many items per GPU call or run several items concurrently per pod. Estimate
the duty cycle (GPU seconds / wall seconds per item) from a profile, and make the smoke stage log both and its GPU %; do not fan out
a GPU Job whose smoke ran under 40%. A Job that drops under the floor is stopped and redesigned, never left to finish.

See `nrp` → `references/policies.md` → Utilization thresholds for RSS, the
small-pod exemption, and the allowance of four pods outside the bands.
The [shared monitor policy](references/utilization-policy.json) supplies the
NRP bands and the other numeric settings used by `nrp-util-check`. Verify
effective settings and any local overrides with `nrp-util-check --policy`
and consult the [monitor utilization reference](../nrp-monitor/references/utilization.md).
The monitor uses ten-minute averages when reporting utilization. For namespace
trends, see the [NRP Accounting MCP](https://nrp.ai/documentation/userdocs/ai/accounting-mcp/).

**If NRP refuses a submit** (admission webhook `job.nrp-nautilus.io`: "Your pods resources utilization is too
low", or a submit, patch or build Job that is denied or BLOCKED), stop and check utilization across the whole
namespace before retrying. Include pods you did not launch (Workflows/Flowforge `workflows-*` drivers, `nf-*`
task pods, other workstreams). Run `kubectl get pods` for every Running pod, then pass all their prefixes to
`nrp-util-check`; the account check only counts pods annotated with your username. Report each pod outside the
bands with its owner and usage. Fix or delete your own pods. Never modify or delete another user’s pods.
Never work around the webhook or retry in a loop. nrp-monitor treats this as an account RED ALERT: it holds every
task's submits until NRP's server-side dry-run accepts again, wakes the owners of the low pods, and alerts the account owner.
Running pods cannot be resized in place. Delete your low Jobs and resubmit at the measured size after admission clears. For deliberate memory resizing, include the whole-life working-set peak in measured need.
Route other Jobs to their owners through the owning coordinator chat.

Patterns that have cost runs (2026-11):
- Jobs that stage inputs from S3 or write large scratch caches can sit at 5-30% of a core for 30-60 min before compute
  starts. Low utilization in that phase is expected; shorten it (parallel reads, smaller staged spans) or account for it
  in monitoring rather than resizing the pod.
- Page cache inflates working set and memory peaks. Before raising memory, compare with process RSS and check for an
  actual OOM kill. When a real OOM comes from transient copies (full-length array slices, unflushed memory maps), fixing
  the spike usually beats a larger request, which also lowers measured utilization.
- Pin hardware by node labels (for example `feature.node.kubernetes.io/cpu-model.*`), not `kubernetes.io/hostname`.
  A hostname pin leaves the Job Pending indefinitely if that node is cordoned, faulty or excluded.
- Never relax an exact reproducibility or parity check to get a run through. A deterministic mismatch on several nodes
  points at the code path (read path, dtype, layout), not the hardware; diagnose which step changes the values.

## Unattended Jobs

Use [nrp-monitor](../nrp-monitor/SKILL.md) for registration, the scheduler,
coordinator chat, and an escalation path. Verify that completion can resume
pending review and delivery before handing back. For registered Jobs shipping
code from S3, follow [Shipping code](../nrp-monitor/references/tasks.md#shipping-code).

Escalate out-of-repo access, quotas, persistent scheduling, and registry
permissions to the relevant operator or [NRP Support](https://nrp.ai/contact/).

## Smoke/profile sizing

Profile 2–3 of the heaviest inputs at full size with the real configuration and process count.
Measure past startup and cache warm-up. A reduced-process smoke run checks basic operation.
Use [monitor registration guidance](../nrp-monitor/references/tasks.md#smokeprofile-sizing) for smoke and profile stages,
and [utilization review](../nrp-monitor/references/utilization.md) for memory LOW and other flags.

### Reporting memory peaks

Copy `references/memory_peak.py` into the job image/code bundle and wrap the workload:
`python memory_peak.py --container CONTAINER --done-json LOCAL_MARKER -- COMMAND ...`.
Omit `--done-json` when there is no local JSON success marker. It updates an existing marker only
on success; upload that marker after the wrapper returns. Keep the `NRP_MEMORY_PEAK {...}` line
in stdout. `--container` must match the manifest container name; omit it only for single-container Jobs.
The helper reads cgroup v2 `memory.peak`, then v1 `memory.max_usage_in_bytes`, then child-process
`ru_maxrss` (explicitly marked as a fallback, not a true container peak; it excludes page cache).
For cache-heavy pods, including large `emptyDir` staging, measure the peak container working
set (`container_memory_working_set_bytes`) through the real workload. Use it as a sizing input
alongside the cgroup peak because process RSS misses charged page cache.
Run it in a fresh job cgroup so the peak belongs to that run. An OOM can kill the wrapper before
it reports: no line is not evidence of low usage. The monitor reads saved log lines; markers are
for provenance, not an alternative success check. For multi-container Jobs report each container separately.
The 1.3x Tier 0 repair factor is a bounded recovery rule; deliberate profile/review sizing uses 1.5x.

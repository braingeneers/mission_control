# R4 single shadow comparison

Window: 2026-11-18T10:52:21 to 2026-11-18T11:23:05 (workstation local time).
Installed evidence: read-only monitor.log and copied task/event state. Snapshot start 2026-11-18T11:22:21.
Private evidence: `/private/tmp/claude-501/nrp-shadow/pass-afbwh5g0`; exit 0.

Checked: installed monitor was never executed. Snapshot is a sequential copy, not an atomic checkpoint. Installed decisions below are recent recorded observations, not a replay on the same cluster snapshot. No recent event means unknown, not an installed decision to do nothing. Task-scoped actions repeat across stage rows and do not imply an action on each stage.

| Task / stage | Installed snapshot / recent event | Shadow outcome / task-scoped attempted action | Comparison |
|---|---|---|---|
| fig2rel-dna-bounded-trial-r2 / search | running/done; submitted fig2rel-dna-bounded-r2-baseline (attempt 1) by monitor (5 task events in window) | running/done; subprocess aws | expected: shadow suppression (IO gates); downstream state is provisional |
| fig2rel-dna-bounded-trial-r2 / baseline | running/running; submitted fig2rel-dna-bounded-r2-baseline (attempt 1) by monitor (5 task events in window) | running/running; subprocess aws | expected: shadow suppression (IO gates); downstream state is provisional |
| fig2rel-dna-bounded-trial-r2 / bounded | running/pending; submitted fig2rel-dna-bounded-r2-baseline (attempt 1) by monitor (5 task events in window) | running/pending; subprocess aws | expected: shadow suppression (IO gates); downstream state is provisional |
| fig2rel-dna-search-r7 / search | WITH_COORDINATOR/failed; no event in window (0 task events in window) | WITH_COORDINATOR/failed; no external action reached | unknown: no recent installed event; snapshot unchanged |
| fig2rel-dna-search-r7 / merge | WITH_COORDINATOR/pending; no event in window (0 task events in window) | WITH_COORDINATOR/pending; no external action reached | unknown: no recent installed event; snapshot unchanged |
| ft-batches-r3 / behaviour-shards | retrying/done; utilization review (12 task events in window) | retrying/done; agents.dispatch_agent | expected: shadow suppression (IO gates); downstream state is provisional |
| ft-batches-r3 / behaviour-assemble | retrying/done; utilization review (12 task events in window) | retrying/done; agents.dispatch_agent | expected: shadow suppression (IO gates); downstream state is provisional |
| ft-batches-r3 / matched-shards | retrying/running; utilization review (12 task events in window) | retrying/running; agents.dispatch_agent | expected: shadow suppression (IO gates); downstream state is provisional |
| ft-batches-r3 / matched-assemble | retrying/pending; utilization review (12 task events in window) | retrying/pending; agents.dispatch_agent | expected: shadow suppression (IO gates); downstream state is provisional |
| ft-celltype-baselines-r2 / celltype | retrying/running; no event in window (0 task events in window) | retrying/running; no external action reached | unknown: no recent installed event; snapshot unchanged |
| ft-disease-baseline / labels | NEEDS_OWNER/done; no event in window (0 task events in window) | NEEDS_OWNER/done; no external action reached | unknown: no recent installed event; snapshot unchanged |
| ft-disease-baseline / baseline | NEEDS_OWNER/running; no event in window (0 task events in window) | NEEDS_OWNER/running; no external action reached | unknown: no recent installed event; snapshot unchanged |
| ft-disease-baseline / merge | NEEDS_OWNER/pending; no event in window (0 task events in window) | NEEDS_OWNER/pending; no external action reached | unknown: no recent installed event; snapshot unchanged |
| ft-official-units-region / official-units | running/done; submitted ft-baselines-region-20261117t201915z (attempt 4) by monitor (8 task events in window) | running/done; no external action reached | same snapshot state; recent event is historical |
| ft-official-units-region / region | running/running; submitted ft-baselines-region-20261117t201915z (attempt 4) by monitor (8 task events in window) | running/running; no external action reached | same snapshot state; recent event is historical |
| ft-pilot-cpu-cpu-20261117e-full / full | running/running; submitted ft-pilot-cpu-cpu-20261117e-full (attempt 11) by monitor (8 task events in window) | running/running; no external action reached | same snapshot state; recent event is historical |
| t71-7b-profile-20260720-ws1-16-4753f3 / profile-maxtwo_cw20107_20260720_well000-ws1-16 | running/failed; fix agent start (3 task events in window) | WITH_COORDINATOR/failed; agents.dispatch_agent | expected: shadow suppression (IO gates); downstream state is provisional |
| t71-7b-profile-20260720-ws17-64-4753f3 / profile-maxtwo_cw20107_20260720_well000-ws17-64 | running/running; submitted pv3-gate-hschweig-25ed7b66 (attempt 1) by monitor (2 task events in window) | WITH_COORDINATOR/failed; agents.dispatch_agent | unexplained: stage changed on newer cluster observation; agent suppression explains only coordinator routing |
| t71-7b-profile-20260720-ws65-128-4753f3 / profile-maxtwo_cw20107_20260720_well000-ws65-128 | running/running; submitted pv3-gate-hschweig-10b424bf (attempt 1) by monitor (2 task events in window) | WITH_COORDINATOR/failed; agents.dispatch_agent | unexplained: stage changed on newer cluster observation; agent suppression explains only coordinator routing |
| t71-7b-profile-loop1-ws1-16-4753f3 / profile-loop1_recordphase-ws1-16 | retrying/running; "No change" is not an allowed answer. mean/request (8 task events in window) | retrying/running; no external action reached | same snapshot state; recent event is historical |
| t71-7b-profile-loop1-ws17-64-4753f3 / profile-loop1_recordphase-ws17-64 | retrying/running; agent done cost=None denials=0 (7 task events in window) | retrying/running; agents.dispatch_agent | expected: shadow suppression (IO gates); downstream state is provisional |
| t71-7b-profile-loop1-ws65-128-4753f3 / profile-loop1_recordphase-ws65-128 | running/running; submitted pv3-gate-hschweig-36f19eb0 (attempt 1) by monitor (2 task events in window) | WITH_COORDINATOR/failed; agents.dispatch_agent | unexplained: stage changed on newer cluster observation; agent suppression explains only coordinator routing |
| t71-ks2-score-test4-r2-hp6-a68d3ef585 / score | running/pending; no event in window (0 task events in window) | running/pending; subprocess aws | expected: shadow suppression (IO gates); downstream state is provisional |

Counts (live task/stage rows): expected differences 10; unexplained differences 3; unchanged with recent evidence 4; unknown recent decision 6.

Unexplained differences: t71-7b-profile-20260720-ws17-64-4753f3 / profile-maxtwo_cw20107_20260720_well000-ws17-64; t71-7b-profile-20260720-ws65-128-4753f3 / profile-maxtwo_cw20107_20260720_well000-ws65-128; t71-7b-profile-loop1-ws65-128-4753f3 / profile-loop1_recordphase-ws65-128

Suppressed route counts: agents.dispatch_agent=12, kubectl delete=1, notify.push=1, s3.incluster_job=1, subprocess aws=24, wake.process_task_webhooks=1

Limits: agent results, postchecks, admission server-create probes and S3 fallback Jobs are unknown. AWS subprocesses are suppressed too, so external S3 observations are unknown. GPU exec fallback is forbidden. Webhooks/wakes and pushes are skipped at their semantic boundary; queued deliveries are not simulated. These are intentional shadow restrictions, not production behavior changes or Cut-register differences. C1–C4 remain the approved rewrite differences; no cut-driven difference is asserted without evidence. Local task changes after suppressed actions are provisional. A day of comparisons is still required.

Pass diagnostics: 1 error log lines (private evidence).

Global coverage limitation (checked in private monitor.log): `check_pods` stopped at the forbidden `kubectl delete` boundary. Legacy pod enforcement therefore was not completed. No object was deleted.

The three new failed stages above recorded the same code failure (`ValueError` parsing stringified group bounds `[17` / `[65`) in live Job logs. A newer observation between the copied state and shadow reads is a plausible explanation, but this is **inferred**, not a proven installed/rewrite match. They remain unexplained for R4. The copied installed task events were also read: recent events support the submitted/running and utilization-review histories above; held tasks retain older events outside this window.

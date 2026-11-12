# NRP monitor: known issues (2026-11-11)

Repository changes affect the live monitor only after installation. No live binaries,
monitor state, scheduler, cluster Jobs or agent configuration were changed for this follow-up.

## Verified fixes in the repository

Offline regressions cover expiring shared node exclusions (24 hours after the latest fault),
historical Thanos placement for vanished pods, stage exclusion CLI, safe terminal Job replacement,
coordinator `NRP_TASK` help, Gemini eligibility failover, open-Claude wake deferral, and
migration of custom legacy launchd labels. Installer tests use a fake HOME and launchctl.
Ambiguous historical placement never chooses a node. No Thanos placement query or repair
was exercised against the real cluster in this follow-up.

One live Antigravity call (`gemini-3.8-flash-low`) returned a parseable BENIGN verdict;
the transcript proves a disallowed `touch` was denied by the generated hook. The call
warned that disabling slash commands cancels plan mode. The conflicting flag was removed;
the final plan-mode argv has only offline coverage. Live config remains operator-selected.
The Gemini CLI's server-side IneligibleTierError/UNSUPPORTED_CLIENT remains an upstream
availability problem; the monitor now fails over instead of treating it as a bad verdict.

## Wake limitations

A live test found that Claude resume into an open interactive session forks a sibling that
the open chat never sees. The monitor now defers when a process names the session or its
transcript changed within five minutes (or process inspection fails). Deferrals consume
WAKE_MAX_TRIES and eventually use the existing fallback; they are never delivery success.
This is conservative detection, not an atomic session lock: a session opened after the check
can still race. Closed-Claude wake and Codex resume from another cwd were seen working in
coordinator CLI tests on November 11. Relay delivery to the intended T3 chat is still unverified.
Wakes block a pass for up to 600 seconds each. Separate task escalations are not merged.

## Remaining limits and unverified behavior

- Codex agents can read any file the user can, including credentials; its sandbox constrains
  writes/network rather than reads. Command allowlists match prefixes. Codex and Gemini/agy
  have time limits but no dollar or turn cap.
- A real cluster repair by Codex, real fixer Claude permission patterns, and real agents producing
  useful HANDOFF_ENTRY blocks remain unverified. Unit tests use fake agents.
- Push notifications are unreliable while a terminal is active; use the persisted digest/Slack DM.
  Auto-arm and heartbeat hooks are Claude-specific; other coordinators must register/check manually.
- Queue time counts against activeDeadlineSeconds; progress tracking uses changing log tails rather
  than per-item S3 counts. The script enforces deadline presence, not measured-runtime derivation.
- A completion followup is not retried if all runners are unavailable when it fires.
- Existing tasks may have no origin or useful handoff. Local plan work never runs automatically;
  launchd cannot read Desktop repositories, so task code uses a cache clone.
- Live pv3 import behavior after multi-directory reship remains unverified; packaging layout is tested.
- `UTIL_OK` is intentionally narrow: lab-floor-only, running non-GPU tasks, bounded count/time;
  ordinary NRP-band/GPU failures cannot be waived.
- Never-submitted pending stages reuse existing success markers after their gates pass, without rerunning.
  Use fresh output keys when a new computation is intended: marker existence does not validate provenance.
  Running Job success still requires all Indexed Job completions and exact head-object keys.

### Same-name Jobs on resume or manual submission

`task resume` can leave a stage pending while a same-name failed Job still exists. A Job created
manually can also collide with submission. Inspect task ownership and Job state first: never
remove a running or pending Job to clear a name. The submission helper already saves logs and
deletes a terminal same-name Job before applying; resume/observation may still adopt it before
that helper runs. Preserve logs, then explicitly remove only the confirmed failed owned Job and
resume through the task's normal submission path. This draft does not change adoption semantics.

## Cost ledger rollout limits

The ledger starts with new events after installation. Historical task/digest events support wake counts but cannot recover unreported tokens or USD cost. T3 relay/CLI wakes do not report coordinator consumption; those costs remain null. Completion wakes are intentionally unchanged pending a separate batching design. Default cap scaling affects new tasks that omit `max_retries`; existing tasks retain their stored cap, though the deputy can raise it within the scaled bound. Recorded resolutions mean accepted state transitions or verified markers, not proof that the eventual outputs pass scientific review.

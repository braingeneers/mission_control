<!-- Handoff for one monitor task. Write it once the monitor is started, before you return; then put its path in the task's "handoff" field.
     Comments like this one are ignored. Use ### for sub-headings inside a section, never ## (a ## line starts a new section). -->

## Registrar

<!-- You write this section, once. Later agents read it and cannot change it. At least 200 characters; aim for 1 to 3 KB. Cover:
     what is being done and why; what each stage produces (paths); what to check when it finishes and what to check when it fails;
     decisions already made (and who made them); things NOT to do; where the code, manifests and outputs are.
     ALSO write, in your own words, who handles failures (the monitor warns when this chat's handoff never says it). Something like:
       "Failures are handled by the monitor's own subagents (Tier 1 triage, Tier 2 fixer), not by me. If they cannot fix it, the monitor
        wakes this chat (as a last resort) with a short summary; I then fix it and `nrp-monitor task resume NAME`, or cancel. The owner is
        notified only after that, when I run `nrp-monitor task needs-owner NAME --reason ...`. I am also woken once when the plan step
        finishes (not once per pod or Job)." -->

## Fix log

<!-- Owned by fix agents. The monitor script appends one entry per attempt (UTC time, failure class, what was tried, result) from the
     agent's HANDOFF_ENTRY block. Nobody edits this by hand. -->

## Continuation

<!-- Owned by continue agents. The monitor script appends what was checked, which next step was registered and the open items.
     Nobody edits this by hand. -->

## For the owner

<!-- Questions and decisions that need a person. The script appends FOR_OWNER lines from either kind of agent. -->

## Wake route and resource review

T3 origins can use `origin.link: "t3-thread://v2/ENV/THREAD"` (angle brackets around the link are accepted).
A configured `<state>/webhooks/<task>` remains the preferred T3 route. Otherwise the monitor sends the wake text
on stdin to `t3 thread send THREAD -`. It selects `NRP_MONITOR_T3_BIN`, then `~/.t3/bin/t3`, then `t3` on PATH.
Missing binaries, nonzero exits, timeouts and an unavailable server count as unavailable delivery: retry up to
`WAKE_MAX_TRIES` (six passes), then fall back to NEEDS_OWNER for an escalation. No new thread is created.
Claude and Codex origins still resume their recorded sessions. Plan-step completion keeps one aggregate wake per step.

Record measured stage runtime, per-pod peaks and earlier OOM limits in the handoff. The triage judge only returns CLOSE or ESCALATE; every Job, manifest and resource change belongs to the fixer. A utilization flag alone leaves running work running.

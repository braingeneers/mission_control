# The handoff

A handoff is one markdown file per task. The agent that registers the task writes it, once, after the monitor is
started and before it returns. Later, when the monitor starts a triage, fix or continue agent, that agent gets the
handoff in its prompt, so it knows what the work is for, what was decided and what not to touch, without the original
chat. Nothing here depends on a particular assistant: any agent that can write a markdown file can register a task.

Start from `scripts/templates/handoff.md` (installed as `~/.local/state/nrp-monitor/templates/handoff.md`).

## Sections and owners

| Heading | Written by | Rule |
| --- | --- | --- |
| `## Registrar` | the registering agent, once | Read-only for everyone afterwards. |
| `## Fix log` | the monitor script, from fix agents' answers and coordinator resume notes | Append-only. Attempts and standing decisions. |
| `## Continuation` | the monitor script, from continue agents' answers | Append-only. What was checked, which step was registered, open items. |
| `## For the owner` | the monitor script, from either kind of agent | Append-only. Questions and decisions that need a person. |

Use `###` for sub-headings inside a section, never `##` (a `##` line starts a new section). Text inside `<!-- -->` is
ignored by every check and is not shown to agents; the template's guidance lines are comments.

## Attaching it

Either put the path in the task file before `task add` (`"handoff": "handoff.md"`; absolute, `~`, or relative to the
task file's folder), or, because the handoff is best written after the task is registered and the monitor is
confirmed, attach it afterwards:

    nrp-monitor task handoff NAME FILE

Both validate the file and copy it to `<state>/tasks/NAME/handoff.md`. That copy is the only one agents ever see (the
scheduler cannot read `~/Desktop`), and `handoff.orig.md` beside it is the unmodified original. Edit your source file
afterwards and nothing changes. A task that already has a handoff keeps it: the Registrar is written once.
`nrp-monitor task show NAME` prints `handoff: accepted, Registrar intact, ...` and the number of entries in each
section; `handoff: none` means nothing was accepted.

Checks: the file must exist, must not be empty, must have a `## Registrar` heading and at least 200 characters of text in
it, at most 16,000 characters there and 100 KB in all, and no repeated `##` heading. A missing, empty or thin handoff is a warning
at `task add` (the same style as the missing-continuation warning); with `NRP_MONITOR_REQUIRE_HANDOFF=1` the add is
refused instead (a continue agent registering the next plan step is only warned). Too long or a repeated heading is
always refused. A finished task with no (or a thin) handoff is listed in the digest as `no-handoff`.

## What the script writes

Agents never edit the file; they run unattended, sometimes sandboxed. The fix and continue prompts embed the handoff
(the Registrar whole, the newest entries of each log section, about 14,000 characters at most) and ask the agent to end
its final answer with:

    HANDOFF_ENTRY:
    <what you tried / checked / decided / next, plain text, about 1500 characters at most>

The script takes everything after the last `HANDOFF_ENTRY:` line, cuts it to 1500 characters, neutralises anything that
could open a heading, a code fence or a comment, and appends it with the UTC time, the agent kind and the attempt number
to `## Fix log` (fix agents) or `## Continuation` (continue agents), using the state lock and an atomic replace. A line
starting `FOR_OWNER:` inside the block goes to `## For the owner` instead (and appears in the digest as
`handoff-owner`). If the agent returns no block, the script appends one automatic line (failure class, the agent's
report, its last words), so a log is never blank.

The Registrar is protected twice. The script writes only the three append sections, and it compares the Registrar's hash
(kept in the task record) before and after every append. If an agent changed the file anyway, the Registrar is restored
from `handoff.orig.md`, the event is logged and a `fault` line goes to the digest; if the original does not match either,
nothing is appended and the fault says so. Follow-up agents (a read-only report when the task finishes) also see the
handoff but add nothing.

## What a good Registrar contains

- What is being done and why, in two or three sentences, and who decided it.
- What each stage produces: the output paths, and what a good result looks like (counts, files).
- What to check when it finishes, and what to check when it fails (the usual suspects, where the logs are).
- Decisions already made, with who made them and when, so a fix agent does not reopen them.
- Things NOT to do: inputs not to change, numbers not to lower, jobs and namespaces not to touch.
- Where the code, manifests and outputs are.
- Who handles failures: the monitor's subagents (Tier 1 triage, Tier 2 fixer) fix things; the registering chat is woken only as a last
  resort, after them, with a short summary and the commands to resume, cancel or (only if the owner is truly needed) `task needs-owner`; the
  owner hears only after that. `task add` prints this reminder and warns when the handoff never says it (the template shows wording).

It is not a log (the script keeps that) and not a copy of the task file. One to three KB is plenty.

### Worked example

    ## Registrar

    Sam is rebuilding the quality-control table for the pilot recordings (approved by Sam, 2026-11-05) so the
    spike-sorting comparison can start. Stage `qc` builds one summary row per recording and writes
    s3://braingeneersdev/sam/qc/summary.csv plus the marker s3://braingeneersdev/sam/qc/DONE.

    A good result has 48 rows (one per recording) and no recording with zero units. If it fails, check memory first:
    the loader holds a whole recording and peaked near 6 GB in the pilot. Logs are in the task's `logs/` folder.

    Decided: the recording list `manifests/pilot.txt` was fixed by Sam; the unit threshold of 20 spikes is Sam's.
    Do NOT drop recordings or lower the threshold to make a run pass; a recording that fails a validity check is
    skipped and logged in `excluded`, and more than 5% skipped means stop and ask Sam.

    Code: lab repo, `qc/` (the task's code clone is a branch of it). Next step after this task: the comparison step of
    the plan `PLAN.md#sorting`; the continue agent checks `summary.csv` has 48 rows first.

## Limits

- The script appends only what an agent returned. An agent that crashes leaves an automatic line, not its reasoning.
- The 1500-character cap applies to each entry; the file is capped at 100 KB at registration, but appended entries can
  grow it later. Prompts embed at most the newest entries, with a note saying how many older ones were left out.
- Tasks registered before this feature, or without a handoff, run exactly as before: no file, and the prompts say
  "(no handoff written)".
- It is not a secret store: never put tokens or credentials in a handoff.

## Wake route and resource review

T3 origins can use `origin.link: "t3-thread://v2/ENV/THREAD"` (angle brackets around the link are accepted).
A configured `<state>/webhooks/<task>` remains the preferred T3 route. Otherwise the monitor sends the wake text
on stdin to `t3 thread send THREAD -`. It selects `NRP_MONITOR_T3_BIN`, then `~/.t3/bin/t3`, then `t3` on PATH.
Missing binaries, nonzero exits, timeouts and an unavailable server count as unavailable delivery: retry up to
`WAKE_MAX_TRIES` (six passes), then fall back to NEEDS_OWNER for an escalation. No new thread is created.
Claude and Codex origins still resume their recorded sessions. Plan-step completion keeps one aggregate wake per step.

Record measured stage runtime, per-pod peaks and earlier OOM limits in the handoff. The triage judge only returns CLOSE or ESCALATE; every Job, manifest and resource change belongs to the fixer. A utilization flag alone leaves running work running.

`task resume --note TEXT` appends a dated coordinator decision to the Fix log when a handoff is attached.
Matching later failures follow that decision within the task approval. Notes use the same sanitization and
1500-character entry limit as fix entries; omitted prompt history remains in the full handoff file.

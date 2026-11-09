<!-- Handoff for one watchdog task. Write it once the monitor is started, before you return; then put its path in the task's "handoff" field.
     Comments like this one are ignored. Use ### for sub-headings inside a section, never ## (a ## line starts a new section). -->

## Registrar

<!-- You write this section, once. Later agents read it and cannot change it. At least 200 characters; aim for 1 to 3 KB. Cover:
     what is being done and why; what each stage produces (paths); what to check when it finishes and what to check when it fails;
     decisions already made (and who made them); things NOT to do; where the code, manifests and outputs are. -->

## Fix log

<!-- Owned by fix agents. The watchdog script appends one entry per attempt (UTC time, failure class, what was tried, result) from the
     agent's HANDOFF_ENTRY block. Nobody edits this by hand. -->

## Continuation

<!-- Owned by continue agents. The watchdog script appends what was checked, which next step was registered and the open items.
     Nobody edits this by hand. -->

## For the owner

<!-- Questions and decisions that need a person. The script appends FOR_OWNER lines from either kind of agent. -->

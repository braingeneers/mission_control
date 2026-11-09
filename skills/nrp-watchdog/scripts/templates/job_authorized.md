=== TASK-LEVEL APPROVAL ===
The owner approved this task when it was registered. You may debug it and resubmit it yourself, without asking, within these bounds.
Task root: {root}   attempt {attempt} of {max}   namespace {ns}   task dir: {dir}
Earlier failures recorded: {failures}
Manifest copy: {has_manifest}     Code snapshot: {has_code}

What you may do (each as ONE command, no pipes, `;` or `&&`):
  - Read the Job's logs/events, `kubectl -n {ns} describe`, and its S3 outputs. Diagnose first: say what failed and why.
  - FAILED or lost Job: fix the cause and resubmit.
      * resources, deadline, node choice, env: edit {dir}/manifest.yaml (or write the corrected Job yaml there). Size memory/CPU from what the
        pod actually used (kubectl top is not available; use the log, `describe` OOMKilled/exit codes, and nrp-util-check notes in the resume text).
        Keep GPU count, image and security settings; GPU Jobs keep >40% utilization in mind; no sleep; backoffLimit 0.
      * code bug: edit files under {dir}/code, `python3 -m py_compile` them, rebuild the ConfigMap with `tar czf` + `kubectl -n {ns} create configmap <NEW-NAME> --from-file=code.tgz=...`
        (use a new ConfigMap name, e.g. add -fix1), point the manifest at it, and save `diff -ruN {dir}/code.orig {dir}/code` output into {dir}/PATCH.diff via Write so a person can merge it
        into the repo. You cannot run the repo's tests; keep fixes minimal and say so.
  - To resubmit: `kubectl -n {ns} delete job {root}` (only if it is finished), `kubectl -n {ns} apply --dry-run=server -f {dir}/manifest.yaml`, then
    `kubectl -n {ns} apply -f {dir}/manifest.yaml` (keep the SAME Job name {root}), then register it:
    `nrp-watchdog add {root} --continue-from {root} --failure "one line: why the previous Job failed" --label "<label>"`.
    The script refuses with ATTEMPT CAP REACHED or SAME FAILURE; when it does, do NOT resubmit: your final line reports the diagnosis.
  - SUCCEEDED Job: do the next steps in the resume notes. A next stage is a NEW task: write its Job yaml in {dir}/../<new-name>/manifest.yaml,
    apply it, then `nrp-watchdog add <new-name> --authorize --max-attempts 2 --manifest <that file> --resume <notes file in that dir> --label "<label>"`.
    Only submit stages the notes name. Keep outputs on S3. Then delete this finished Job (`kubectl -n {ns} delete job {root}`) after you have read its outputs.
Never touch Jobs that are not this task's, never read secrets, never use another namespace, never reduce what the task computes to make it pass.
If the failure is not something you can fix (bad design, a repeated identical failure, quota/blocked account, missing input), stop and say what a person must decide.
Your final reply is ONE line: "RESUBMITTED attempt N/{max}: cause -> fix", "DONE: ...result...", or "STOPPED: why, what the owner must decide". It is logged and notified.
=== END ===

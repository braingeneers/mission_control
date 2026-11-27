"""NRP monitor nrp_task (mechanical extraction; R3a)."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import code_shipping as _m_code_shipping
from . import cluster as _m_cluster
from . import decisions as _m_decisions
from . import ladder as _m_ladder
from . import plans as _m_plans
from . import state as _m_state
from .task import pass_ as _m_task_pass_
from .task import registry as _m_task_registry
from . import timeouts as _m_timeouts

# ---- nrp-task: the fix agent's only shell tool -------------------------------------------------------------------
def cmd_tool(a):
    from . import stage_jobs as _m_stage_jobs
    from . import s3 as _m_s3  # Local import avoids orchestration cycles.
    from . import config as _m_config  # Local import avoids orchestration cycles.
    from . import task_commands as _m_task_commands  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.rest[:1] == ["configmap"]:
        sys.exit("Code bundles in ConfigMaps are banned on NRP. Use nrp-task ship.")
    if a.rest[:1] != ["ship"] and any(x in ("--help", "-h") for x in a.rest):
        print("Usage: NRP_TASK=<name> nrp-task show|logs JOB|describe JOB|util JOB|s3 ls URI|ship NAME [--from SUBDIR]|reship JOB [--allow-unpushed]|submit JOB --reason TEXT\n"
              "Coordinator chats must select a task with NRP_TASK; use nrp-monitor task list to find it.")
        return 0
    n = os.environ.get("NRP_TASK", "")
    t = _m_state.task_load(n)
    if not t:
        sys.exit("nrp-task: use NRP_TASK=<name> nrp-task ...; live tasks: " + ", ".join(
            n for n in _m_state.task_names() if (_m_state.task_load(n) or {}).get("status") in _m_state.TASK_LIVE))
    argv, ns = a.rest, t["namespace"]
    jobs = {s["job"]: s for s in t["stages"]}
    usage = ("nrp-task show | logs JOB [--tail N] | describe JOB | util JOB | s3 ls URI | s3 cat URI | ship NAME [--from SUBDIR] | "
             "reship JOB | commit MESSAGE | submit JOB --reason TEXT | delete JOB | plan | next-add FILE | "
             "report RESUBMITTED|STOPPED|DONE|CONTINUED|WAITING|NOT-DONE TEXT")
    if not argv:
        sys.exit(usage)
    c, rest = argv[0], argv[1:]
    if os.environ.get("NRP_MONITOR_AGENT_ROLE") == "triage" and c not in ("show", "logs", "describe", "util", "s3"):
        sys.exit("triage is judge only; changes belong to the fixer")

    def need_job():
        if not rest or rest[0] not in jobs:
            sys.exit("nrp-task %s: JOB must be one of this task's Jobs: %s" % (c, ", ".join(jobs)))
        return rest[0]

    def kc(*args):
        r = _m_cluster.kubectl("-n", ns, *args, timeout=180)
        sys.stdout.write(r.stdout[-60000:])
        sys.stderr.write(r.stderr[-2000:])
        return r.returncode

    from . import cli_args
    if c in ("resize", "restart"):
        opts = cli_args.tool_parser(c).parse_args(rest)
        opts.name = n
        ok, message = _m_stage_jobs.utilization_restart(n, opts.stage, opts.cpu, opts.mem)
        print(message)
        return 0 if ok else 1
    if c == "decide":
        args = cli_args.tool_parser(c).parse_args(rest)
        _m_state.task_txn(n, lambda task: _m_decisions.record_decision(task, args.fingerprint, args.action, args.why, "task", args.max_uses, os.environ.get("NRP_MONITOR_AGENT_ROLE", "agent")))
        return 0
    if c == "apply-decision":
        if not _m_decisions.apply_decision(n, argparse.Namespace(dry_run=False)):
            sys.exit("decision not applicable or refused by budgets/markers")
        return 0
    if c == "retry-cap":
        if os.environ.get("NRP_MONITOR_AGENT_ROLE") != "deputy" or len(rest) != 1 or not rest[0].isdigit():
            sys.exit("retry-cap is deputy-only: N")
        value = int(rest[0])
        if not t["max_retries"] <= value <= _m_decisions.scaled_retry_cap(t["stages"]):
            sys.exit("retry-cap exceeds scaled cap or lowers the existing cap")
        _m_state.task_txn(n, lambda task: task.update(max_retries=value))
        return 0
    if c == "show":
        return _m_task_commands.cmd_task_show(argparse.Namespace(name=n))
    if c == "logs":
        j = need_job()
        tail = rest[rest.index("--tail") + 1] if "--tail" in rest else "200"
        if not tail.isdigit():
            sys.exit("--tail N")
        saved = sorted((_m_state.task_dir(n) / "logs").glob(j + "-a*.txt"))
        if t["status"] == "done" and saved:
            print("\n".join(saved[-1].read_text().splitlines()[-int(tail):]))
            return 0
        rc = kc("logs", "job/" + j, "--all-containers", "--tail=" + tail)
        if rc:
            print("(live logs unavailable; saved logs: %s)" % ", ".join(str(p) for p in sorted((_m_state.task_dir(n) / "logs").glob(j + "-a*.txt"))))
        return 0
    if c == "describe":
        j = need_job()
        kc("describe", "job", j)
        return kc("describe", "pods", "-l", "job-name=" + j)
    if c == "util":
        j = need_job()
        r = subprocess.run(["nrp-util-check", "-n", ns, "--min-age", "0", j + "-"], capture_output=True, text=True, timeout=300)
        print(r.stdout.strip() or r.stderr.strip())
        return 0
    if c == "postcheck":
        if rest:
            sys.exit("postcheck takes no arguments; only the declared command may run")
        result = _m_task_pass_.run_postcheck(t)
        print(json.dumps(result))
        return 0 if result["ok"] else 1
    # Retained bounded plan-completion copy; independent of removed night code.
    if c == "s3" and rest[:1] == ["cp"]:
        if len(rest) != 3:
            sys.exit("s3 cp URI DEST")
        uri, dest = rest[1:]
        h = _m_plans.plan_header((t.get("on_done") or {}).get("plan")) or {}
        if not any(uri.startswith(prefix.rstrip("/") + "/") for prefix in h.get("may_touch", []) if prefix.startswith("s3://")):
            sys.exit("source outside plan may_touch")
        if dest.startswith("s3://"):
            if not any(dest.startswith(prefix.rstrip("/") + "/") for prefix in h.get("may_touch", []) if prefix.startswith("s3://")):
                sys.exit("destination outside plan may_touch")
            target = dest
        else:
            root = (_m_state.task_dir(n) / "downloads").resolve()
            target = Path(dest).resolve()
            if not target.is_relative_to(root):
                sys.exit("destination must be under task downloads")
        if not _m_s3.s3_split(uri) or (dest.startswith("s3://") and not _m_s3.s3_split(dest)):
            sys.exit("copy requires exact object URIs")
        bucket, key = _m_s3.s3_split(uri)
        head = subprocess.run(_m_task_registry.aws_cmd() + ["s3api", "head-object", "--bucket", bucket, "--key", key],
                              capture_output=True, text=True, timeout=120, env=_m_config.aws_env())
        try:
            size = json.loads(head.stdout)["ContentLength"]
        except (ValueError, KeyError):
            sys.exit("cannot verify small object size")
        if head.returncode or not isinstance(size, int) or not 0 <= size <= 256 * 1024:
            sys.exit("copy limited to objects up to 256 KiB")
        if isinstance(target, Path):
            target.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(_m_task_registry.aws_cmd() + ["s3", "cp", uri, str(target)], capture_output=True, text=True, timeout=120, env=_m_config.aws_env())
        print(result.stdout[-1000:])
        return result.returncode
    if c == "s3":
        if len(rest) != 2 or rest[0] not in ("ls", "cat"):
            sys.exit("nrp-task s3 ls|cat s3://bucket/key")
        r = subprocess.run(["nrp-s3-read", rest[0], rest[1]], capture_output=True, text=True, timeout=300)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr[-1000:])
        return r.returncode
    if c == "ship":
        parser = argparse.ArgumentParser(prog="nrp-task ship")
        parser.add_argument("name")
        parser.add_argument("--from", dest="from_dir", metavar="SUBDIR")
        parser.add_argument("--add", action="append", default=[], metavar="PATH")
        parser.add_argument("--allow-unpushed", action="store_true", help="debug only")
        return _m_code_shipping.ship_code(t, parser.parse_args(rest))
    if c == "reship":
        parser = argparse.ArgumentParser(prog="nrp-task reship")
        parser.add_argument("job", choices=jobs)
        parser.add_argument("--add", action="append", default=[], metavar="PATH")
        parser.add_argument("--allow-unpushed", action="store_true", help="debug only")
        opts = parser.parse_args(rest)
        j = opts.job
        if not t.get("code"):
            sys.exit("this task has no code clone")
        job_state = _m_cluster.job_state(j, ns)
        if job_state == "error":
            sys.exit("could not verify Job %s has stopped" % j)
        if job_state in ("running", "pending"):
            sys.exit("Job %s is still running or pending; reship only for a finished, failed or deleted Job" % j)
        manifest = jobs[j]["manifest"]
        try:
            adapter = _m_code_shipping.shipping_adapter(t["code"], manifest)
            if adapter:
                if opts.add:
                    sys.exit("--add requires the generic code shipping adapter")
                return adapter.reship(n, j, manifest, t["code"], _m_code_shipping.upload_code_archive)
            return _m_code_shipping.reship_code(t, j, manifest, allow_unpushed=opts.allow_unpushed, additions=opts.add)
        except (_m_state.ChainError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
            sys.exit("reship refused: %s" % exc)
    if c == "commit":
        if not t.get("code") or not rest:
            sys.exit("nrp-task commit MESSAGE (task needs a code clone)")
        cl = t["code"]["clone"]
        diff = _m_task_registry.git("diff", "--no-renames", "--name-only", "-z", "--diff-filter=DMRTUXB",
                                    "HEAD", cwd=cl)
        if diff.returncode:
            sys.exit("could not inspect tracked code changes")
        changed = [name for name in diff.stdout.split("\0") if name]
        if not changed:
            sys.exit("nothing to commit")
        try:
            _m_code_shipping.reject_denied(changed)
        except _m_state.ChainError as exc:
            sys.exit(str(exc))
        py = [name for name in changed if name.endswith(".py") and (Path(cl) / name).is_file()]
        for f in py:
            r = subprocess.run([sys.executable, "-m", "py_compile", str(Path(cl) / f)], capture_output=True, text=True)
            if r.returncode:
                sys.exit("py_compile failed for %s: %s" % (f, r.stderr.strip()[-300:]))
        r = _m_task_registry.git("--literal-pathspecs", "commit", "-qm",
                                 "monitor fix (%s): %s" % (n, " ".join(rest)[:200]), "--only", "--", *changed, cwd=cl)
        if r.returncode:
            sys.exit(r.stderr.strip() or "could not commit tracked code changes")
        sha = _m_task_registry.git("rev-parse", "--short", "HEAD", cwd=cl).stdout.strip()
        _m_state.task_txn(n, lambda t: _m_state.tev(t, "fix commit %s: %s" % (sha, " ".join(rest)[:150])))
        print("committed %s on %s (%d file(s)); compiled: %s" % (sha, t["code"]["branch"], len(changed), ", ".join(py) or "none"))
        return r.returncode
    if c == "submit":
        j = need_job()
        if "--reason" not in rest or rest.index("--reason") + 1 >= len(rest):
            sys.exit("nrp-task submit JOB --reason 'cause -> fix'")
        ok, msg = _m_stage_jobs.do_submit(n, jobs[j]["id"], rest[rest.index("--reason") + 1], "agent")
        print(msg)
        return 0 if ok else 1
    if c == "delete":
        j = need_job()
        st_, f = _m_cluster.job_state(j, ns), t.get("failure") or {}
        if st_ == "error":
            sys.exit("could not verify Job %s state before deletion" % j)
        util = t.get("util_event") or {}
        util_retry = util.get("job") == j and st_ in ("running", "pending")
        if util_retry:
            evidence = util.get("evidence") or {}
            if util.get("rule") == "gpu":                                 # a GPU under NRP's floor is a policy violation, not a sizing question:
                if not _m_state.GPU_PCT_RE.search(util["detail"]) or "no DCGM series" in util["detail"]:
                    sys.exit("utilization review: a GPU observation without a measured DCGM flag cannot authorize deletion")
            elif not _m_timeouts.stage_resumable(jobs[j]) or (util.get("rule") != "nrp" and  # NRP floor: restart whenever it resumes
                                                  (evidence.get("remaining_seconds") or 0) - max(0, _m_state.now() - util.get("ts", _m_state.now())) <= 7200):
                sys.exit("utilization review: leave running Job to finish; resubmit requires resumable stage and >2h measured time left")
            f = util
        if st_ in ("running", "pending") and not (f.get("job") == j and f.get("cls") in ("util", "infra")):
            sys.exit("Job %s is %s; only a finished Job, or one this task's failure says to stop (util/stuck), may be deleted" % (j, st_))
        result = _m_stage_jobs.delete_stage_job(t, jobs[j], "deleted by the fix agent")
        rc = result.returncode
        if rc:
            print(result.stderr, file=sys.stderr)
            return rc
        if rc == 0 and util_retry:
            _m_ladder.task_fail(n, jobs[j]["id"], "util", util["sig"], util["detail"], extra={"evidence": util.get("evidence")})
        _m_state.task_txn(n, lambda t: _m_state.tev(t, "agent deleted Job %s (was %s)" % (j, st_)))
        return rc
    if c == "plan":
        od = t.get("on_done")
        if not od:
            sys.exit("this task belongs to no plan")
        h = _m_plans.plan_header(od["plan"])
        go, held = _m_plans.next_steps(h, od["from_step"])
        print("plan %s, this task ran step %s. Approved through %s. Stops for the owner: %s. may_touch: %s"
              % (od["plan"], od["from_step"], h["approved_through"], ", ".join(h["stops"]) or "none", ", ".join(h["may_touch"]) or "-"))
        print("may start now: %s" % (", ".join(go) or "nothing"))
        for x in held:
            print("held: step %s (%s)" % x)
        print("plan text: %s   templates: %s   write next TASK files under: %s"
              % (_m_plans.plan_dir(od["plan"]) / "plan.md", _m_plans.plan_dir(od["plan"]) / "files", _m_plans.plan_dir(od["plan"]) / "work"))
        return 0
    if c == "next-add":
        return _m_plans.tool_next_add(n, t, rest)

    if c == "report":
        kinds = ("CONTINUED", "WAITING", "NOT-DONE", "STOPPED") if (t.get("continuation") or {}).get("state") == "running" \
            else ("RESUBMITTED", "STOPPED", "DONE", "UTIL_OK")
        if len(rest) < 2 or rest[0] not in kinds:
            sys.exit("nrp-task report %s 'one line'" % "|".join(kinds))
        line = " ".join(" ".join(rest[1:]).split())[:400]
        _m_state.task_txn(n, lambda t: (t.update(report={"status": rest[0], "line": line, "ts": _m_state.now()}), _m_state.tev(t, "agent report %s: %s" % (rest[0], line))))
        print("recorded")
        return 0
    sys.exit(usage)


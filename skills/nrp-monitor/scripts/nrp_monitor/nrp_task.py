"""NRP monitor nrp_task (mechanical extraction; R3a)."""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import agents as _m_agents
from . import cluster as _m_cluster
from . import decisions as _m_decisions
from . import ladder as _m_ladder
from . import plans as _m_plans
from . import state as _m_state
from .task import pass_ as _m_task_pass_
from .task import registry as _m_task_registry
from . import timeouts as _m_timeouts

# ---- nrp-task: the fix agent's only shell tool -------------------------------------------------------------------
def reship_dirs(code):
    """(primary package dir, [extra package dirs]) that `nrp-task reship` packs: everything the task's code declares.
    Primary = code.pkg_dir, else code.subdir when it is the predictor_v3 folder, else <clone>/predictor_v3. Extras = code.extra_pkg_dirs
    (relative = inside the clone, absolute = another checkout read in place). Raises ChainError when something declared is missing."""
    clone = Path(code["clone"])

    def res(x):
        p = Path(os.path.expanduser(x))
        return p if p.is_absolute() else clone / x
    if code.get("pkg_dir"):
        pkg = res(code["pkg_dir"])
    else:
        sub = clone / (code.get("subdir") or "")
        pkg = sub if sub.name == "predictor_v3" else clone / "predictor_v3"
    if not pkg.is_dir() or pkg.name != "predictor_v3":
        raise _m_state.ChainError("needs the predictor_v3 package folder (code.subdir, <clone>/predictor_v3, or code.pkg_dir); got %s" % pkg)
    extras = [res(x) for x in code.get("extra_pkg_dirs") or []]
    for x in extras:
        if not x.is_dir():
            raise _m_state.ChainError("code.extra_pkg_dirs: %s does not exist in the clone (commit it, or check the path)" % x)
    return pkg.resolve(), [x.resolve() for x in extras]


def cmd_tool(a):
    from . import s3 as _m_s3  # Local import avoids orchestration cycles.
    from . import config as _m_config  # Local import avoids orchestration cycles.
    from . import task_commands as _m_task_commands  # Local import breaks orchestration cycle; patches stay on the defining module.
    if any(x in ("--help", "-h") for x in a.rest):
        print("Usage: NRP_TASK=<name> nrp-task show|logs JOB|describe JOB|util JOB|s3 ls URI|reship JOB|submit JOB --reason TEXT\n"
              "Coordinator chats must select a task with NRP_TASK; use nrp-monitor task list to find it.")
        return 0
    n = os.environ.get("NRP_TASK", "")
    t = _m_state.task_load(n)
    if not t:
        sys.exit("nrp-task: use NRP_TASK=<name> nrp-task ...; live tasks: " + ", ".join(
            n for n in _m_state.task_names() if (_m_state.task_load(n) or {}).get("status") in _m_state.TASK_LIVE))
    argv, ns = a.rest, t["namespace"]
    jobs = {s["job"]: s for s in t["stages"]}
    usage = ("nrp-task show | logs JOB [--tail N] | describe JOB | util JOB | s3 ls URI | s3 cat URI | configmap NAME [--from SUBDIR] | "
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

    if c == "decide":
        parser = argparse.ArgumentParser(prog="nrp-task decide")
        parser.add_argument("fingerprint")
        parser.add_argument("--action", choices=_m_state.DECISION_ACTIONS, required=True)
        parser.add_argument("--why", required=True)
        parser.add_argument("--max-uses", type=int)
        args = parser.parse_args(rest)
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
    if c == "configmap":
        if not t.get("code"):
            sys.exit("this task has no code clone")
        if not rest or not re.match(r"^%s-[a-z0-9-]{1,40}$" % re.escape(n), rest[0]):
            sys.exit("configmap NAME must be %s-<suffix> (lowercase)" % n)
        sub = rest[rest.index("--from") + 1] if "--from" in rest else (t["code"].get("subdir") or ".")
        src = (Path(t["code"]["clone"]) / sub).resolve()
        if not src.is_dir() or not src.is_relative_to(Path(t["code"]["clone"]).resolve()):
            sys.exit("--from must be a folder inside the clone")
        tgz = _m_state.WORK / "task" / ("%s.tgz" % rest[0])
        tgz.parent.mkdir(parents=True, exist_ok=True)
        ex = [x for p in _m_state.CODE_SKIP for x in ("--exclude", p)] + [x for e in _m_state.CODE_SKIP_EXT for x in ("--exclude", "*" + e)]
        r = subprocess.run(["tar", "czf", str(tgz), *ex, "-C", str(src), "."], capture_output=True, text=True)
        if r.returncode or tgz.stat().st_size > 900 * 1024:
            sys.exit("tar failed or archive over 900 KB (ConfigMap limit 1 MB): %s" % r.stderr.strip()[:200])
        rc = kc("create", "configmap", rest[0], "--from-file=code.tgz=%s" % tgz)
        if rc == 0:
            _m_state.task_txn(n, lambda t: _m_state.tev(t, "configmap %s built from %s" % (rest[0], sub)))
        return rc
    if c == "reship":
        # pv3 Jobs run code shipped through S3 (spec.json -> code.uri), not code baked into the manifest: a fix in the clone
        # reaches the Job only when the clone's predictor_v3/ is packed like `--ship-code`, uploaded, and spec.json points at it.
        j = need_job()
        if not t.get("code"):
            sys.exit("this task has no code clone")
        if _m_cluster.job_state(j, ns) in ("running", "pending"):
            sys.exit("Job %s is still running; reship only for a finished, failed or deleted Job" % j)
        spec_uri = _m_task_registry.pv3_spec_uri(jobs[j]["manifest"])
        if not spec_uri:
            sys.exit("Job %s does not run from an S3 spec (no `--spec s3://...` in its command): nothing to reship" % j)
        try:
            pkg, extras = reship_dirs(t["code"])
        except _m_state.ChainError as e:
            sys.exit("reship refused: %s" % e)
        r = subprocess.run(_m_task_registry.aws_cmd() + ["s3", "cp", spec_uri, "-"], capture_output=True, text=True, timeout=180, env=_m_config.aws_env())
        try:
            spec = json.loads(r.stdout)
            old = spec["code"]["uri"]
        except Exception:
            sys.exit("cannot read %s with a `code` entry (aws rc=%d %s)" % (spec_uri, r.returncode, r.stderr.strip()[:150]))
        tgz = _m_state.WORK / "task" / ("%s-reship.tgz" % j)
        tgz.parent.mkdir(parents=True, exist_ok=True)
        py = os.environ.get("NRP_TASK_PYTHON") or (str(_m_state.CODE_PYTHON) if _m_state.CODE_PYTHON and _m_state.CODE_PYTHON.exists() else sys.executable)
        # the same `codeship.build` the original --ship-code used, from the package's own checkout; extra dirs are packed beside
        # predictor_v3/ exactly as at submission (PV3_CODE_EXTRA_PACKAGES layout), so the pod's imports resolve the same way
        snippet = ("import json,sys,pathlib; pkg,out=sys.argv[1:3]; extras=[pathlib.Path(x) for x in sys.argv[3:]]; "
                   "sys.path.insert(0,str(pathlib.Path(pkg).parent)); "
                   "from predictor_v3.utils.jobs import codeship; "
                   "b=codeship.build(pathlib.Path(pkg), **({'extra_pkg_dirs': tuple(extras)} if extras else {})); "
                   "pathlib.Path(out).write_bytes(b.data); print(json.dumps({'sha256':b.sha256,'n':b.n_files,'skipped':list(b.skipped)}))")
        b = subprocess.run([py, "-c", snippet, str(pkg), str(tgz), *map(str, extras)], capture_output=True, text=True, timeout=300,
                           cwd=str(pkg.parent), env=dict(_m_agents.clean_env(), PYTHONPATH=str(pkg.parent)))
        if b.returncode:
            sys.exit("could not pack the task's code (%s): %s" % (", ".join(x.name for x in [pkg] + extras), (b.stderr.strip() or b.stdout.strip())[-400:]))
        info = json.loads(b.stdout.strip().splitlines()[-1])
        new_uri = old.rsplit("/", 1)[0] + "/%s.tgz" % info["sha256"][:16]
        if info["sha256"] == spec["code"].get("sha256"):
            print("the task's code (%s) is identical to what %s already runs (%s); nothing to reship"
                  % (", ".join(x.name for x in [pkg] + extras), j, info["sha256"][:16]))
            return 0
        for src, dst in ((str(tgz), new_uri),):
            u = subprocess.run(_m_task_registry.aws_cmd() + ["s3", "cp", src, dst], capture_output=True, text=True, timeout=300, env=_m_config.aws_env())
            if u.returncode:
                sys.exit("upload of the code tarball failed: %s" % u.stderr.strip()[:200])
        spec["code"] = {"uri": new_uri, "sha256": info["sha256"]}
        u = subprocess.run(_m_task_registry.aws_cmd() + ["s3", "cp", "-", spec_uri], input=json.dumps(spec, sort_keys=True, indent=2),
                           capture_output=True, text=True, timeout=180, env=_m_config.aws_env())
        if u.returncode:
            sys.exit("could not rewrite %s: %s" % (spec_uri, u.stderr.strip()[:200]))
        _m_state.task_txn(n, lambda t: _m_state.tev(t, "reshipped code for %s: %s (%d files; dirs %s) -> %s" % (j, info["sha256"][:16], info["n"], ", ".join(x.name for x in [pkg] + extras), spec_uri)))
        print("reshipped: %s now runs code %s (%d files from %s%s); spec %s rewritten. Resubmit with `nrp-task submit %s --reason ...`."
              % (j, info["sha256"][:16], info["n"], ", ".join(x.name for x in [pkg] + extras), ", left out for size: %s" % ", ".join(info["skipped"]) if info["skipped"] else "", spec_uri, j))
        return 0
    if c == "commit":
        if not t.get("code") or not rest:
            sys.exit("nrp-task commit MESSAGE (task needs a code clone)")
        cl = t["code"]["clone"]
        changed = _m_task_registry.git("status", "--porcelain", cwd=cl).stdout.splitlines()
        py = [l[3:].strip() for l in changed if l[3:].strip().endswith(".py")]
        for f in py:
            r = subprocess.run([sys.executable, "-m", "py_compile", str(Path(cl) / f)], capture_output=True, text=True)
            if r.returncode:
                sys.exit("py_compile failed for %s: %s" % (f, r.stderr.strip()[-300:]))
        if not changed:
            sys.exit("nothing to commit")
        _m_task_registry.git("add", "-A", cwd=cl)
        r = _m_task_registry.git("commit", "-qm", "monitor fix (%s): %s" % (n, " ".join(rest)[:200]), cwd=cl)
        sha = _m_task_registry.git("rev-parse", "--short", "HEAD", cwd=cl).stdout.strip()
        _m_state.task_txn(n, lambda t: _m_state.tev(t, "fix commit %s: %s" % (sha, " ".join(rest)[:150])))
        print("committed %s on %s (%d file(s)); compiled: %s" % (sha, t["code"]["branch"], len(changed), ", ".join(py) or "none"))
        return r.returncode
    if c == "submit":
        j = need_job()
        if "--reason" not in rest or rest.index("--reason") + 1 >= len(rest):
            sys.exit("nrp-task submit JOB --reason 'cause -> fix'")
        ok, msg = _m_task_pass_.do_submit(n, jobs[j]["id"], rest[rest.index("--reason") + 1], "agent")
        print(msg)
        return 0 if ok else 1
    if c == "delete":
        j = need_job()
        st_, f = _m_cluster.job_state(j, ns), t.get("failure") or {}
        util = t.get("util_event") or {}
        util_retry = util.get("job") == j and st_ in ("running", "pending")
        if util_retry:
            evidence = util.get("evidence") or {}
            if util.get("rule") == "gpu":                                 # a GPU under NRP's floor is a policy violation, not a sizing question:
                pass                                                      # stopping it never waits for "time left" or resumability
            elif not _m_timeouts.stage_resumable(jobs[j]) or (util.get("rule") != "nrp" and  # NRP floor: restart whenever it resumes
                                                  (evidence.get("remaining_seconds") or 0) - max(0, _m_state.now() - util.get("ts", _m_state.now())) <= 7200):
                sys.exit("utilization review: leave running Job to finish; resubmit requires resumable stage and >2h measured time left")
            f = util
        if st_ in ("running", "pending") and not (f.get("job") == j and f.get("cls") in ("util", "infra")):
            sys.exit("Job %s is %s; only a finished Job, or one this task's failure says to stop (util/stuck), may be deleted" % (j, st_))
        _m_task_pass_.save_task_logs(t, jobs[j], "deleted by the fix agent")
        rc = kc("delete", "job", j, "--wait=true", "--timeout=180s")
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


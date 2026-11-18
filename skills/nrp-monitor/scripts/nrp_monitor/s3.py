"""NRP monitor s3 (mechanical extraction; R3a)."""
import argparse
import collections
import contextlib
import fcntl
import getpass
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import state as _m_state


def s3_split(uri):
    """(bucket, key) of an s3://bucket/key URI that names ONE object, else None (bucket-only, empty key, or a trailing-slash 'folder')."""
    m = re.match(r"^s3://([^/]+)/(.+)$", uri) if isinstance(uri, str) else None
    return None if not m or m.group(2).endswith("/") else (m.group(1), m.group(2))


def s3_incluster_on():
    """NRP_MONITOR_S3_INCLUSTER: auto (default) = check through one in-cluster Job when the external endpoint fails; off = never."""
    return os.environ.get("NRP_MONITOR_S3_INCLUSTER", "auto").strip().lower() not in ("off", "0", "no", "false", "never")


def s3_check_job_manifest(name, args, script=_m_state.S3_JOB_SCRIPT):
    """Job that runs `bash -c SCRIPT s3check ARGS...` with the in-cluster Ceph endpoint (pods reach it when the laptop cannot reach the public one)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    labels = {"pv3/user": _m_state.OWNER_LABEL, "nrp-monitor/kind": "s3check"}
    return {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": name, "namespace": _m_state.NS, "labels": labels},
            "spec": {"activeDeadlineSeconds": 300, "backoffLimit": 0, "ttlSecondsAfterFinished": 3600,
                     "template": {"metadata": {"labels": labels}, "spec": {
                         "restartPolicy": "Never",
                         "affinity": {"nodeAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": {"nodeSelectorTerms": [
                             {"matchExpressions": [{"key": "kubernetes.io/hostname", "operator": "NotIn", "values": ["nrp-c17.nysernet.org"]}]}]}}},
                         "containers": [{"name": "s3check", "image": _m_state.S3_JOB_IMAGE, "imagePullPolicy": "IfNotPresent",
                                         "command": ["bash", "-c", script, "s3check"] + list(args),
                                         "env": [{"name": "AWS_SHARED_CREDENTIALS_FILE", "value": "/.aws/credentials"},
                                                 {"name": "AWS_CONFIG_FILE", "value": "/.aws/.s3cfg"},
                                                 {"name": "AWS_ENDPOINT_URL", "value": _m_state.S3_JOB_ENDPOINT},
                                                 {"name": "AWS_REQUEST_CHECKSUM_CALCULATION", "value": "when_required"},
                                                 {"name": "AWS_RESPONSE_CHECKSUM_VALIDATION", "value": "when_required"}],
                                         "resources": {"requests": {"cpu": "1", "memory": "512Mi", "ephemeral-storage": "1Gi"},
                                                       "limits": {"cpu": "1", "memory": "512Mi", "ephemeral-storage": "1Gi"}},
                                         "volumeMounts": [{"name": "prp-s3-credentials", "mountPath": "/.aws/credentials", "subPath": "credentials"},
                                                          {"name": "prp-s3-credentials", "mountPath": "/.aws/.s3cfg", "subPath": ".s3cfg"}]}],
                         "volumes": [{"name": "prp-s3-credentials", "secret": {"secretName": "prp-s3-credentials"}}]}}}}


def incluster_job(script, args, log_flag):
    """Run ONE short in-cluster Job (read-only S3 script), wait at most S3_JOB_WAIT_S, return its logs (str) or None when it could not
    be created or gave no logs; the Job is always deleted by name. `log_flag` is the `kubectl logs` size flag, e.g. --tail=60."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    name = "nrpmon-s3check-%s" % uuid.uuid4().hex[:8]
    text = None
    try:
        r = subprocess.run(["kubectl", "-n", _m_state.NS, "create", "-f", "-"], input=json.dumps(s3_check_job_manifest(name, args, script)),
                           capture_output=True, text=True, timeout=60)
        if r.returncode:
            _m_state.log("s3 in-cluster check: could not create Job: %s" % (r.stderr or r.stdout).strip()[-150:])
            return None
        end = time.time() + _m_state.S3_JOB_WAIT_S
        while True:
            g = _m_cluster.kubectl("-n", _m_state.NS, "get", "job", name, "-o", "jsonpath={.status.succeeded}/{.status.failed}", timeout=30)
            ok_, bad_ = (g.stdout.strip().split("/") + ["", ""])[:2] if g.returncode == 0 else ("", "")
            if ok_ not in ("", "0") or bad_ not in ("", "0"):
                break
            if time.time() >= end:
                _m_state.log("s3 in-cluster check: Job %s not finished in %ds" % (name, _m_state.S3_JOB_WAIT_S))
                break
            time.sleep(_m_state.S3_JOB_POLL_S)
        lg = _m_cluster.kubectl("-n", _m_state.NS, "logs", "job/" + name, log_flag, timeout=60)
        text = lg.stdout if lg.returncode == 0 else None
    except Exception as e:
        _m_state.log("s3 in-cluster check: %s: %s" % (type(e).__name__, str(e)[:120]))
    finally:
        try:
            _m_cluster.kubectl("-n", _m_state.NS, "delete", "job", name, "--wait=false", timeout=60)
        except Exception as e:
            _m_state.log("s3 in-cluster check: delete of Job %s failed: %s" % (name, str(e)[:100]))
    _m_state.log("s3 in-cluster Job %s ran (%s)" % (name, "logs read" if text is not None else "no logs"))
    return text


def s3_incluster(uris):
    """{uri: True|False|None} from ONE short in-cluster Job (EXISTS/MISSING/ERROR lines). Anything not answered EXISTS or MISSING stays
    None (callers keep their retry and escalation)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    uris = [u for u in dict.fromkeys(uris) if s3_split(u)]
    res = {u: None for u in uris}
    if not uris:
        return res
    for line in (incluster_job(_m_state.S3_JOB_SCRIPT, uris, "--tail=%d" % (len(uris) + 50)) or "").splitlines():
        w = line.strip().split(" ", 1)
        if len(w) == 2 and w[1] in res and w[0] in ("EXISTS", "MISSING", "ERROR"):
            res[w[1]] = True if w[0] == "EXISTS" else False if w[0] == "MISSING" else None
    _m_state.log("s3 in-cluster check: %d URIs, %d exist, %d missing, %d unanswered" % (
        len(uris), sum(v is True for v in res.values()), sum(v is False for v in res.values()), sum(v is None for v in res.values())))
    return res


def s3_check_many(uris, c=None):
    """{uri: True|False|None}: the external head-object for each; every URI it could not answer (not a 404) goes through ONE in-cluster Job
    (unless NRP_MONITOR_S3_INCLUSTER=off). None is never success."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    out = {u: s3_exists(u, c) for u in dict.fromkeys(uris)}
    todo = [u for u, v in out.items() if v is None and s3_split(u)]
    if todo and s3_incluster_on():
        _m_state.log("s3 external check failed for %d URI(s); falling back to one in-cluster Job" % len(todo))
        _m_state.PASS["s3_incluster"] = _m_state.PASS.get("s3_incluster", 0) + len(todo)
        out.update(s3_incluster(todo))
    return out


def s3_prepass(a):
    """Once per pass, before chains and tasks run: gather the success markers (running stages whose Job finished or vanished) and
    gates (pending stages' after_s3) that will be checked, check them all, and keep the answers in S3_PASS for this pass.
    Only here is the in-cluster fallback used, so a pass makes at most one S3-check Job however many URIs failed."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    _m_state.S3_PASS = {}
    if a.dry_run or not s3_incluster_on():
        return
    want, conf = [], {}
    jobs_ns = {}

    def jobs_of(ns):
        if ns not in jobs_ns:
            try:
                jobs_ns[ns] = _m_cluster.fetch_jobs(ns)
            except Exception:
                jobs_ns[ns] = None
        return jobs_ns[ns]

    for n in [x for x in _m_state.task_names() if (_m_state.task_load(x) or {}).get("status") in _m_state.TASK_LIVE]:
        t = _m_state.task_load(n)
        js = jobs_of(t["namespace"])
        if js is None:
            continue
        for s in t["stages"]:
            if s["state"] == "running" and (js.get(s["job"]) or {"state": "ok"})["state"] == "ok":
                want += s["done_s3"]
            elif s["state"] == "pending" and (s.get("after_s3") or s.get("waiting_on")) and all(_m_state.tstage(t, x)["state"] == "done" for x in s["after"]):
                want += s.get("after_s3", [])
    for u, v in s3_check_many([u for u in dict.fromkeys(want) if s3_split(u)], None).items():
        if v is not None:
            _m_state.S3_PASS[u] = v


def s3_exists(uri, c):
    """EXACT object check: True (this key exists) / False (404 Not Found) / None (could not tell). Fail-closed.
    Uses `aws s3api head-object`, never `aws s3 ls`: `ls s3://b/k` is a PREFIX match, so `.../DONE` was satisfied by `.../DONE.1`
    (and `DONE.1` by `DONE.10`), the monitor declared an Indexed Job finished while shards were still running and deleted its pods
    (finch-feature-followup, 2026-11-06). None = 403/5xx/network/timeout/odd output/a URI that is not one object; callers retry and
    escalate after repeated passes, they never treat None as success. `c` may be {} (aws_profile, s3_endpoint)."""
    from . import config as _m_config  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    c = c or {}
    bk = s3_split(uri)
    if bk is None:
        _m_state.log("s3 head %s: not a single-object s3://bucket/key URI" % uri)
        return None
    if _m_state.S3_PASS is not None and uri in _m_state.S3_PASS:                              # answered earlier in this pass (s3_prepass)
        return _m_state.S3_PASS[uri]
    cmd = ["aws"]
    ep = os.environ.get("NRP_MONITOR_S3_ENDPOINT") or c.get("s3_endpoint") or _m_state.DEFAULT_S3
    if ep:
        cmd += ["--endpoint-url", ep]
    if c.get("aws_profile"):
        cmd += ["--profile", c["aws_profile"]]
    try:
        r = subprocess.run(cmd + ["s3api", "head-object", "--bucket", bk[0], "--key", bk[1], "--output", "json"],
                           capture_output=True, text=True, timeout=120, env=_m_config.aws_env())
    except Exception as e:
        _m_state.log("s3 head %s: %s" % (uri, str(e)[:100]))
        return None
    if r.returncode == 0:
        try:
            if isinstance(json.loads(r.stdout), dict):
                return True
        except ValueError:
            pass
        _m_state.log("s3 head %s rc=0 but unreadable output" % uri)
        return None
    err = r.stderr or ""
    if "(404)" in err and "HeadObject" in err:                            # HEAD has no body: "An error occurred (404) when calling the HeadObject operation: Not Found"
        return False
    _m_state.log("s3 head %s rc=%s %s" % (uri, r.returncode, err.strip()[-100:]))   # 403, 5xx, could not connect, expired token...
    return None


def save_logs(c, s, reason):
    """Last ~200 log lines + describe of the Job and its pods, kept because pods vanish."""
    from . import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    ns, job = c["namespace"], s["job"]
    parts = ["# chain %s step %s job %s  saved %s\n# reason: %s\n" % (c["name"], s["id"], job, _m_state.iso(), reason)]
    for title, args in (("logs (last 200 lines)", ["logs", "job/" + job, "--all-containers", "--tail=200"]),
                        ("describe job", ["describe", "job", job]),
                        ("describe pods", ["describe", "pods", "-l", "job-name=" + job])):
        try:
            r = _m_cluster.kubectl("-n", ns, *args, timeout=120)
            body = (r.stdout if r.returncode == 0 else "(kubectl failed rc=%d: %s)\n%s" % (r.returncode, r.stderr.strip()[:200], r.stdout))
        except Exception as e:
            body = "(kubectl error: %s)" % str(e)[:150]
        parts.append("\n## %s\n%s" % (title, body[-40000:]))
    p = _m_state.CHAINS / c["name"] / "logs" / ("%s.txt" % s["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(parts)[-100000:])
    return str(p)


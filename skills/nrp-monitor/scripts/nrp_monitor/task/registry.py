"""NRP monitor task/registry (mechanical extraction; R3a)."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---- validation ----------------------------------------------------------------------------------------------
def protected_dirs():
    return [(Path.home() / d).resolve() for d in ("Desktop", "Documents", "Downloads")]


def under_protected(path):
    try:
        p = Path(os.path.expanduser(path)).resolve()
    except Exception:
        return None
    for d in protected_dirs():
        if p == d or d in p.parents:
            return d
    return None


def load_chain_file(path):
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    p = Path(path).expanduser()
    if not p.is_file():
        raise _m_state.ChainError("chain file not found: %s" % p)
    if p.stat().st_size > 1024 * 1024:
        raise _m_state.ChainError("chain file over 1 MB")
    text = p.read_text()
    if p.suffix in (".yml", ".yaml"):
        try:
            import yaml
        except ImportError:
            raise _m_state.ChainError("YAML needs PyYAML; use JSON")
        return yaml.safe_load(text), text
    try:
        return json.loads(text), text
    except ValueError as e:
        raise _m_state.ChainError("not valid JSON: %s" % e)

# ---- manifests, S3, code -------------------------------------------------------------------------------------
def manifest_structure(doc):
    """Reject malformed Job trees before any code walks container resources."""
    if not isinstance(doc, dict) or doc.get("kind") != "Job":
        raise ValueError("kind must be Job")
    if not isinstance(doc.get("metadata"), dict):
        raise ValueError("metadata must be a mapping")
    node = doc
    for key in ("spec", "template", "spec"):
        node = node.get(key)
        if not isinstance(node, dict):
            raise ValueError("Job spec.template.spec must contain mappings")
    for key in ("containers", "initContainers"):
        containers = node.get(key, [])
        if not isinstance(containers, list) or (key == "containers" and not containers):
            raise ValueError("%s must be a container list" % key)
        for c in containers:
            if not isinstance(c, dict):
                raise ValueError("container must be a mapping")
            res = c.get("resources", {})
            if not isinstance(res, dict):
                raise ValueError("container resources must be a mapping")
            for field in ("requests", "limits"):
                if field in res and not isinstance(res[field], dict):
                    raise ValueError("container resources.%s must be a mapping" % field)


def manifest_error(path, error):
    mark = getattr(error, "problem_mark", None)
    where = "%s:%d:%d" % (path, mark.line + 1, mark.column + 1) if mark else str(path)
    return "%s: %s: %s" % (where, type(error).__name__, getattr(error, "problem", None) or str(error))


def agent_manifest_checkpoint(n):
    """Durable originals: nrp-task submit runs in a separate process while the agent edits."""
    from .. import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    paths = {s["manifest"] for s in t["stages"] if s.get("manifest")}
    folder = _m_state.task_dir(n) / "manifests"
    paths.update(str(p) for p in folder.glob("*") if p.suffix in (".yaml", ".yml", ".json"))
    originals = {}
    for path in sorted(paths):
        manifest_structure(manifest_doc(path))
        originals[path] = Path(path).read_text()
    _m_notify.write_json(_m_state.task_dir(n) / "agent-manifests.json", originals)
    return originals


def validate_agent_manifests(n, originals=None):
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    checkpoint = _m_state.task_dir(n) / "agent-manifests.json"
    if originals is None:
        originals = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    paths = set(originals) | {s["manifest"] for s in _m_state.task_load(n)["stages"] if s.get("manifest")}
    paths.update(str(p) for p in (_m_state.task_dir(n) / "manifests").glob("*") if p.suffix in (".yaml", ".yml", ".json"))
    errors = []
    for path in sorted(paths):
        try:
            problems = manifest_configmap_problems(path)
            if problems:
                raise ValueError("; ".join(problems))
            manifest_structure(manifest_doc(path))
        except Exception as error:
            detail = manifest_error(path, error)
            if path in originals:
                Path(path).write_text(originals[path])
                detail += " (previous manifest restored)"
            elif Path(path).exists():
                # Preserve evidence without leaving invalid YAML among the accepted manifests.
                Path(path).rename(str(path) + ".rejected")
                detail += " (invalid new manifest quarantined as .rejected)"
            errors.append(detail)
    if errors:
        def record(t):
            t.setdefault("manifest_rejections", []).extend(errors)
            _m_state.tev(t, "manifest edit rejected: " + "; ".join(errors))
        _m_state.task_txn(n, record)
    return errors


CONFIGMAP_DATA_MAX = 16 * 1024
CONFIGMAP_ARCHIVE_SUFFIXES = (".tgz", ".tar", ".tar.gz", ".zip")


def manifest_documents(path):
    text = Path(path).read_text()
    try:
        import yaml
    except ImportError:
        return [json.loads(text)]
    return [doc for doc in yaml.safe_load_all(text) if doc]


def configmap_problems(doc):
    if not isinstance(doc, dict):
        return []
    if str(doc.get("kind", "")).endswith("List"):
        return [problem for item in doc.get("items") or []
                for problem in configmap_problems(item)]
    if doc.get("kind") != "ConfigMap":
        return []
    name = (doc.get("metadata") or {}).get("name", "<unnamed>")
    fields = {key: doc.get(key) or {} for key in ("data", "binaryData")}
    for key, values in fields.items():
        if not isinstance(values, dict):
            return ["ConfigMap %s: %s must be a mapping" % (name, key)]
    for values in fields.values():
        for key in values:
            if str(key).lower().endswith(CONFIGMAP_ARCHIVE_SUFFIXES):
                return ["ConfigMap %s contains archive key %s. Use nrp-task ship." % (name, key)]
    if len(json.dumps(fields, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")) > CONFIGMAP_DATA_MAX:
        return ["ConfigMap %s exceeds %d KiB of serialized data and binaryData. Use nrp-task ship."
                % (name, CONFIGMAP_DATA_MAX // 1024)]
    return []


def manifest_configmap_problems(path):
    return [problem for doc in manifest_documents(path) for problem in configmap_problems(doc)]


def manifest_check(path, ns, job):
    """Parse one Job manifest (YAML/JSON) and check the NRP house rules. Returns a list of problems."""
    try:
        docs = manifest_documents(path)
        problems = [problem for doc in docs for problem in configmap_problems(doc)]
    except Exception as e:
        return ["cannot read manifest %s: %s" % (path, str(e)[:120])]
    if problems:
        return problems
    if len(docs) != 1 or not isinstance(docs[0], dict):
        return ["%s: exactly one Job per manifest file" % path]
    try:
        manifest_structure(docs[0])
    except ValueError as e:
        return [manifest_error(path, e)]
    j, bad = docs[0], []
    md, spec = j.get("metadata") or {}, j.get("spec") or {}
    if j.get("kind") != "Job":
        bad.append("kind must be Job (Jobs only: no bare pods or Deployments)")
    if md.get("name") != job:
        bad.append("metadata.name is %r, the stage's job is %r" % (md.get("name"), job))
    if md.get("namespace") not in (None, ns):
        bad.append("namespace must be %s" % ns)
    if spec.get("backoffLimit") != 0:
        bad.append("spec.backoffLimit must be 0")
    if not spec.get("activeDeadlineSeconds"):
        bad.append("spec.activeDeadlineSeconds required (it counts queue time: include the expected wait)")
    ttl = spec.get("ttlSecondsAfterFinished")
    if ttl is not None and ttl < 3600:
        bad.append("ttlSecondsAfterFinished %s: at least 3600, so the monitor sees the Job finish and saves its logs" % ttl)
    pod = ((spec.get("template") or {}).get("spec")) or {}
    if pod.get("restartPolicy") not in ("Never", "OnFailure"):
        bad.append("template.spec.restartPolicy must be Never")
    for c in pod.get("containers") or []:
        res = c.get("resources") or {}
        if not res.get("requests") and not res.get("limits"):
            bad.append("container %s: resources.requests required" % c.get("name"))
        cmdtxt = " ".join(map(str, (c.get("command") or []) + (c.get("args") or [])))
        if re.search(r"\bsleep\s+(inf|infinity|\d{4,})\b", cmdtxt):
            bad.append("container %s: no long sleep (an idle pod is an NRP violation)" % c.get("name"))
    return bad


def manifest_gpu(path):
    """GPUs requested by the first container of a manifest (0 when none or unreadable)."""
    try:
        text = Path(path).read_text()
        try:
            import yaml
            j = yaml.safe_load(text)
        except ImportError:
            j = json.loads(text)
        n = 0
        for c in j["spec"]["template"]["spec"]["containers"]:
            r = c.get("resources") or {}
            for k in ("requests", "limits"):
                n = max(n, int(str((r.get(k) or {}).get("nvidia.com/gpu", 0)) or 0))
        return n
    except Exception:
        return 0


def gpu_expired(s):
    """None, or the reason a stage that asks for a GPU may not be (re)submitted today. the owner's GPU OK is per day; a stage
    declares the last day it covers in `gpu_ok_until` (YYYY-MM-DD) and the monitor never submits a GPU Job after it."""
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not s.get("manifest") or not manifest_gpu(s["manifest"]):
        return None
    if s.get("gpu_plan"):                            # covered by the approval date of an approved plan step (see plan_gpu_cover)
        return None
    until = s.get("gpu_ok_until")
    if not until:
        return "GPU APPROVAL: stage %s requests a GPU but has no gpu_ok_until date" % s["id"]
    if _m_state.today_iso() > until:
        return "GPU APPROVAL: the owner's GPU OK for stage %s ran through %s (today %s); a GPU retry needs their new OK " \
               "(`nrp-monitor task resume NAME --gpu-ok-until YYYY-MM-DD`)" % (s["id"], until, _m_state.today_iso())
    return None


def pv3_spec_uri(path):
    """The `--spec s3://...` argument of a pv3 Job's command, or None."""
    try:
        text = Path(path).read_text()
        try:
            import yaml
            j = yaml.safe_load(text)
        except ImportError:
            j = json.loads(text)
        c = j["spec"]["template"]["spec"]["containers"][0]
        argv = [str(x) for x in (c.get("command") or []) + (c.get("args") or [])]
        return next((argv[i + 1] for i, x in enumerate(argv[:-1]) if x == "--spec" and argv[i + 1].startswith("s3://")), None)
    except Exception:
        return None


def manifest_mem(t, s):
    try:
        import yaml
        j = yaml.safe_load(Path(s["manifest"]).read_text())
        c = j["spec"]["template"]["spec"]["containers"][0]["resources"]
        return str((c.get("limits") or {}).get("memory") or (c.get("requests") or {}).get("memory") or "?")
    except Exception:
        return "?"


def aws_cmd(c=None):
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    cmd = ["aws", "--endpoint-url", os.environ.get("NRP_MONITOR_S3_ENDPOINT") or (c or {}).get("s3_endpoint") or _m_state.DEFAULT_S3]
    if (c or {}).get("aws_profile"):
        cmd += ["--profile", c["aws_profile"]]
    return cmd


def s3_bucket_ok(bucket):
    from .. import config as _m_config  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        r = subprocess.run(aws_cmd() + ["s3", "ls", "s3://%s/" % bucket], capture_output=True, text=True, timeout=120, env=_m_config.aws_env())
    except Exception:
        return None
    if "NoSuchBucket" in r.stderr or "AccessDenied" in r.stderr:
        return False
    return True if r.returncode in (0, 1) else None


def git(*args, cwd=None, inp=None):
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return subprocess.run(["git", *_m_state.GIT_ID, *args], cwd=cwd, capture_output=True, text=True, input=inp, timeout=600)


def clone_code(name, code, warn):
    """Clone the repo at a commit into ~/.cache/nrp-tasks/<task>/repo (launchd can read there, not ~/Desktop),
    on branch monitor/<task>; uncommitted tracked changes under subdir are applied and committed."""
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    repo = Path(os.path.expanduser(code["repo"])).resolve()
    sub = (code.get("subdir") or "").strip("/")
    restore_parent_clone(repo)
    r = git("rev-parse", "--show-toplevel", cwd=str(repo))
    if r.returncode:
        raise _m_state.ChainError("code.repo %s is not a git repository" % repo)
    top = Path(r.stdout.strip())
    given = repo
    if repo != top:                                                   # repo given as a subfolder
        sub = str((repo / sub).relative_to(top)).strip(".").strip("/") if sub else str(repo.relative_to(top))
        repo = top
    r = git("rev-parse", "--verify", (code.get("commit") or "HEAD") + "^{commit}", cwd=str(repo))
    if r.returncode:
        raise _m_state.ChainError("code.commit %s not found in %s" % (code.get("commit"), repo))
    sha = r.stdout.strip()
    extras, shipped_extras = [], []                                   # code dirs the task ships besides subdir: in this repo / as declared
    for x in code.get("extra_pkg_dirs") or []:
        if os.path.isabs(os.path.expanduser(x)):
            shipped_extras.append(str(Path(x).expanduser()))             # another checkout: packed in place at reship, not cloned
        else:
            rel = str((given / x).relative_to(top)).strip(".").strip("/") if given != top else x.strip("/")
            extras.append(rel)
            shipped_extras.append(rel)
    scope = [x for x in ([sub] + extras if sub else []) if x] or ["."]
    if not sub and not code.get("full_checkout"):                    # whole-repo clones were most of the task cache's disk
        size = checkout_bytes(repo, sha)
        if size > _m_state.CLONE_FULL_MAX:
            raise _m_state.ChainError(
                "code.subdir is not set, so the task would check out all of %s (%d MiB at %s; limit %d MiB). Set code.subdir to the folder "
                "the task runs from (and code.extra_pkg_dirs for other code it ships), or code.full_checkout: true if it really needs the "
                "whole repo" % (repo, size >> 20, sha[:10], _m_state.CLONE_FULL_MAX >> 20))
    dest = _m_state.TASK_CACHE / name / "repo"
    checkout_into(repo, dest, scope if sub else None, "monitor/" + name, sha)
    if not code.get("commit"):
        diff = git("diff", "HEAD", "--binary", "--", *scope, cwd=str(repo)).stdout
        if diff.strip():
            a = git("apply", "--whitespace=nowarn", "-", cwd=str(dest), inp=diff)
            if a.returncode:
                raise _m_state.ChainError("could not carry uncommitted changes into the clone: %s" % a.stderr.strip()[:200])
            git("add", "-A", cwd=str(dest))
            git("commit", "-qm", "uncommitted state of %s at task add" % repo, cwd=str(dest))
            warn.append("uncommitted changes under %s were committed in the clone" % (sub or repo))
        copied, skipped, total = [], [], 0
        for rel in git("ls-files", "-z", "--others", "--exclude-standard", "--", *scope, cwd=str(repo)).stdout.split("\0"):
            src = repo / rel
            if not rel or not src.is_file():
                continue
            if src.suffix not in _m_state.CLONE_SUFFIXES or src.stat().st_size > _m_state.CLONE_MAX_FILE or total + src.stat().st_size > _m_state.CODE_SNAPSHOT_MAX:
                skipped.append(rel)
                continue
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest / rel)
            total += src.stat().st_size
            copied.append(rel)
        if copied:
            git("add", "-A", cwd=str(dest))
            git("commit", "-qm", "untracked source files at task add (%d)" % len(copied), cwd=str(dest))
            warn.append("%d untracked source file(s) under %s were copied into the clone and committed (e.g. %s)"
                        % (len(copied), sub or repo, copied[0]))
        if skipped:
            warn.append("%d untracked file(s) under %s are NOT in the clone (not source or over %d MiB; e.g. %s); commit them or set code.commit"
                        % (len(skipped), sub or repo, _m_state.CLONE_MAX_FILE >> 20, skipped[0]))
    out = {"repo": str(repo), "base": sha, "clone": str(dest), "branch": "monitor/" + name, "subdir": sub,
           "snapshot": git("rev-parse", "HEAD", cwd=str(dest)).stdout.strip()}         # past here = commits a fixer made, not task-add copies
    if code.get("full_checkout"):
        out["full_checkout"] = True
    if code.get("pkg_dir"):
        out["pkg_dir"] = code["pkg_dir"]
    if shipped_extras:
        out["extra_pkg_dirs"] = shipped_extras
    return out


def checkout_bytes(repo, sha):
    """Sum of blob sizes a full checkout of sha would write (git ls-tree -r -l)."""
    r = git("ls-tree", "-r", "-l", sha, cwd=str(repo))
    return sum(int(f[3]) for f in (l.split(None, 4) for l in r.stdout.splitlines()) if len(f) > 3 and f[3].isdigit())


def checkout_into(repo, dest, scope, branch, sha):
    """Fresh clone of repo at sha on branch into dest; scope = sparse cone dirs, None = whole tree."""
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = git("clone", "-q", "--no-checkout", str(repo), str(dest))
    if r.returncode:
        raise _m_state.ChainError("git clone failed: %s" % r.stderr.strip()[:200])
    if scope:
        git("sparse-checkout", "set", "--cone", *scope, cwd=str(dest))
    r = git("checkout", "-q", "-B", branch, sha, cwd=str(dest))
    if r.returncode:
        raise _m_state.ChainError("git checkout failed: %s" % r.stderr.strip()[:200])


def restore_parent_clone(path, depth=0):
    """A repo path inside another task's pruned clone (continuations, plan TASK files): rebuild that clone first."""
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    path = Path(path)
    cache = _m_state.TASK_CACHE.resolve() if _m_state.TASK_CACHE.exists() else _m_state.TASK_CACHE
    if path.exists() or not path.is_relative_to(cache) or path == cache or depth >= 20:
        return
    parent = _m_state.task_load(path.relative_to(cache).parts[0])
    if parent and parent.get("code"):
        ensure_clone(parent, depth + 1)


def ensure_clone(t, depth=0):
    """Rebuild a pruned task clone: code.repo at code.base with the same sparse scope, then the task's saved commits
    (TASKS/<task>/code.bundle) on its branch. Returns the clone path; raises ChainError when it cannot."""
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    code = t["code"]
    dest = Path(code["clone"])
    if (dest / ".git").exists():
        return dest
    repo = Path(code["repo"])
    restore_parent_clone(repo, depth)                                 # a continuation's repo is its parent's (maybe pruned) clone
    if not repo.exists():
        raise _m_state.ChainError("cannot restore the clone of %s: its source repo %s is gone" % (t["name"], repo))
    sub = (code.get("subdir") or "").strip("/")
    extras = [x.strip("/") for x in code.get("extra_pkg_dirs") or [] if not os.path.isabs(os.path.expanduser(x))]
    checkout_into(repo, dest, [x for x in [sub] + extras if x] if sub else None, code["branch"], code["base"])
    bundle = _m_state.task_dir(t["name"]) / "code.bundle"
    if bundle.exists():
        r = git("fetch", "-q", str(bundle), code["branch"], cwd=str(dest))
        if r.returncode or git("reset", "-q", "--hard", "FETCH_HEAD", cwd=str(dest)).returncode:
            shutil.rmtree(dest.parent, ignore_errors=True)
            raise _m_state.ChainError("cannot restore the clone of %s from %s: %s" % (t["name"], bundle, r.stderr.strip()[:200]))
    _m_state.log("task %s: clone restored at %s" % (t["name"], dest))
    return dest


def code_dir_problem(x, what):
    """None, or why `x` cannot be a code dir: relative = inside the task's repo (no `..`), absolute / `~` = another git checkout."""
    if not isinstance(x, str) or not x.strip() or "\0" in x:
        return "%s: a folder path" % what
    p = Path(os.path.expanduser(x))
    if p.is_absolute():
        return None if p.is_dir() else "%s: %s is not a folder" % (what, x)
    if ".." in Path(x).parts:
        return "%s: %s must stay inside the code repo (no ..); use an absolute path for another checkout" % (what, x)
    return None


def code_dirs_check(code):
    """Problems with code.pkg_dir / code.extra_pkg_dirs (what `nrp-task reship` packs besides the clone's own package)."""
    bad = []
    if code.get("pkg_dir") is not None:
        pr = code_dir_problem(code["pkg_dir"], "code.pkg_dir")
        bad += [pr] if pr else []
    ex = code.get("extra_pkg_dirs")
    if ex is not None:
        if not isinstance(ex, list) or len(ex) > 8:
            bad.append("code.extra_pkg_dirs: a list of at most 8 package folders")
        else:
            for i, x in enumerate(ex):
                pr = code_dir_problem(x, "code.extra_pkg_dirs[%d]" % i)
                if pr:
                    bad.append(pr)
            names = [Path(os.path.expanduser(x)).name for x in ex if isinstance(x, str)]
            if len(set(names)) != len(names) or not all(n.isidentifier() for n in names):
                bad.append("code.extra_pkg_dirs: each folder name must be a distinct Python package name (it is the top-level folder in the shipped tarball)")
    return bad

# ---- task add / validate ---------------------------------------------------------------------------------------
def validate_task(raw, warn, plan_gpu=None):
    from .. import config as _m_config  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import s3 as _m_s3  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import tier0 as _m_tier0  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    bad = []
    if not isinstance(raw, dict):
        raise _m_state.ChainError("top level must be an object")
    name = raw.get("name")
    if not isinstance(name, str) or not _m_state.TASK_RE.match(name):
        bad.append("name: lowercase letters, digits and -, max 40")
    for k in ("goal", "approved"):
        if not isinstance(raw.get(k), str) or len(raw[k].strip()) < 8:
            bad.append("%s: required (approved = the owner's words and the date he approved the task)" % k)
    mode = raw.get("mode", "auto")
    if mode not in ("auto", "watch"):
        bad.append("mode: auto (default: agents debug and resubmit) or watch (any failure goes to the owner)")
    notes = raw.get("notes", "")
    if not isinstance(notes, str) or len(notes.encode()) > 4096:
        bad.append("notes: text, at most 4 KB (what a fresh agent needs: how the job works, what a good result looks like)")
    ns = raw.get("namespace", _m_state.NS)
    mr = raw.get("max_retries", _m_decisions.scaled_retry_cap(raw.get("stages") or []))
    if not isinstance(mr, int) or isinstance(mr, bool) or mr < 0:
        bad.append("max_retries: nonnegative integer")
    postcheck = raw.get("postcheck")
    if postcheck is not None:
        if (not isinstance(postcheck, dict) or not isinstance(postcheck.get("cmd"), list)
                or not postcheck["cmd"] or not all(isinstance(x, str) and x for x in postcheck["cmd"])
                or not isinstance(postcheck.get("expect"), str) or not postcheck["expect"]):
            bad.append("postcheck: {cmd: [exact local read-only checker argv], expect: nonempty text}")
    code = raw.get("code")
    if code is not None and (not isinstance(code, dict) or not isinstance(code.get("repo"), str)):
        bad.append("code: {repo: path, commit?: sha, subdir?: path, pkg_dir?: path, extra_pkg_dirs?: [path]}")
        code = None
    if code is not None:
        bad += code_dirs_check(code)
    fol = raw.get("followup", "")
    if not isinstance(fol, str) or len(fol.encode()) > 2048:
        bad.append("followup: text, at most 2 KB (what a read-only agent reports when the task is done)")
    try:
        origin = _m_wake.norm_origin(raw.get("origin"))
    except _m_state.ChainError as e:
        origin = None
        bad.append(str(e))
    steps = raw.get("stages")
    if not isinstance(steps, list) or not steps:
        raise _m_state.ChainError("; ".join(bad + ["stages: non-empty list required"]))
    stages, ids, buckets = [], set(), set()
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            bad.append("stages[%d]: object" % i)
            continue
        sid = s.get("id") or s.get("job")
        w = "stage %s" % sid
        job = s.get("job")
        if not isinstance(job, str) or not _m_state.JOB_RE.match(job) or len(job) > 63:
            bad.append("%s: job must be a DNS-1123 name" % w)
        if sid in ids:
            bad.append("%s: duplicate id" % w)
        ids.add(sid)
        st0 = s.get("state", "pending")
        if st0 not in ("pending", "running", "done"):
            bad.append("%s: state pending|running|done" % w)
        d3 = s.get("done_s3")
        if not isinstance(d3, list) or not d3 or not all(_m_s3.s3_split(x) for x in d3):
            bad.append("%s: done_s3 = full s3://bucket/key URIs of single objects (no trailing slash; checked EXACTLY, never as a prefix) "
                       "that exist only when the stage succeeded (the success check)" % w)
            d3 = []
        buckets |= {x[5:].split("/")[0] for x in d3}
        m = s.get("manifest")
        if st0 != "done" and (mode == "auto" or st0 == "pending"):
            if not isinstance(m, str) or not os.path.isfile(os.path.expanduser(m)):
                bad.append("%s: manifest (path to the Job yaml) required and must exist" % w)
            else:
                bad += ["%s: %s" % (w, p) for p in manifest_check(os.path.expanduser(m), ns, job)]
        elif isinstance(m, str) and os.path.isfile(os.path.expanduser(m)):
            try:
                bad += ["%s: %s" % (w, p) for p in manifest_configmap_problems(os.path.expanduser(m))]
            except Exception as e:
                bad.append("%s: %s" % (w, manifest_error(m, e)))
        purpose = str(s.get("purpose") or s.get("type") or s.get("kind") or sid).lower()
        smoke = s.get("smoke") is True or s.get("profile") is True or purpose in ("smoke", "profile")
        if smoke and isinstance(m, str) and os.path.isfile(os.path.expanduser(m)):
            try:
                spec = manifest_doc(os.path.expanduser(m))["spec"]
                counts = [spec.get(k, 1) for k in ("parallelism", "completions")]
                cap = _m_config.util_policy().get("smoke_max_jobs", 3)
                if any(not isinstance(v, int) or isinstance(v, bool) or v < 1 for v in counts) or max(counts) > cap:
                    bad.append("%s: smoke/profile parallelism and completions must be 1..%d (smoke_max_jobs); include the largest/longest item" % (w, cap))
            except (OSError, ValueError, KeyError, TypeError):
                bad.append("%s: cannot determine smoke/profile pod count" % w)
        after = s.get("after", [])
        if not isinstance(after, list):
            bad.append("%s: after = list of stage ids" % w)
            after = []
        a3 = s.get("after_s3", [])
        if not isinstance(a3, list) or not all(_m_s3.s3_split(x) for x in a3):
            bad.append("%s: after_s3 = list of full s3://bucket/key URIs that must all exist before the stage is submitted "
                       "(a gate on another task's success marker)" % w)
            a3 = []
        elif set(a3) & set(d3):
            bad.append("%s: after_s3 repeats one of the stage's own done_s3 URIs (it would never be submitted)" % w)
        buckets |= {x[5:].split("/")[0] for x in a3}
        gok = s.get("gpu_ok_until")
        if gok is not None and not (isinstance(gok, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", gok)):
            bad.append("%s: gpu_ok_until = YYYY-MM-DD (the last day of the owner's GPU OK)" % w)
            gok = None
        res = s.get("resumable")
        if res is not None and not isinstance(res, bool):
            bad.append("%s: resumable = true only when re-running the stage skips items whose outputs already exist (Tier 0 then resubmits it once with 2x deadline after a timeout)" % w)
            res = None
        stage = {"id": sid, "job": job, "manifest": os.path.expanduser(m) if isinstance(m, str) else None,
                 "after": after, "done_s3": d3, "state": st0, "attempt": 1}
        if "resource_group" in s:
            if isinstance(s["resource_group"], str) and s["resource_group"].strip():
                stage["resource_group"] = s["resource_group"]
            else:
                bad.append("%s: resource_group must be a nonempty string asserting compatible resource templates" % w)
        if "queue_wait_ceiling" in s:
            try:
                _m_tier0.queue_ceiling_seconds(s["queue_wait_ceiling"])
                stage["queue_wait_ceiling"] = s["queue_wait_ceiling"]
            except ValueError:
                bad.append("%s: queue_wait_ceiling must be a positive duration like 6h" % w)
        if "cpu_fallback" in s:
            fallback = s["cpu_fallback"]
            if not ((isinstance(fallback, str) and fallback.strip()) or (isinstance(fallback, dict) and fallback)):
                bad.append("%s: cpu_fallback must be a manifest path or resources override" % w)
            else:
                stage["cpu_fallback"] = fallback
        runtime = s.get("measured_runtime_seconds")
        if runtime is not None:
            if isinstance(runtime, (int, float)) and not isinstance(runtime, bool) and runtime > 0:
                stage["measured_runtime_seconds"] = runtime
            else:
                bad.append("%s: measured_runtime_seconds must be a positive measured stage runtime" % w)
        if smoke:
            stage["purpose"] = "profile" if purpose == "profile" or s.get("profile") else "smoke"
        if res:
            stage["resumable"] = True
        if a3:
            stage["after_s3"] = a3
        if gok:
            stage["gpu_ok_until"] = gok
        if st0 != "done" and stage["manifest"] and os.path.isfile(stage["manifest"]) and manifest_gpu(stage["manifest"]) and plan_gpu:
            stage["gpu_plan"] = plan_gpu                   # an approved plan step: the owner's approval of the plan is the GPU OK
        elif st0 != "done" and stage["manifest"] and os.path.isfile(stage["manifest"]) and manifest_gpu(stage["manifest"]):
            if not gok:
                bad.append("%s: the manifest requests a GPU, so gpu_ok_until (YYYY-MM-DD, last day of the owner's GPU OK) is required" % w)
            elif gok < _m_state.today_iso():
                bad.append("%s: gpu_ok_until %s is already past (today %s)" % (w, gok, _m_state.today_iso()))
        stages.append(stage)
    for s in stages:
        for x in s["after"]:
            if x not in ids:
                bad.append("stage %s: after refers to unknown stage %s" % (s["id"], x))
    for b in sorted(buckets):
        ok = s3_bucket_ok(b)
        if ok is False:
            bad.append("bucket %s does not exist or is not readable (outputs must name the real bucket, e.g. braingeneersdev)" % b)
        elif ok is None:
            warn.append("could not check bucket %s" % b)
    if bad:
        raise _m_state.ChainError("\n  - ".join(["%d problem(s):" % len(bad)] + bad))
    return {"name": name, "goal": raw["goal"].strip(), "approved": raw["approved"].strip(), "label": str(raw.get("label") or name)[:80],
            "namespace": ns, "mode": mode, "notes": notes, "max_retries": mr, "followup": fol, "code": code, "origin": origin,
            "group": raw.get("group"), "postcheck": postcheck, "stages": stages, "status": "running", "attempts": [], "failure": None, "created": _m_state.now(), "events": [],
            "escalations": 0, "util": [], "agent_runs": []}


def cmd_task_add(a):
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        raw = load_chain_file(a.file)[0]
        if isinstance(raw, dict):
            raw["origin"] = _m_wake.origin_overlay(raw.get("origin"), a)
    except _m_state.ChainError as e:
        sys.exit("task refused: %s" % e)
    return task_add_raw(raw, a.file, by="session")


def task_add_raw(raw, src_file, by="session", parent=None):
    """Register a task. by = "session" (a person or chat: `task add`) or "continuation" (the plan agent, via `nrp-task next-add`)."""
    from .. import cluster as _m_cluster  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import plans as _m_plans  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import s3 as _m_s3  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .. import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    warn = []
    try:
        od_raw = raw.pop("on_done", None) if isinstance(raw, dict) else None
        dig = raw.pop("digest_only", None) if isinstance(raw, dict) else None
        hp = raw.pop("handoff", None) if isinstance(raw, dict) else None
        if dig is not None and (not isinstance(dig, str) or not 8 <= len(dig.strip()) <= 300):
            raise _m_state.ChainError("digest_only: why nobody needs to look at the result (8-300 characters); it turns off the completion wake")
        od = _m_plans.check_on_done(od_raw, raw, src_file, by, parent) if od_raw is not None else None   # refuses unapproved / stop steps first
        if od:
            h = _m_plans.plan_header(od["plan"])
            if raw.get("group") is not None and not isinstance(raw["group"], str):
                raise _m_state.ChainError("group: a declared group name")
            group = raw.get("group") or next((g for g, steps in h.get("groups", {}).items() if od["from_step"] in steps), None)
            if group and group not in h.get("groups", {}):
                raise _m_state.ChainError("group: unknown plan group")
            raw["group"] = group
            if group in h.get("retries", {}) and "max_retries" not in raw:
                raw["max_retries"] = h["retries"][group]
        t = validate_task(raw, warn, plan_gpu=_m_plans.plan_gpu_cover(od))
    except _m_state.ChainError as e:
        sys.exit("task refused: %s" % e)
    if od:
        t["on_done"] = od
    n = t["name"]
    if dig:
        t["digest_only"] = dig.strip()
    if not od and not t.get("followup") and not dig:
        msg = ("no continuation: when this task finishes the coordinator chat is woken with no plan step to check. Add "
               "\"on_done\": {\"plan\": \"PATH#ID\", \"from_step\": \"N\"} (wakes the chat; never passes a named stop), "
               "\"followup\" for a one-shot report, or \"digest_only\": \"why nobody needs to look at the result\" (turns off the wake).")
        if os.environ.get("NRP_MONITOR_REQUIRE_CONTINUATION"):
            sys.exit("task refused: " + msg)
        warn.append(msg)
    try:
        htext, hthin, hwhy = _m_wake.handoff_load(hp, src_file)
    except _m_state.ChainError as e:
        sys.exit("task refused: %s" % e)
    if htext is None or hthin:
        msg = ("no handoff: %s, so the agents that fix or continue this task later start with only the task fields. After the monitor is "
               "started, write the handoff from templates/handoff.md (`## Registrar`: what is being done and why, what each stage produces, "
               "what to check, decisions made, what NOT to do, where the code and outputs are) and set \"handoff\": \"PATH\" in the task file."
               % hwhy)
        if os.environ.get("NRP_MONITOR_REQUIRE_HANDOFF") and by == "session":     # a continue agent registering the next step is only warned
            sys.exit("task refused: " + msg)
        warn.append(msg)
    if htext is not None and not hthin and _m_wake.handoff_escalation_missing(htext):
        warn.append("the handoff does not say how failures are handled. " + _m_state.HANDOFF_ESC_ASK)
    # v3: a task registered by a person/chat must name its chat (ft-tables-w6 had none, so its alert woke nobody). A continuation
    # inherits its parent's origin, so one without is only warned about (refusing would strand the approved plan).
    _m_wake.require_origin_note(t["origin"], "task", n, always=(by == "session"))
    with _m_state.state_lock():
        if _m_state.task_load(n) and _m_state.task_load(n)["status"] not in ("done", "cancelled"):
            sys.exit("task %s already exists and is %s (`nrp-monitor task show %s`)" % (n, _m_state.task_load(n)["status"], n))
        busy = {}
        for o in _m_state.task_names():
            ot = _m_state.task_load(o)
            if o != n and ot and ot["status"] in _m_state.TASK_LIVE + _m_state.TASK_HELD:
                busy.update({s["job"]: o for s in ot["stages"] if s["state"] != "done"})
        dup = [s["job"] for s in t["stages"] if s["job"] in busy]
        if dup:
            sys.exit("task refused: Job %s already belongs to %s" % (dup[0], busy[dup[0]]))
    if t["code"]:
        try:
            t["code"] = clone_code(n, t["code"], warn)
        except _m_state.ChainError as e:
            sys.exit("task refused: %s" % e)
    d = _m_state.task_dir(n)
    shutil.rmtree(d, ignore_errors=True)
    (d / "manifests").mkdir(parents=True)
    (d / "logs").mkdir()
    for s in t["stages"]:
        if s["manifest"]:
            dst = d / "manifests" / ("%s.yaml" % s["job"])
            shutil.copyfile(s["manifest"], dst)
            s["manifest"] = str(dst)
        if s["state"] == "running":
            s["submitted"] = _m_state.now()
            if _m_cluster.job_state(s["job"], t["namespace"]) == "missing":
                warn.append("stage %s is marked running but Job %s is not in the cluster yet" % (s["id"], s["job"]))
        for u in s["done_s3"]:
            if s["state"] != "done" and _m_s3.s3_exists(u, {}) is True:
                warn.append("stage %s: %s ALREADY exists, so the success check would pass on old output; prefer a fresh prefix" % (s["id"], u))
    (d / "task.src").write_text(Path(src_file).expanduser().read_text())
    if htext is not None:
        _m_wake.handoff_attach(t, htext, hthin, _m_wake.handoff_path(hp, src_file))
    _m_state.tev(t, "added (mode %s, %d stages, max %d retries)" % (t["mode"], len(t["stages"]), t["max_retries"]))
    if od:
        _m_state.tev(t, "plan %s step %s (registered by %s%s)" % (od["plan"], od["from_step"], by, ", after task " + parent if parent else ""))
    with _m_state.state_lock():
        if od and _m_plans.plan_state(od["plan"])["status"] == "closed":
            sys.exit("task refused: plan %s is closed" % od["plan"])
        _m_state.task_write(t)
    agent_manifest_checkpoint(n)
    if od:
        _m_plans.ledger_add(od["plan"], od["from_step"], n, by, parent)
    for w in warn:
        print("warning: " + w, file=sys.stderr)
    _m_notify.digest("added", "%s: %s | %s" % (t["label"], t["goal"][:150], _m_wake.origin_plain(t["origin"])), n)
    print("task %s added (%s, %s): %d stage(s). The monitor submits pending stages, checks done_s3, retries failures with a "
          "fresh agent and pushes to the owner only when it needs them.%s" % (n, t["mode"], _m_wake.origin_plain(t["origin"]), len(t["stages"]),
          " Code clone: %s (branch %s)." % (t["code"]["clone"], t["code"]["branch"]) if t["code"] else ""))
    tgt = _m_wake.wake_target(t)
    print("Wake: %s. The monitor wakes that same chat (never a new thread) once per finished plan step and, as a last resort, when its own "
          "subagents cannot fix a failure; nothing else wakes it." % (
          {"t3": "T3 webhook relay", "t3-cli": "T3 CLI thread %s" % (tgt or {}).get("session"), "claude": "Claude Code session %s" % (tgt or {}).get("session"),
           "codex": "Codex session %s" % (tgt or {}).get("session")}[tgt["harness"]] if tgt else
           "NO wake target (no webhook, no --origin-harness/--origin-session): a failure that needs the chat goes to the owner instead"))
    if htext is None or hthin or _m_wake.handoff_escalation_missing(htext):
        print("HANDOFF: " + _m_state.HANDOFF_ESC_ASK + " Attach it with `nrp-monitor task handoff %s FILE` (templates/handoff.md)." % n)
    return 0


def manifest_doc(path):
    text = Path(path).read_text()
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:
        return json.loads(text)


def manifest_write(path, doc):
    manifest_structure(doc)  # validate before replacing the previously accepted bytes
    try:
        import yaml
        Path(path).write_text(yaml.safe_dump(doc, sort_keys=False))
    except ImportError:
        Path(path).write_text(json.dumps(doc, indent=2))


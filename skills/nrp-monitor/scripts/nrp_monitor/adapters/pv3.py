"""Legacy project shipping adapter.

2026-11-25: Remove once the registration scan in references/tasks.md reports no users.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import agents as _m_agents
from .. import config as _m_config
from .. import state as _m_state
from ..task import registry as _m_task_registry


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


def spec_uri(path):
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


def matches(code, manifest=None):
    if any(Path(code.get(key) or ".").name == "predictor_v3" for key in ("pkg_dir", "subdir")):
        return True
    if manifest:
        uri = spec_uri(manifest)
        return bool(uri and ("/pv3/" in uri or (
            uri.endswith("/spec.json") and "predictor_v3.utils.jobs.entry" in Path(manifest).read_text()
        )))
    return False


def reship(n, j, manifest, code, upload):
    uri = spec_uri(manifest)
    if not uri:
        sys.exit("Job %s does not run from an S3 spec (no `--spec s3://...` in its command): nothing to reship" % j)
    try:
        pkg, extras = reship_dirs(code)
    except _m_state.ChainError as e:
        sys.exit("reship refused: %s" % e)
    r = subprocess.run(_m_task_registry.aws_cmd() + ["s3", "cp", uri, "-"], capture_output=True, text=True, timeout=180, env=_m_config.aws_env())
    try:
        spec = json.loads(r.stdout)
        old = spec["code"]["uri"]
    except Exception:
        sys.exit("cannot read %s with a `code` entry (aws rc=%d %s)" % (uri, r.returncode, r.stderr.strip()[:150]))
    with tempfile.TemporaryDirectory(prefix="nrp-legacy-ship-") as tmp:
        tgz = Path(tmp) / "code.tgz"
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
        upload(tgz, new_uri)
        spec["code"] = {"uri": new_uri, "sha256": info["sha256"]}
        u = subprocess.run(_m_task_registry.aws_cmd() + ["s3", "cp", "-", uri], input=json.dumps(spec, sort_keys=True, indent=2),
                           capture_output=True, text=True, timeout=180, env=_m_config.aws_env())
        if u.returncode:
            sys.exit("could not rewrite %s: %s" % (uri, u.stderr.strip()[:200]))
        _m_state.task_txn(n, lambda t: _m_state.tev(t, "reshipped code for %s: %s (%d files; dirs %s) -> %s" % (j, info["sha256"][:16], info["n"], ", ".join(x.name for x in [pkg] + extras), uri)))
        print("reshipped: %s now runs code %s (%d files from %s%s); spec %s rewritten. Resubmit with `nrp-task submit %s --reason ...`."
              % (j, info["sha256"][:16], info["n"], ", ".join(x.name for x in [pkg] + extras), ", left out for size: %s" % ", ".join(info["skipped"]) if info["skipped"] else "", uri, j))
        return 0

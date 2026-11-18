"""NRP monitor config (mechanical extraction; R3a)."""
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


def util_policy():
    """The effective utilization policy, read by the sibling `nrp-util-check` (shared file + optional local override; one
    implementation). Returns {} when the sibling is not beside this script (the built-in defaults then apply)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not _m_state._UTIL:
        mod = None
        try:
            import importlib.machinery, importlib.util
            f = Path(__file__).resolve().parent.parent / "nrp-util-check"
            if f.is_file():
                ld = importlib.machinery.SourceFileLoader("nrp_util_check_policy", str(f))
                mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(ld.name, ld))
                ld.exec_module(mod)
        except Exception as e:
            mod = None
            _m_state.log("utilization policy not readable (%s); built-in defaults" % str(e)[:100])
        if mod is not None:
            for w in mod.POLICY_WARNINGS:
                _m_state.log(w)
        _m_state._UTIL.append(dict(mod.POLICY) if mod is not None else {})
    return _m_state._UTIL[0]


def gpu_floor():
    """NRP's GPU floor (fraction) from the effective policy; 0.40 when the policy is not readable."""
    try:
        return float(util_policy().get("gpu_floor") or 0.40)
    except (TypeError, ValueError):
        return 0.40


def max_jobs():
    """Cap on our unfinished Jobs at once: `max_concurrent_jobs` of the effective policy (shared default 400; a local override
    may only lower it). NRP_MONITOR_MAX_JOBS can lower it further for one run."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    n = util_policy().get("max_concurrent_jobs") or _m_state.DEFAULT_MAX_JOBS
    try:
        e = int(os.environ.get("NRP_MONITOR_MAX_JOBS") or 0)
    except ValueError:
        e = 0
    return min(n, e) if e > 0 else n


def _skip_limit():
    """Fraction of items whose single-item skips make a failure a pattern that goes to the owner (settings: skip_limit_fraction in
    config.json or NRP_MONITOR_SKIP_LIMIT_FRACTION; default 0.05, from the owner's house rules)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    v = os.environ.get("NRP_MONITOR_SKIP_LIMIT_FRACTION") or _m_state.OWNER.get("skip_limit_fraction")
    try:
        v = float(v)
        if 0 < v <= 1:
            return v
    except (TypeError, ValueError):
        pass
    return 0.05


def skip_limit_text():
    return "%g%%" % round(100 * _skip_limit(), 4)


def util_waiver_max():
    """How many util waivers one task may be given (settings: util_waiver_max in config.json or NRP_MONITOR_UTIL_WAIVER_MAX; default 3;
    0 turns waivers off). Once a task has used them, a util flag that survives the fix agent goes to the owner again."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    v = os.environ.get("NRP_MONITOR_UTIL_WAIVER_MAX")
    v = _m_state.OWNER.get("util_waiver_max") if v in (None, "") else v
    try:
        v = int(v)
        if v >= 0:
            return v
    except (TypeError, ValueError):
        pass
    return 3


def util_waiver_hours():
    """How long one util waiver suppresses the lab-floor flag of its Job (util_waiver_hours in config.json or NRP_MONITOR_UTIL_WAIVER_HOURS; default 6)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    v = os.environ.get("NRP_MONITOR_UTIL_WAIVER_HOURS")
    v = _m_state.OWNER.get("util_waiver_hours") if v in (None, "") else v
    try:
        v = float(v)
        if 0 < v <= 24 * 30:
            return v
    except (TypeError, ValueError):
        pass
    return 6.0

# ---- cluster / S3 reads --------------------------------------------------------------------------------------
def aws_env():
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    e = _m_agents.clean_env()
    for k in ("AWS_PROFILE", "AWS_CONFIG_FILE", "AWS_SHARED_CREDENTIALS_FILE", "AWS_DEFAULT_REGION"):
        if k in os.environ:
            e[k] = os.environ[k]
    return e


def step_env(s):
    e = aws_env()
    e.setdefault("PATH", "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin")
    e.update(s.get("env") or {})
    return e


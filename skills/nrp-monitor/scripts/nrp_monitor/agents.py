"""NRP monitor agents (mechanical extraction; R3a)."""
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

# ---- headless agents -----------------------------------------------------------------------------------------
def clean_env():
    keep = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "SHELL", "KUBECONFIG", "XDG_CONFIG_HOME",
            "NRP_MONITOR_STATE", "NRP_MONITOR_TESTING", "NRP_MONITOR_NO_WAKE", "NRP_MONITOR_T3_BIN",
            "NRP_MONITOR_CLAUDE_BIN", "NRP_MONITOR_CODEX_BIN", "NRP_TASK_CACHE", "NRP_MONITOR_NO_PUSH", "NRP_MONITOR_S3_ENDPOINT", "NRP_TASK_PYTHON")
    return {k: v for k, v in os.environ.items() if k in keep}


def default_agent_cfg():
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return {"runners": ["claude"],
            "models": {"pod": {"claude": _m_state.POD_MODEL}, "triage": {"claude": _m_state.TRIAGE_MODEL}, "repair": {"claude": _m_state.JOB_MODEL},
                       "repair_auth": {"claude": _m_state.JOB_MODEL}, "task": {"claude": _m_state.TASK_MODEL}, "deputy": {"claude": "sonnet", "codex": "gpt-6.1-sol"}},
            "limits": {"pod": {"turns": _m_state.POD_TURNS, "budget": _m_state.POD_BUDGET, "timeout": 900},
                       "triage": {"turns": _m_state.TRIAGE_TURNS, "budget": _m_state.TRIAGE_BUDGET, "timeout": _m_state.TRIAGE_TIMEOUT},
                       "repair": {"turns": _m_state.JOB_TURNS, "budget": _m_state.JOB_BUDGET, "timeout": 1500},
                       "repair_auth": {"turns": _m_state.AUTH_TURNS, "budget": _m_state.AUTH_BUDGET, "timeout": _m_state.AUTH_TIMEOUT},
                       "task": {"turns": _m_state.TASK_TURNS, "budget": _m_state.TASK_BUDGET, "timeout": _m_state.TASK_TIMEOUT},
                       "deputy": {"turns": _m_state.TASK_TURNS, "budget": _m_state.TASK_BUDGET, "timeout": _m_state.TASK_TIMEOUT}},
            "followup_ladder": ["triage"] + ["repair"] * _m_state.FOLLOWUP_REPAIR_ATTEMPTS,
            "tiers": {}}


def check_backend(tier, i, b):
    """One validated `tiers.<tier>[i]` entry: {runner, model?} -> normalised dict. Raises ValueError."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    w = "tiers.%s[%d]" % (tier, i)
    if not isinstance(b, dict) or set(b) - {"runner", "model"}:
        raise ValueError("%s: an object {runner, model}" % w)
    r = b.get("runner")
    if r not in _m_state.KNOWN_RUNNERS:
        raise ValueError("%s.runner: one of %s" % (w, "/".join(_m_state.KNOWN_RUNNERS)))
    if r == "agy" and tier not in _m_state.READ_ONLY_TIERS:
        raise ValueError("%s: this runner is limited to the %s tier (a read-only verdict); use claude or codex for %s" % (w, "/".join(_m_state.READ_ONLY_TIERS), tier))
    out = {"runner": r}
    if b.get("model") is not None:
        if not isinstance(b["model"], str) or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,64}", b["model"]):
            raise ValueError("%s.model: a model name" % w)
        out["model"] = b["model"]
    return out


def parse_agent_cfg(raw):
    """The effective config for a parsed agents.json object (defaults + overrides). Raises ValueError naming the first problem."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    cfg = default_agent_cfg()
    if not isinstance(raw, dict):
        raise ValueError("top level must be an object")
    bad = sorted(set(raw) - {"runners", "models", "limits", "followup_ladder", "tiers"})
    if bad:
        raise ValueError("unknown key(s) %s" % ", ".join(bad))
    if "runners" in raw:
        rs = raw["runners"]
        if not (isinstance(rs, list) and rs and len(set(rs)) == len(rs) and all(r in _m_state.KNOWN_RUNNERS for r in rs)):
            raise ValueError("runners: a non-empty list of %s, first = preferred" % "/".join(_m_state.KNOWN_RUNNERS))
        cfg["runners"] = list(rs)
    for tier, per in (raw.get("models") or {}).items():
        if tier not in _m_state.TIERS or not isinstance(per, dict):
            raise ValueError("models.%s: tier must be one of %s with {runner: model}" % (tier, ", ".join(_m_state.TIERS)))
        for r, m in per.items():
            if r not in _m_state.KNOWN_RUNNERS or not isinstance(m, str) or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,64}", m):
                raise ValueError("models.%s.%s: a model name" % (tier, r))
            cfg["models"].setdefault(tier, {})[r] = m
    for tier, per in (raw.get("limits") or {}).items():
        if tier not in _m_state.TIERS or not isinstance(per, dict) or set(per) - {"turns", "budget", "timeout"}:
            raise ValueError("limits.%s: tier + {turns, budget, timeout}" % tier)
        for k, v in per.items():
            if isinstance(v, bool) or not isinstance(v, (int, float, str)) or float(v) <= 0:
                raise ValueError("limits.%s.%s: a positive number" % (tier, k))
            cfg["limits"][tier][k] = int(v) if k == "timeout" else str(v)
    if "followup_ladder" in raw:
        ld = raw["followup_ladder"]
        if not (isinstance(ld, list) and 1 <= len(ld) <= 6 and all(x in _m_state.LADDER_STEPS for x in ld)):
            raise ValueError("followup_ladder: 1-6 steps, each triage or repair")
        cfg["followup_ladder"] = list(ld)
    if "tiers" in raw:
        tr = raw["tiers"]
        if not isinstance(tr, dict):
            raise ValueError("tiers: {tier: [backend, ...]}")
        for tier, lst in tr.items():
            if tier not in _m_state.TIERS or not isinstance(lst, list) or not 1 <= len(lst) <= 4:
                raise ValueError("tiers.%s: tier must be one of %s with 1-4 backends, first = preferred" % (tier, ", ".join(_m_state.TIERS)))
            cfg["tiers"][tier] = [check_backend(tier, i, b) for i, b in enumerate(lst)]
        if "runners" not in raw:                                          # the runners are the ones the tiers name (status, `agents test`)
            names = []
            for lst in cfg["tiers"].values():
                names += [b["runner"] for b in lst if b["runner"] not in names]
            cfg["runners"] = names + [r for r in cfg["runners"] if r not in names]
    return cfg


def load_agent_cfg():
    """(config, problem). A missing file is the defaults; an invalid one is the defaults plus a problem text (never a crash)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not _m_state.AGENTS_CFG.exists():
        return default_agent_cfg(), None
    try:
        return parse_agent_cfg(json.loads(_m_state.AGENTS_CFG.read_text())), None
    except (ValueError, OSError) as e:
        return default_agent_cfg(), "agents.json ignored (defaults used): %s" % e


def agent_cfg():
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    cfg, problem = load_agent_cfg()
    if problem and _m_state.PASS.get("cfg_problem") != problem:
        _m_state.PASS["cfg_problem"] = problem
        _m_state.log(problem)
        _m_notify.digest("fault", problem)
    return cfg


def tier_settings(tier, runner):
    cfg = agent_cfg()
    lim = cfg["limits"][tier]
    return {"model": cfg["models"].get(tier, {}).get(runner), "turns": str(lim["turns"]), "budget": str(lim["budget"]),
            "timeout": int(lim["timeout"])}


def tier_backends(tier):
    """The ordered backends a tier may use: `tiers.<tier>` when configured, else the old `runners` x `models` form (the agy runner only for
    the tiers it is limited to)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    cfg = agent_cfg()
    if tier == "deputy" and not cfg["tiers"].get(tier):
        return [{"runner": "claude", "model": cfg["models"]["deputy"]["claude"]}]
    if cfg["tiers"].get(tier):
        return [dict(b) for b in cfg["tiers"][tier]]
    return [dict({"runner": r}, **({"model": cfg["models"][tier][r]} if cfg["models"].get(tier, {}).get(r) else {}))
            for r in cfg["runners"] if r != "agy" or tier in _m_state.READ_ONLY_TIERS]


def spec_model(spec, runner):
    """The model a runner uses for this spec: the backend dispatch chose, else the tier's `models` entry."""
    b = spec.get("backend") or {}
    return b.get("model") or tier_settings(spec["tier"], runner)["model"]


class AgentCmd(list):
    """The Claude form of an agent command (a list) plus the spec every runner builds its own command from."""
    spec = None


def claude_argv(spec):
    s = tier_settings(spec["tier"], "claude")
    argv = ["claude", "-p", "--model", spec_model(spec, "claude") or s["model"], "--max-turns", s["turns"], "--max-budget-usd", s["budget"],
            "--permission-mode", "dontAsk", "--no-session-persistence"]
    if spec["json"]:
        argv += ["--output-format", "json"]
    if spec["allowed"]:                                                   # dontAsk denies everything else; an empty list is not a valid flag value
        argv += ["--allowedTools"] + spec["allowed"]
    if spec["deny"]:
        argv += ["--disallowedTools"] + spec["deny"]
    return argv


def agent_cmd(tier, allowed, json_out=False, deny=()):
    spec = {"tier": tier, "allowed": list(allowed), "json": json_out, "deny": list(deny)}
    cmd = AgentCmd(claude_argv(spec))
    cmd.spec = spec
    return cmd


def limit_hit(rc, out, err):
    """True when a finished agent process answered with a usage limit instead of doing the work."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    out = (out or "").strip()
    text = out
    if out.startswith("{"):                                               # claude --output-format json; agy --output-format json has `error`
        try:
            j = json.loads(out)
            text = str(j.get("result") or j.get("error") or "")
            rc = rc or (1 if j.get("is_error") or j.get("error") else 0)
        except ValueError:
            pass
    if rc:
        return bool(_m_state.LIMIT_ANY.search(text[-600:] + "\n" + (err or "")[-600:]))
    return bool(_m_state.LIMIT_START.search(text[:200]))


def auth_hit(rc, out, err):
    """True when a finished agent process failed because the CLI is not signed in / its credentials are invalid (not a bad answer)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    out = (out or "").strip()
    text = out
    if out.startswith("{"):
        try:
            j = json.loads(out)
            text = str(j.get("result") or j.get("error") or "")
            rc = rc or (1 if j.get("is_error") or j.get("error") else 0)
        except ValueError:
            pass
    return bool(rc) and bool(_m_state.AUTH_ANY.search(text + "\n" + (err or "")) or re.search(
        r"IneligibleTierError|UNSUPPORTED_CLIENT|no longer supported for Gemini Code Assist", out + "\n" + (err or ""), re.I))


def reset_time(text):
    """Epoch seconds of 'resets 2pm (America/Los_Angeles)' (next occurrence, plus a minute), or None."""
    m = re.search(r"resets?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)(?:\s*\(([^)]+)\))?", text or "", re.I)
    if not m:
        return None
    hh = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0)
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(m.group(4)) if m.group(4) else datetime.now().astimezone().tzinfo
    except Exception:
        tz = datetime.now().astimezone().tzinfo
    n = datetime.now(tz)
    t = n.replace(hour=hh, minute=int(m.group(2) or 0), second=0, microsecond=0)
    if t <= n:
        t += timedelta(days=1)
    return t.timestamp() + 60


def runner_ready(name):
    return shutil.which(name, path=clean_env().get("PATH")) is not None


def runner_blocked(name):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return float((_m_notify.read_json(_m_state.RUNNER_STATE, {}).get(name) or {}).get("until", 0)) > _m_state.now()


def available_runners():
    return [r for r in agent_cfg()["runners"] if not runner_blocked(r) and runner_ready(r)]


def agents_available():
    return bool(available_runners())


def is_unavailable(text):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return str(text).startswith(_m_state.UNAVAILABLE)


def unavailable_text():
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    st, bits = _m_notify.read_json(_m_state.RUNNER_STATE, {}), []
    for r in agent_cfg()["runners"]:
        u = float((st.get(r) or {}).get("until", 0))
        bits.append("%s %s" % (r, ("%s until %s" % ("not signed in, retried" if (st.get(r) or {}).get("kind") == "auth" else "out of usage",
                                                    datetime.fromtimestamp(u).strftime("%a %H:%M"))) if u > _m_state.now() else
                               "not installed" if not runner_ready(r) else "unavailable"))
    return "%s: %s" % (_m_state.UNAVAILABLE, "; ".join(bits))


def block_runner(runner, out, err, kind="limit"):
    """Set a runner aside: `limit` until its reset time (usage / rate limit), `auth` for AUTH_BLOCK_S (not signed in)."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    text = " ".join(((out or "") + " " + (err or "")).split())
    if kind == "auth":
        m = _m_state.AUTH_ANY.search(text)
        why = text[max(0, m.start() - 20):m.end() + 100] if m else text[:120]
        until = _m_state.now() + _m_state.AUTH_BLOCK_S
    else:
        m = _m_state.LIMIT_ANY.search(text)
        why = text[max(0, m.start() - 20):m.end() + 100] if m else text[:120]
        until = reset_time(text) or _m_state.now() + 3600
        until = min(max(until, _m_state.now() + 300), _m_state.now() + 8 * 86400)
    st = _m_notify.read_json(_m_state.RUNNER_STATE, {})
    st[runner] = {"until": until, "since": _m_state.now(), "why": why[:200], "kind": kind}
    _m_state.STATE.mkdir(parents=True, exist_ok=True)
    _m_notify.write_json(_m_state.RUNNER_STATE, st)
    what = "is not signed in (auth error); tried again after" if kind == "auth" else "is out of usage until"
    _m_state.log("agent runner %s %s %s: %s" % (runner, what, _m_state.iso_at(until), why[:160]))
    _m_notify.digest("fault", "agent runner %s %s %s (%s); %s" % (
        runner, what, _m_state.iso_at(until), why[:100], "work moves to " + ", ".join(available_runners()) if available_runners() else "no runner left: agent work waits"))
    if not available_runners():
        _m_notify.push("agents unavailable: %s. Fix agents and follow-ups wait (no retry is used up) and resume by themselves; "
             "`nrp-monitor agents` shows the state, or add a runner in agents.json." % unavailable_text().split(": ", 1)[1],
             "agents:unavailable")


def exec_claude(spec, prompt, cwd, timeout, env):
    try:
        r = subprocess.run(claude_argv(spec), input=prompt, capture_output=True, text=True, cwd=str(cwd), env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "timeout", "", "", None
    if limit_hit(r.returncode, r.stdout, r.stderr):
        return "limit", r.stdout, r.stderr, r.returncode
    return ("auth" if auth_hit(r.returncode, r.stdout, r.stderr) else "ok"), r.stdout, r.stderr, r.returncode


def codex_rules(allowed):
    """Claude `Bash(prefix:*)` allowlist entries as Codex execpolicy rules: a matching command runs outside the sandbox
    (network, kubectl); everything else stays sandboxed."""
    rules = []
    for a in allowed:
        m = re.fullmatch(r"Bash\((.*?)(?::\*)?\)", a)
        if not m:
            continue
        try:
            toks = shlex.split(m.group(1))
        except ValueError:
            continue
        if toks:
            rules.append("prefix_rule(pattern=%s, decision=\"allow\")" % json.dumps(toks))
    return "\n".join(rules) + "\n"


def codex_writable(allowed):
    """Directories the Claude allowlist lets the agent edit (Edit/Write rules), minus anything inside .git."""
    out = []
    for a in allowed:
        m = re.fullmatch(r"(?:Edit|Write)\(/(/.*?)/\*\*\)", a)
        if m and ".git" not in m.group(1).split("/") and m.group(1) not in out:
            out.append(m.group(1))
    return out


def exec_codex(spec, prompt, cwd, timeout, env):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    auth = Path(os.environ.get("NRP_MONITOR_CODEX_AUTH") or Path.home() / ".codex" / "auth.json")   # env: tests
    if not auth.exists():
        return "auth", "", "codex is not signed in (no %s)" % auth, 1
    s = tier_settings(spec["tier"], "codex")
    s["model"] = spec_model(spec, "codex")
    _m_state.WORK.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix="codex-home-", dir=str(_m_state.WORK)))
    try:
        (home / "rules").mkdir()
        os.symlink(str(auth), str(home / "auth.json"))
        (home / "rules" / "monitor.rules").write_text(codex_rules(spec["allowed"]))
        last = home / "last.txt"
        argv = ["codex", "exec", "-s", "read-only" if spec["tier"] == "triage" else "workspace-write", "-c", 'approval_policy="never"',
                "-c", "sandbox_workspace_write.exclude_tmpdir_env_var=true", "-c", "sandbox_workspace_write.exclude_slash_tmp=true",
                "--skip-git-repo-check", "--ephemeral", "-C", str(cwd), "-o", str(last)]
        for d in codex_writable(spec["allowed"]):
            argv += ["--add-dir", d]
        if s["model"]:
            argv += ["-m", s["model"]]
        argv.append("-")
        try:
            r = subprocess.run(argv, input=prompt, capture_output=True, text=True, cwd=str(cwd), env=dict(env, CODEX_HOME=str(home)),
                               timeout=timeout)
        except subprocess.TimeoutExpired:
            return "timeout", "", "", None
        text = last.read_text().strip() if last.exists() else ""
        if limit_hit(r.returncode, text or r.stdout, r.stderr):
            return "limit", text or r.stdout, r.stderr, r.returncode
        if auth_hit(r.returncode, text or r.stdout, r.stderr):
            return "auth", text or r.stdout, r.stderr, r.returncode
        if spec["json"]:
            text = json.dumps({"result": text or (r.stderr.strip() or r.stdout.strip())[-300:], "is_error": bool(r.returncode),
                               "total_cost_usd": None, "num_turns": None, "permission_denials": [], "runner": "codex",
                               "usage": {"total_tokens": int(re.search(r"tokens used\s+([\d,]+)", r.stderr).group(1).replace(",", ""))} if re.search(r"tokens used\s+([\d,]+)", r.stderr) else None})
        return "ok", text or (r.stdout if r.returncode else ""), r.stderr, r.returncode
    finally:
        shutil.rmtree(str(home), ignore_errors=True)


def agy_workspace(home, allowed):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    hooks = home / ".agents"
    hooks.mkdir(parents=True)
    (hooks / "allow.json").write_text(json.dumps(allowed))
    (hooks / "gate.py").write_text(_m_state.AGY_GATE)
    import shlex
    command = " ".join(shlex.quote(x) for x in (sys.executable, str(hooks / "gate.py"), str(hooks / "allow.json")))
    (hooks / "hooks.json").write_text(json.dumps({"nrp-monitor": {"PreToolUse": [
        {"matcher": "*", "hooks": [{"type": "command", "command": command, "timeout": 10}]}]}}))


def exec_agy(spec, prompt, cwd, timeout, env):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if spec["tier"] != "triage":
        return "error", "", "agy is read-only triage only", 1
    _m_state.WORK.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agy-run-", dir=str(_m_state.WORK)) as td:
        home = Path(td)
        agy_workspace(home, spec["allowed"])
        argv = ["agy", "--print", prompt, "--mode", "plan", "--effort", "low",
                "--output-format", "json", "--model", (spec.get("backend") or {}).get("model") or "gemini-3.8-flash-low"]
        try:
            r = subprocess.run(argv, cwd=str(home), env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "timeout", "", "", None
        if limit_hit(r.returncode, r.stdout, r.stderr):
            return "limit", r.stdout, r.stderr, r.returncode
        if auth_hit(r.returncode, r.stdout, r.stderr):
            return "auth", r.stdout, r.stderr, r.returncode
        text, failed = r.stdout.strip(), bool(r.returncode)
        try:
            j = json.loads(text)
            text = str(j.get("result") or j.get("response") or j.get("error") or "")
            failed = failed or bool(j.get("is_error") or j.get("error"))
        except ValueError:
            pass
        if spec["json"]:
            text = json.dumps({"result": text, "is_error": failed, "runner": "agy"})
        return "ok", text, r.stderr, r.returncode


RUNNER_EXEC = {"claude": exec_claude, "codex": exec_codex, "agy": exec_agy}


def backend_name(b):
    return "%s%s" % (b["runner"], "/" + b["model"] if b.get("model") else "")


def note_failover(spec, backends, i, why, on_failover):
    """One line per failover (log, digest, and the task's events through `on_failover`): which backend was unavailable, why, who takes over."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    nxt = next((x for x in backends[i + 1:] if not runner_blocked(x["runner"]) and runner_ready(x["runner"])), None)
    msg = "backend failover (tier %s): %s unavailable (%s); %s" % (spec["tier"], backend_name(backends[i]), why[:120],
                                                                     "using " + backend_name(nxt) if nxt else "no backend left for this tier")
    _m_state.log(msg)
    _m_notify.digest("failover", msg)
    if on_failover:
        on_failover(msg)


def dispatch_agent(spec, prompt, cwd, timeout=None, env=None, on_failover=None):
    """(runner, status, out, err, rc). status: ok | timeout | unavailable (every backend of the tier is out of usage, not signed in or missing).
    Backends are tried in the tier's order; the next one is used ONLY when one is unavailable. A timeout or a bad answer is returned as is."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    cwd.mkdir(parents=True, exist_ok=True)
    env = env or clean_env()
    backends = tier_backends(spec["tier"])
    for i, b in enumerate(backends):
        runner = b["runner"]
        if not runner_ready(runner):
            note_failover(spec, backends, i, "not installed", on_failover)
            continue
        if runner_blocked(runner):
            u = float((_m_notify.read_json(_m_state.RUNNER_STATE, {}).get(runner) or {}).get("until", 0))
            note_failover(spec, backends, i, "set aside until %s" % _m_state.iso_at(u), on_failover)
            continue
        status, out, err, rc = RUNNER_EXEC[runner](dict(spec, backend=b), prompt, cwd, timeout or tier_settings(spec["tier"], runner)["timeout"], env)
        if status in ("limit", "auth"):
            block_runner(runner, out, err, status)
            note_failover(spec, backends, i, "usage limit" if status == "limit" else "not signed in", on_failover)
            continue
        if spec.get("json"):
            try:
                payload = json.loads(out)
                payload.setdefault("model", b.get("model") or tier_settings(spec["tier"], runner)["model"])
                out = json.dumps(payload)
            except (ValueError, AttributeError):
                pass
        if status == "ok":
            _m_notify.push_clear("agents:unavailable")
        return runner, status, out, err, rc
    return None, "unavailable", unavailable_text(), "", None


def run_agent(cmd, prompt, cwd, timeout=None):
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import legacy as _m_legacy  # Local import breaks orchestration cycle; patches stay on the defining module.
    spec = dict(cmd.spec, json=True)
    runner, status, stdout, stderr, rc = dispatch_agent(spec, prompt, cwd, timeout)
    try:
        result = json.loads(stdout)
        text = str(result.get("result") or "")
    except (ValueError, AttributeError):
        result, text = {}, stdout
    tier = spec["tier"]
    kind = "pod_agent" if tier == "pod" else "followup"
    _m_decisions.cost_event(spec.get("ledger_task", cwd.name), kind, "1" if tier == "triage" else "2",
               "resolved" if _m_legacy.followup_solved(text) or (tier == "pod" and re.match(r"^(DELETED|OVERSIZED|KEPT|NOTFOUND)\b", text)) else "stopped" if status != "ok" else "escalated",
               runner=runner, model=result.get("model"), result=result)
    stdout = text
    if status == "unavailable":
        return stdout
    if status == "timeout":
        return "AGENT TIMEOUT"
    out = [l.strip() for l in stdout.splitlines() if l.strip()]
    if rc:
        return "AGENT ERROR rc=%d %s" % (rc, (stderr.strip() or stdout.strip())[-300:])
    verdict = [l for l in out if re.match(r"(DELETED|OVERSIZED|KEPT|NOTFOUND|RESUBMITTED|DONE|STOPPED|ESCALATE)\b", l)]
    return (verdict[-1] if verdict else out[-1]) if out else "AGENT EMPTY"


def kube_read_allow(k):
    """Read-only kubectl patterns for headless follow-up agents. Both flag orders work: `kubectl -n NS get job X` and
    `kubectl get job X -n NS` (agents write the second; a literal `kubectl -n NS get` prefix denied it, 2026-11-05).
    Only job/pod/event reads and logs/describe are allowed, never secrets."""
    pats = [k + " get:*", k + " describe:*", k + " logs:*"]
    pats += ["kubectl get job:*", "kubectl get jobs:*", "kubectl get pod:*", "kubectl get pods:*", "kubectl get event:*", "kubectl get events:*",
             "kubectl describe job:*", "kubectl describe pod:*", "kubectl logs:*"]
    return ["Bash(%s)" % p for p in pats]


def auth_allowed(k, job, ns, adir):
    """Task-level approval (owner decision 2026-11-05): the task was approved when it was registered with --authorize, so the follow-up
    agent may debug and resubmit it without asking: apply Job files, create a ConfigMap, delete THIS task's finished Jobs, edit the
    task's own files under approved/<task>/, and register the replacement (the script enforces the attempt cap and the
    same-failure rule there). It cannot touch secrets, other namespaces or other people's Jobs."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    a = str(_m_state.APPROVED).rstrip("/")                    # all task dirs: a next-stage task needs its own manifest dir
    pats = [k + " apply:*", k + " create configmap:*", k + " delete job %s:*" % job,
            "kubectl apply:*", "kubectl create configmap:*", "kubectl delete job %s:*" % job,
            "nrp-monitor add:*", "nrp-monitor list", "nrp-watchdog add:*", "nrp-watchdog list", "tar czf:*", "tar tzf:*", "diff:*", "ls:*", "cat %s/:*" % a, "python3 -m py_compile:*"]
    out = ["Bash(%s)" % p for p in pats]
    out += ["Read(/%s/**)" % a, "Edit(/%s/**)" % a]     # leading // = absolute path; Edit rules cover Write too
    return out


def pod_allowed(pod, owner_job):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    k = "kubectl -n %s" % _m_state.NS
    a = ["Bash(%s get pod %s:*)" % (k, pod), "Bash(%s logs %s:*)" % (k, pod), "Bash(%s describe pod %s:*)" % (k, pod),
         "Bash(%s exec %s -- nvidia-smi:*)" % (k, pod), "Bash(%s delete pod %s)" % (k, pod),
         "Bash(nrp-util-check:*)"]
    if owner_job:
        a += ["Bash(%s get job %s:*)" % (k, owner_job), "Bash(%s delete job %s)" % (k, owner_job)]
    return a


def pod_prompt(pod, flag_line, owner_job, strike=1):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = (_m_state.TPL / "pod_check.md").read_text()
    text = ("first flag" if strike < 2 else
            "flagged again on the pass after an OVERSIZED warning")
    return (t.replace("{strike}", str(strike)).replace("{strike_text}", text).replace("{pod}", pod).replace("{ns}", _m_state.NS).replace("{flag_line}", flag_line)
            .replace("{owner_job}", owner_job or "(none: not owned by a Job)").replace("{user}", _m_state.USER_ANN).replace("{owner}", _m_state.OWNER_NAME))


def job_prompt(job, rec, status, resume_text):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = (_m_state.TPL / "job_followup.md").read_text()
    out = (t.replace("{job}", job).replace("{ns}", rec.get("ns", _m_state.NS)).replace("{status}", status)
           .replace("{label}", rec.get("label") or "").replace("{origin}", _m_wake.origin_plain(rec.get("origin")))
           .replace("{resume}", resume_text))
    au = rec.get("authorize")
    if au:
        ta = (_m_state.TPL / "job_authorized.md").read_text()
        out += "\n" + (ta.replace("{job}", job).replace("{ns}", rec.get("ns", _m_state.NS)).replace("{dir}", au["dir"])
                        .replace("{attempt}", str(au["attempt"])).replace("{max}", str(au["max"]))
                        .replace("{root}", au["root"]).replace("{failures}", "; ".join(au.get("failures", [])) or "none yet")
                        .replace("{has_manifest}", "yes: %s/manifest.yaml" % au["dir"] if au.get("manifest") else "no (the notes say how the Job was made)")
                        .replace("{has_code}", "yes: %s/code (original in code.orig)" % au["dir"] if au.get("code") else "no"))
    return out


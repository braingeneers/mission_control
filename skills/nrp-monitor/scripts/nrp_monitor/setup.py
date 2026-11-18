"""NRP monitor setup (mechanical extraction; R3a)."""
import json
import os
import shutil
import sys
import time

from . import agents as _m_agents
from . import notify as _m_notify
from . import state as _m_state


def installed_runners():
    return [r for r in _m_state.KNOWN_RUNNERS if shutil.which(r)]


def suggest_tiers(have):
    """The suggested ordered backends per tier for the runners `have` (installed AND subscribed). Gemini flash with the lowest thinking for
    triage when available (its only tier), Sonnet for the fixer; the other available runner is listed after as the failover."""
    tiers = {}
    tri = []
    if "agy" in have:
        tri.append({"runner": "agy", "model": "gemini-3.8-flash-low"})
    for r in ("claude", "codex"):
        if r in have:
            tri.append({"runner": r, "model": _m_state.SETUP_DEFAULT_MODEL[(r, "triage")]})
    fix = [{"runner": r, "model": _m_state.SETUP_DEFAULT_MODEL[(r, "task")]} for r in ("claude", "codex") if r in have]
    if tri:
        tiers["triage"] = tri[:3]
    if fix:
        tiers["task"] = fix[:3]
    return tiers


def parse_backend_spec(tier, text, i=0):
    """'runner[:model]' -> a validated backend dict (ValueError names the problem)."""
    parts = [x.strip() for x in text.split(":")]
    if not parts[0] or len(parts) > 2:
        raise ValueError("backend %r: runner[:model]" % text)
    b = {"runner": parts[0]}
    if len(parts) > 1 and parts[1]:
        b["model"] = parts[1]
    return _m_agents.check_backend(tier, i, b)


def parse_backend_list(tier, text):
    return [parse_backend_spec(tier, x, i) for i, x in enumerate(t for t in text.split(",") if t.strip())]


def backend_label(b):
    return "%s%s%s" % (b["runner"], "/" + b["model"] if b.get("model") else " (CLI default model)", ", thinking " + str(b["thinking"]) if b.get("thinking") is not None else "")


def setup_config(old, tiers):
    """The agents.json object to write: whatever the user already had (limits, models, follow-up ladder) plus `tiers`, and `runners` (the
    tiers' runners, fixer first; read-only runners are still excluded from writing tiers)."""
    cfg = {k: v for k, v in (old or {}).items() if k != "tiers"}
    cfg["tiers"] = dict((old or {}).get("tiers") or {}, **tiers)
    runners = []
    for tier in ("task", "triage", "deputy"):
        for b in cfg["tiers"].get(tier, []):
            if b["runner"] not in runners:
                runners.append(b["runner"])
    if runners:
        cfg["runners"] = runners
    else:
        cfg.pop("runners", None)
    return {k: cfg[k] for k in ("runners", "tiers", "models", "limits", "followup_ladder") if k in cfg}


def write_agents_cfg(new_text):
    """Atomically replace agents.json with `new_text`, keeping the old file as agents.json.bak. Returns the backup path or None."""
    _m_state.AGENTS_CFG.parent.mkdir(parents=True, exist_ok=True)
    bak = None
    if _m_state.AGENTS_CFG.exists():
        bak = _m_state.AGENTS_CFG.with_name(_m_state.AGENTS_CFG.name + ".bak")
        shutil.copy2(str(_m_state.AGENTS_CFG), str(bak))
    tmp = _m_state.AGENTS_CFG.with_name(_m_state.AGENTS_CFG.name + ".tmp")
    tmp.write_text(new_text)
    os.chmod(str(tmp), 0o600)
    os.replace(str(tmp), str(_m_state.AGENTS_CFG))
    return bak


def setup_ask(prompt, default=""):
    try:
        ans = input("%s%s: " % (prompt, " [%s]" % default if default else "")).strip()
    except EOFError:
        sys.exit("setup needs answers: run it in a terminal, or use --non-interactive with --triage/--fixer")
    return ans or default


def cmd_setup(a):
    import difflib
    installed = installed_runners()
    interactive = not a.non_interactive
    if interactive and not sys.stdin.isatty() and not os.environ.get("NRP_MONITOR_SETUP_ANYSTDIN"):
        sys.exit("setup is interactive and stdin is not a terminal. Run it in a terminal, or pass --non-interactive "
                 "[--subscriptions claude,agy] [--triage RUNNER:MODEL[:THINKING],...] [--fixer RUNNER:MODEL,...] [--dry-run].")
    print("NRP monitor setup: which assistants run its background agents (Tier 1 triage, Tier 2 fixer).")
    print("Tier 3 is always the chat that owns the work (woken once per finished step, or as a last resort); there is no separate Opus tier.\n")
    print("Installed CLIs: %s" % (", ".join("%s (%s)" % (r, shutil.which(r)) for r in installed) or "none found on PATH"))
    if a.subscriptions is not None:
        subs = [x.strip() for x in a.subscriptions.split(",") if x.strip()]
    elif interactive:
        ans = setup_ask("Which do you have a subscription or API access for? (%s)" % ", ".join(_m_state.SUBSCRIPTIONS), ",".join(installed) or "claude")
        subs = [x.strip().lower() for x in ans.replace(" ", ",").split(",") if x.strip()]
    else:
        subs = list(installed)
    bad = [x for x in subs if x not in _m_state.SUBSCRIPTIONS]
    if bad:
        sys.exit("unknown subscription(s) %s (choose from %s)" % (", ".join(bad), ", ".join(_m_state.SUBSCRIPTIONS)))
    for r in subs:
        if r in _m_state.KNOWN_RUNNERS and r not in installed:
            print("note: you named %s but its CLI is not on PATH; install it before using it (it is left out of the suggestions)." % r)
    have = [r for r in _m_state.KNOWN_RUNNERS if r in subs and r in installed]
    if "t3" in subs:
        print("T3: the coordinator chat is woken through the task's webhook relay (configured per task by the operator); the T3 chat itself "
              "may run Claude or Codex, which is a separate choice from the agents below.")
    sugg = suggest_tiers(have)
    tiers, explicit = {}, {"triage": a.triage, "task": a.fixer}
    for tier, title in _m_state.SETUP_TIERS:
        if explicit[tier]:
            try:
                tiers[tier] = parse_backend_list(tier, explicit[tier])
            except ValueError as e:
                sys.exit("--%s: %s" % ("fixer" if tier == "task" else "triage", e))
            if not tiers[tier]:
                sys.exit("--%s: at least one backend" % ("fixer" if tier == "task" else "triage"))
            continue
        default = sugg.get(tier, [])
        if not default:
            sys.exit("no backend is available for %s: it needs %s installed and in your subscriptions" % (title, "Claude Code or Codex" if tier == "task" else "Claude Code, Codex or Gemini CLI"))
        if interactive:
            print("\n%s\n  suggested, in order (the next is used only when the one before is unavailable):" % title)
            for i, b in enumerate(default, 1):
                print("   %d. %s" % (i, backend_label(b)))
            print("  Enter to accept, or type backends as runner[:model],... (e.g. agy:gemini-3.8-flash-low,claude:haiku).")
            while True:
                ans = setup_ask("%s backends" % ("Tier 1" if tier == "triage" else "Tier 2"), "")
                try:
                    tiers[tier] = parse_backend_list(tier, ans) if ans else default
                    unavailable = [b["runner"] for b in tiers[tier] if b["runner"] not in have]
                    if unavailable:
                        print("  %s: not installed or not in your subscriptions; they stay in the list but will be skipped." % ", ".join(sorted(set(unavailable))))
                    break
                except ValueError as e:
                    print("  %s" % e)
        else:
            tiers[tier] = default
    old, old_text = None, ""
    if _m_state.AGENTS_CFG.exists():
        old_text = _m_state.AGENTS_CFG.read_text()
        try:
            old = json.loads(old_text)
            if not isinstance(old, dict):
                raise ValueError("not an object")
        except ValueError:
            sys.exit("%s exists but is not valid JSON; fix or move it first (setup will not overwrite what it cannot read)" % _m_state.AGENTS_CFG)
    if getattr(a, "deputy", None):
        try:
            tiers["deputy"] = parse_backend_list("deputy", a.deputy)
        except ValueError as e:
            sys.exit("--deputy: %s" % e)
    new = setup_config(old, tiers)
    try:
        _m_agents.parse_agent_cfg(new)
    except ValueError as e:
        sys.exit("the chosen configuration is invalid: %s" % e)
    new_text = json.dumps(new, indent=2) + "\n"
    old_lines = old_text.splitlines(True)
    if old_lines and not old_lines[-1].endswith("\n"):
        old_lines[-1] += "\n"
    diff = "".join(difflib.unified_diff(old_lines, new_text.splitlines(True), "agents.json (current)" if old is not None else "(new file)", "agents.json (proposed)"))
    if not diff:
        print("\nagents.json already matches: nothing to change.")
        return 0
    print("\n" + diff)
    if a.dry_run:
        print("(dry run: nothing written)")
        return 0
    if interactive and setup_ask("Write %s%s? (y/n)" % (_m_state.AGENTS_CFG, " (the old file is kept as .bak)" if old is not None else ""), "y").lower() not in ("y", "yes"):
        print("nothing written")
        return 1
    bak = write_agents_cfg(new_text)
    print("wrote %s%s. Check with `nrp-monitor agents` and `nrp-monitor agents test`." % (_m_state.AGENTS_CFG, " (previous version: %s)" % bak if bak else ""))
    return 0


def cmd_agents(a):
    cfg, problem = _m_agents.load_agent_cfg()
    if a.acmd == "unblock":
        st = _m_notify.read_json(_m_state.RUNNER_STATE, {})
        if a.runner not in _m_state.KNOWN_RUNNERS:
            sys.exit("runner must be one of %s" % ", ".join(_m_state.KNOWN_RUNNERS))
        st.pop(a.runner, None)
        _m_notify.write_json(_m_state.RUNNER_STATE, st)
        _m_notify.push_clear("agents:unavailable")
        print("%s: block cleared" % a.runner)
        return 0
    if a.acmd == "test":
        spec = {"tier": "triage", "allowed": [], "json": False, "deny": []}
        (_m_state.WORK / "followup").mkdir(parents=True, exist_ok=True)
        rc = 0
        for r in ([a.runner] if a.runner else list(dict.fromkeys(cfg["runners"] + [b["runner"] for bs in cfg.get("tiers", {}).values() for b in bs]))):
            if r not in _m_state.KNOWN_RUNNERS or not _m_agents.runner_ready(r):
                print("%-7s not installed" % r)
                rc = 1
                continue
            t0 = time.time()
            bk = next((x for x in _m_agents.tier_backends("triage") if x["runner"] == r), {"runner": r})
            status, out, err, code = _m_agents.RUNNER_EXEC[r](dict(spec, backend=bk), "Reply with exactly the single word OK and nothing else.", _m_state.WORK / "followup", 180, _m_agents.clean_env())
            if status in ("limit", "auth"):
                _m_agents.block_runner(r, out, err, status)
            ok = status == "ok" and not code and out.strip().upper().startswith("OK")
            print("%-7s %s in %.0fs: %s" % (r, "works" if ok else "FAILED (%s)" % status, time.time() - t0,
                                           " ".join((out or err or "").split())[-120:]))
            rc = rc or (0 if ok else 1)
        return rc
    print("config: %s%s" % (_m_state.AGENTS_CFG, "" if _m_state.AGENTS_CFG.exists() else " (absent: Claude only, built-in models)"))
    if problem:
        print("PROBLEM: " + problem)
    st = _m_notify.read_json(_m_state.RUNNER_STATE, {})
    for r in cfg["runners"]:
        u = float((st.get(r) or {}).get("until", 0))
        print("runner %d: %-7s %s" % (cfg["runners"].index(r) + 1, r, "NOT INSTALLED" if not _m_agents.runner_ready(r) else
              "out of usage until %s (%s)" % (_m_state.iso_at(u), st[r].get("why", "")[:70]) if u > _m_state.now() else "ready"))
    for tier in _m_state.TIERS:
        lim = cfg["limits"][tier]
        print("  %-11s %s  turns %s budget $%s timeout %ss (turns/budget: Claude only)" % (
              tier, " -> ".join("%s%s%s" % (x["runner"], "/" + x["model"] if x.get("model") else " (default model)",
                                           " thinking=%s" % x["thinking"] if x.get("thinking") is not None else "") for x in _m_agents.tier_backends(tier)) or "(no backend)",
              lim["turns"], lim["budget"], lim["timeout"]))
    print("Tier 3 (every task): its coordinator chat, woken through its origin (t3 CLI/webhook / claude or codex session); no model entry")
    print("job follow-up ladder: " + " -> ".join(cfg["followup_ladder"]) + " -> a person")
    return 0


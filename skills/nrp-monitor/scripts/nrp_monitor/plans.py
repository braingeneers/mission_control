"""NRP monitor plans (mechanical extraction; R3a)."""
import os
import re
import shutil
import sys
from pathlib import Path


def on_done_enabled():
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return _m_state.ON_DONE_FLAG.exists()


def plan_dir(pid):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return _m_state.PLANS / pid


def split_list(v):
    v = (v or "").strip()
    if v.lower() in ("", "none", "-", "[]"):
        return []
    return [x.strip() for x in v.strip("[]").split(",") if x.strip()]


def plan_section(text, pid):
    """The part of a plan file that belongs to plan `pid`: the heading carrying `<!-- plan:pid -->` down to the next heading of the
    same or higher level (code fences skipped). A file whose only run block names pid is used whole."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    lines, fence, start, level = text.splitlines(), False, None, 0
    for i, l in enumerate(lines):
        if l.lstrip().startswith("```"):
            fence = not fence
            continue
        m = re.match(r"^(#{1,6})\s", l)
        if fence or not m:
            continue
        if start is None and ("<!-- plan:%s -->" % pid) in l:
            start, level = i, len(m.group(1))
        elif start is not None and len(m.group(1)) <= level:
            return "\n".join(lines[start:i]) + "\n"
    if start is not None:
        return "\n".join(lines[start:]) + "\n"
    if len(re.findall(r"^```run\s*$", text, re.M)) == 1:
        return text
    raise _m_state.ChainError("no heading with <!-- plan:%s --> in the plan file (and it is not a single-plan file)" % pid)


def parse_run_block(section):
    """The machine-read run header: a ```run fenced block of `key: value` lines (# starts a comment)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    m = re.search(r"^```run\s*\n(.*?)^```", section, re.S | re.M)
    if not m:
        raise _m_state.ChainError("the plan section has no ```run block (run header)")
    raw, bad = {}, []
    for l in m.group(1).splitlines():
        l = re.sub(r"(^|\s)#.*$", "", l).rstrip()
        if not l.strip():
            continue
        if ":" not in l:
            bad.append("run block line without `key:`: %r" % l[:60])
            continue
        k, v = l.split(":", 1)
        raw[k.strip()] = v.strip()
    h = {"plan": raw.get("plan", ""), "approval": raw.get("approval", ""), "steps": split_list(raw.get("steps")),
         "approved_through": raw.get("approved_through", "none").strip() or "none",
         "stops": split_list(raw.get("stop_for_owner") or raw.get("stop_for_hunter")), "may_touch": split_list(raw.get("may_touch")),
         "templates": split_list(raw.get("templates")), "next": {}}
    h["fallback"] = raw.get("fallback", "on").lower()
    try:
        h["fallback_hours"] = float(raw.get("fallback_hours", 3))
        if not 0 < h["fallback_hours"] < float("inf"):
            raise ValueError()
    except ValueError:
        bad.append("fallback_hours: a finite positive number")
    if h["fallback"] not in ("on", "off"):
        bad.append("fallback: on or off")
    for part in [x for x in (raw.get("next") or "").split(";") if x.strip()]:
        a, _, b = part.partition(">")
        if not b:
            bad.append("next: `step>step[,step]; ...` (got %r)" % part.strip())
            continue
        h["next"][a.strip()] = [x.strip() for x in b.split(",") if x.strip()]
    h["groups"], h["retries"], h["wake_overrides"] = {}, {}, {}
    for part in filter(str.strip, raw.get("groups", "").split(";")):
        name, sep, members = part.strip().partition("=")
        if not sep or not _m_state.PLAN_ID_RE.fullmatch(name) or name in h["groups"]:
            bad.append("groups: unique name=step[,step] entries")
            continue
        h["groups"][name] = split_list(members)
    assigned = []
    for members in h["groups"].values():
        if not members or any(x not in h["steps"] for x in members):
            bad.append("groups: nonempty sets of known steps required")
        assigned += members
    if len(assigned) != len(set(assigned)):
        bad.append("groups: each step belongs to at most one group")
    h["wake"] = raw.get("wake", "group" if h["groups"] else "task")
    for key, value in raw.items():
        if key.startswith("wake_"):
            name = key[5:]
            if name not in h["groups"]:
                bad.append("wake override: unknown group " + name)
            h["wake_overrides"][name] = value
    if any(v not in ("task", "group", "digest") for v in [h["wake"]] + list(h["wake_overrides"].values())):
        bad.append("wake: task, group or digest")
    for part in filter(str.strip, raw.get("retries", "").split(";")):
        name, sep, value = part.strip().partition("=")
        if not sep or name not in h["groups"] or not value.isdigit():
            bad.append("retries: known-group=nonnegative-integer")
        else:
            h["retries"][name] = int(value)
    if not _m_state.PLAN_ID_RE.match(h["plan"]):
        bad.append("plan: id of lowercase letters, digits and - (max 40)")
    if len(h["approval"]) < 8:
        bad.append("approval: the owner's words and the date (verbatim), required")
    if not h["steps"]:
        bad.append("steps: the step ids in order, e.g. `1, 2, 2b, 3`")
    for s in h["steps"]:
        if not _m_state.STEP_ID_RE.match(s):
            bad.append("steps: bad step id %r" % s)
    if len(set(h["steps"])) != len(h["steps"]):
        bad.append("steps: duplicate id")
    known = set(h["steps"])
    if h["approved_through"] != "none" and h["approved_through"] not in known:
        bad.append("approved_through: one of the steps, or none")
    for k in ("stops",):
        bad += ["%s: unknown step %s" % (k, s) for s in h[k] if s not in known]
    for a, bs in h["next"].items():
        bad += ["next: unknown step %s" % s for s in [a] + bs if s not in known]
    if bad:
        raise _m_state.ChainError("run block: " + "; ".join(bad))
    return h


def step_pos(h, s):
    return h["steps"].index(s) if s in h["steps"] else 10 ** 6


def approved_pos(h):
    return -1 if h["approved_through"] == "none" else step_pos(h, h["approved_through"])


def plan_header(pid):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    h = _m_notify.read_json(plan_dir(pid) / "header.json", None) if pid else None
    if isinstance(h, dict) and "stops" not in h:
        # headers synced before the owner-neutral rename store the list as stop_for_hunter / stop_for_owner
        h["stops"] = list(h.get("stop_for_owner") or h.get("stop_for_hunter") or [])
    return h


def plan_state(pid):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    st = _m_notify.read_json(plan_dir(pid) / "state.json", {})
    st.setdefault("status", "idle")
    st.setdefault("ledger", {})
    st.setdefault("events", [])
    return st


def plan_txn(pid, fn):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    def modify(st):
        fn(st)  # plan callbacks historically do not veto writes with False
    def write(st):
        plan_dir(pid).mkdir(parents=True, exist_ok=True)
        _m_notify.write_json(plan_dir(pid) / "state.json", st)
    _m_state.json_txn(lambda: plan_state(pid), modify, write)


def pev(st, msg):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    st["events"].append("%s %s" % (_m_state.iso(), " ".join(msg.split())[:300]))
    del st["events"][:-60]


def plan_set(pid, status, msg, reason=None):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    def f(st):
        if st["status"] == "closed":
            pev(st, "closed plan: " + msg)
            return
        st["status"], st["since"] = status, _m_state.now()
        st["reason"] = reason or ""
        pev(st, msg)
    plan_txn(pid, f)
    _m_state.log("plan %s: %s" % (pid, msg[:300]))


def ledger_add(pid, step, task, by, parent):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    plan_txn(pid, lambda st: (st["ledger"].setdefault(step, []).append({"task": task, "by": by, "parent": parent, "t": _m_state.now()}),
                              st.update(status="running", since=_m_state.now(), reason="") if st["status"] != "closed" else None,
                              pev(st, "step %s registered as task %s by %s" % (step, task, by))))
    _m_notify.digest("plan-start", "plan %s step %s started as task %s (by %s%s)" % (pid, step, task, by, ", after " + parent if parent else ""), task)


def plan_sync(path, pid, reopen=False):
    """Copy plan `pid` from `path` into plans/<pid>/ (session side: launchd cannot read ~/Desktop). Returns the header."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    p = Path(path).expanduser()
    try:
        text = p.read_text()
    except OSError as e:
        raise _m_state.ChainError("cannot read plan file %s: %s" % (p, e))
    sec = plan_section(text, pid)
    if len(sec.encode()) > _m_state.PLAN_MAX:
        raise _m_state.ChainError("plan section %s is %d KB; keep it under %d KB (details belong in linked docs)" % (pid, len(sec.encode()) >> 10, _m_state.PLAN_MAX >> 10))
    h = parse_run_block(sec)
    if h["plan"] != pid:
        raise _m_state.ChainError("run block says plan: %s, the reference says #%s" % (h["plan"], pid))
    files, total = [], 0
    for rel in h["templates"]:
        src = (p.parent / rel).resolve()
        if not src.is_file():
            raise _m_state.ChainError("templates: %s not found next to the plan" % rel)
        total += src.stat().st_size
        files.append((Path(rel).name, src))
    if total > _m_state.PLAN_FILES_MAX:
        raise _m_state.ChainError("templates total %d KB, over %d KB" % (total >> 10, _m_state.PLAN_FILES_MAX >> 10))
    d = plan_dir(pid)
    (d / "work").mkdir(parents=True, exist_ok=True)
    shutil.rmtree(d / "files", ignore_errors=True)
    (d / "files").mkdir()
    for name, src in files:
        shutil.copyfile(src, d / "files" / name)
    (d / "plan.md").write_text(sec)
    _m_notify.write_json(d / "header.json", dict(h, source=str(p.resolve()), synced=_m_state.iso()))
    def synced(st):
        if reopen and st["status"] == "closed":
            st.update(status="running", since=_m_state.now(), reason="")
            pev(st, "reopened by plan sync --reopen")
        if st.pop("owner_wait", None):
            if st["status"] != "closed":
                st.update(status="running", since=_m_state.now(), reason="")
            pev(st, "owner wait cleared by plan sync")
            _m_notify.digest("plan-resume", "plan %s owner wait cleared by plan sync" % pid)
        st.update(activity_at=_m_state.now())
    plan_txn(pid, lambda st: (synced(st), pev(st, "synced from %s (approved through %s; stops %s)" % (p.name, h["approved_through"], ", ".join(h["stops"]) or "none"))))
    return h


def next_steps(h, from_step, ledger=None, parent=None):
    """(go, held): steps after `from_step` the continue agent may start, and [(step, why)] for those it may not.
    `parent` = the task whose continue agent is registering: tasks it already registered for a step do not hold that step, so one
    step can have several tasks (per-cell fan-outs); a step started by anyone else is still held."""
    ledger = ledger if ledger is not None else plan_state(h["plan"])["ledger"]
    if from_step in h["next"]:
        cand = h["next"][from_step]
    else:
        i = step_pos(h, from_step)
        cand = h["steps"][i + 1:i + 2] if i < len(h["steps"]) else []
    go, held = [], []
    for s in cand:
        if s in h["stops"]:
            held.append((s, "planned stop for the owner"))
        elif step_pos(h, s) > approved_pos(h):
            held.append((s, "beyond the approved range (approved through %s)" % h["approved_through"]))
        elif [e for e in ledger.get(s, []) if not (parent and e.get("by") != "session" and e.get("parent") == parent)]:
            held.append((s, "already started once (task %s); a rerun needs a session" % ledger[s][-1]["task"]))
        else:
            go.append(s)
    return go, held


def resolve_plan_path(path, raw, src_file):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    p = Path(path).expanduser()
    if p.is_absolute():
        return p
    bases = []
    code = raw.get("code") if isinstance(raw, dict) else None
    if isinstance(code, dict) and code.get("repo"):
        r = _m_task_registry.git("rev-parse", "--show-toplevel", cwd=os.path.expanduser(code["repo"]))
        if r.returncode == 0:
            bases.append(Path(r.stdout.strip()))
    bases += [Path(src_file).expanduser().resolve().parent, Path.cwd()]
    for b in bases:
        if (b / p).is_file():
            return b / p
    raise _m_state.ChainError("on_done.plan: %s not found (relative to the code repo, the task file's folder or the current folder)" % path)


def check_on_done(od, raw, src_file, by, parent):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not isinstance(od, dict) or not od.get("plan") or str(od.get("from_step") or "") == "":
        raise _m_state.ChainError('on_done: {"plan": "path/PLAN.md#plan-id", "from_step": "STEP"} (from_step = the plan step this task runs)')
    ref, step = str(od["plan"]), str(od["from_step"])
    if by == "session":
        path, _, pid = ref.partition("#")
        if not pid:
            raise _m_state.ChainError("on_done.plan: path#plan-id (the id in the plan's run block)")
        h = plan_sync(resolve_plan_path(path, raw, src_file), pid)
    else:
        pid = ref.partition("#")[2] or ref
        h = plan_header(pid)
        if not h:
            raise _m_state.ChainError("plan %s has no snapshot (register the first task from a session)" % pid)
    if plan_state(pid)["status"] == "closed":
        raise _m_state.ChainError("plan %s is closed; use plan sync PATH#ID --reopen first" % pid)
    if step not in h["steps"]:
        raise _m_state.ChainError("on_done.from_step %s is not a step of plan %s (%s)" % (step, pid, ", ".join(h["steps"])))
    if step_pos(h, step) > approved_pos(h):
        raise _m_state.ChainError("plan %s is approved through step %s; step %s is not. Record the owner's answer in the plan's run block "
                         "(approved_through) first" % (pid, h["approved_through"], step))
    if step in h["stops"]:
        raise _m_state.ChainError("step %s is a stop for the owner in plan %s: record the owner's decision in the plan and take it out of stop_for_owner first" % (step, pid))
    # v3: a step may have several tasks (per-cell fan-outs); it counts as done when all of them are (process_continuations).
    # A session may add another task to a step at any time; a continue agent only to a step it started itself in this run.
    led = plan_state(pid)["ledger"].get(step) or []
    if by != "session" and [e for e in led if not (e.get("by") != "session" and e.get("parent") == parent)]:
        raise _m_state.ChainError("step %s of plan %s was already started once (task %s); only a session may rerun it" % (step, pid, led[-1]["task"]))
    depth = 0
    if parent:
        depth = int(((_m_state.task_load(parent) or {}).get("on_done") or {}).get("depth", 0)) + 1
        if depth > len(h["steps"]):
            raise _m_state.ChainError("continuation depth %d exceeds the plan's %d steps (loop guard)" % (depth, len(h["steps"])))
    return {"plan": pid, "from_step": step, "depth": depth, "by": by, "parent": parent}


def plan_gpu_cover(od):
    """Why a GPU stage of this plan task needs no gpu_ok_until: the plan's approval (with its date) covers GPU stages of its
    approved steps (owner decision 2026-11-06). None when the task is not a plan step or the approval line has no ISO date."""
    if not od:
        return None
    h = plan_header(od["plan"]) or {}
    m = re.search(r"\d{4}-\d{2}-\d{2}", h.get("approval", ""))
    return "plan %s approved %s" % (od["plan"], m.group(0)) if m else None


def tool_next_add(n, t, rest):
    """`nrp-task next-add FILE`: the continue agent registers the next plan step. Every gate is checked here, not trusted to the prompt."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import wake as _m_wake  # Local import breaks orchestration cycle; patches stay on the defining module.
    from .task import registry as _m_task_registry  # Local import breaks orchestration cycle; patches stay on the defining module.
    cont, od = t.get("continuation") or {}, t.get("on_done") or {}
    if cont.get("state") != "running" or not od:
        sys.exit("next-add is only for the continue agent of a finished plan task")
    if len(rest) != 1:
        sys.exit("nrp-task next-add FILE   (a TASK.json you wrote under %s)" % (plan_dir(od["plan"]) / "work"))
    p = Path(rest[0]).expanduser().resolve()
    if not (p.is_relative_to(plan_dir(od["plan"]).resolve() / "work") and p.is_file()):
        sys.exit("FILE must be an existing file under %s" % (plan_dir(od["plan"]) / "work"))
    try:
        raw = _m_task_registry.load_chain_file(str(p))[0]
    except _m_state.ChainError as e:
        sys.exit("next-add refused: %s" % e)
    if not isinstance(raw, dict):
        sys.exit("next-add refused: TASK file must be an object")
    h = plan_header(od["plan"])
    step = str((raw.get("on_done") or {}).get("from_step") or "")
    go, held = next_steps(h, od["from_step"], parent=n)
    if step not in go:
        why = dict(held).get(step, "not a next step of %s" % od["from_step"])
        sys.exit("next-add refused: step %r may not be started automatically (%s). Report WAITING instead." % (step, why))
    for s in raw.get("stages") or []:
        m = s.get("manifest")
        if isinstance(m, str) and not Path(m).expanduser().resolve().is_relative_to(plan_dir(od["plan"]).resolve() / "work"):
            sys.exit("next-add refused: manifest %s must be a file you wrote under %s" % (m, plan_dir(od["plan"]) / "work"))
    hp = raw.get("handoff")
    if isinstance(hp, str) and hp and not _m_wake.handoff_path(hp, str(p)).resolve().is_relative_to(plan_dir(od["plan"]).resolve() / "work"):
        sys.exit("next-add refused: handoff %s must be a file you wrote under %s" % (hp, plan_dir(od["plan"]) / "work"))
    raw["on_done"] = {"plan": od["plan"], "from_step": step}
    raw["approved"] = ("auto-continued by the monitor after task %s, plan %s approved through step %s: %s"
                       % (n, od["plan"], h["approved_through"], h["approval"]))[:1000]
    o = t.get("origin") or {}
    raw["origin"] = {k: o[k] for k in _m_state.ORIGIN_FIELDS if o.get(k)} or None
    raw.pop("mode", None)
    carry = {k: t["code"][k] for k in ("pkg_dir", "extra_pkg_dirs") if (t.get("code") or {}).get(k)}     # what reship packs stays declared
    if t.get("code"):
        raw["code"] = dict({"repo": t["code"]["clone"], "subdir": (raw.get("code") or {}).get("subdir") or t["code"].get("subdir") or ""}, **carry)
    else:
        raw.pop("code", None)
    rc = _m_task_registry.task_add_raw(raw, str(p), by="continuation", parent=n)
    _m_state.task_txn(n, lambda t: t["continuation"].setdefault("registered", []).append(raw["name"]))
    return rc


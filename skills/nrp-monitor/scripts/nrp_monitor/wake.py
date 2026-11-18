"""NRP monitor wake (mechanical extraction; R3a)."""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


def norm_origin(raw, source="registered"):
    """Validated origin dict, or None when raw is empty. Raises ChainError on a malformed value."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if raw in (None, {}, ""):
        return None
    if not isinstance(raw, dict):
        raise _m_state.ChainError("origin: object {title, link, assistant, collaborator}")
    bad = sorted(set(raw) - set(_m_state.ORIGIN_FIELDS))
    if bad:
        raise _m_state.ChainError("origin: unknown field(s) %s (allowed: %s)" % (", ".join(bad), ", ".join(_m_state.ORIGIN_FIELDS)))
    o = {k: _m_state.one_line(raw[k], {"title": 120, "link": 300, "note": 200, "evidence": 300, "cwd": 300}.get(k, 80))
         for k in _m_state.ORIGIN_FIELDS if raw.get(k) not in (None, "")}
    if o.get("harness") and o["harness"] not in _m_state.ORIGIN_HARNESSES:
        raise _m_state.ChainError("origin.harness: one of %s (got %r)" % (", ".join(_m_state.ORIGIN_HARNESSES), o["harness"][:20]))
    if o.get("session") and not _m_state.ORIGIN_SESSION_RE.match(o["session"]):
        raise _m_state.ChainError("origin.session: a session id (letters, digits, . _ : -; 4-100 characters), got %r" % o["session"][:40])
    if o.get("session") and o.get("harness") not in ("claude", "codex"):
        raise _m_state.ChainError("origin.session needs origin.harness claude or codex (a T3 chat is reached through its webhook and link)")
    if o.get("harness") in ("claude", "codex") and not o.get("session"):
        raise _m_state.ChainError("origin.harness %s needs origin.session: the id of the chat to wake (--origin-session ID; %s is read when it is "
                         "set in this shell)" % (o["harness"], _m_state.SESSION_ENV[o["harness"]]))
    if o.get("cwd") and not (o["cwd"].startswith("/") and ".." not in o["cwd"].split("/")):
        raise _m_state.ChainError("origin.cwd: an absolute directory path without ..")
    link = o.get("link", "")
    if link.startswith("<") and link.endswith(">"):                    # T3 prints links as <t3-thread://...>
        link = o["link"] = link[1:-1]
    if link and not _m_state.ORIGIN_LINK_RE.match(link):
        raise _m_state.ChainError("origin.link: a t3-thread://... or https://... link without spaces, <, > or | (got %r)" % link[:60])
    if not o.get("title") and not link and not o.get("session"):
        raise _m_state.ChainError("origin: needs the chat title and/or its exact link (the chat a person returns to)")
    o.setdefault("collaborator", _m_state.OWNER_NAME)
    o["recorded"], o["source"] = _m_state.iso(), source
    return o


def detect_session(harness):
    """The session id of the assistant running THIS command, from its environment, or "". Used only when --origin-harness is given
    without --origin-session: the person said which harness, the id is read, never guessed from anything else. A delegated child agent has
    its own session, not the chat's, so a Claude Code child session gets a warning."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    v = os.environ.get(_m_state.SESSION_ENV.get(harness, ""), "")
    if v and harness == "claude" and os.environ.get("CLAUDE_CODE_CHILD_SESSION"):
        print("warning: CLAUDE_CODE_CHILD_SESSION is set: %s may be a delegated child agent's session, not the chat the person talks to. "
              "Pass --origin-session with the chat's own id if they differ." % _m_state.SESSION_ENV[harness], file=sys.stderr)
    return v


def origin_overlay(raw_origin, a):
    """JSON origin (dict or None) overlaid with --origin-* flags; the flags win. A claude/codex harness without a session takes the id from
    the environment of the assistant running this command, and without a cwd the current directory."""
    flags = {k: getattr(a, "origin_" + k, None) for k in ("title", "link", "assistant", "collaborator", "harness", "session", "cwd")}
    flags = {k: v for k, v in flags.items() if v}
    if raw_origin not in (None, {}) and not isinstance(raw_origin, dict):
        return raw_origin                                              # let norm_origin refuse it
    merged = dict(raw_origin or {}, **flags) if flags else raw_origin
    if isinstance(merged, dict) and merged.get("harness") in ("claude", "codex"):
        if not merged.get("session"):
            merged = dict(merged, session=detect_session(merged["harness"]))
        if not merged.get("cwd"):
            merged = dict(merged, cwd=os.getcwd())
    return merged


def add_origin_args(p):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    p.add_argument("--origin-title", help="title of the chat that owns this work (where a person returns on an alert)")
    p.add_argument("--origin-link", help="exact link of that chat, e.g. t3-thread://v2/ENV/THREAD (T3 thread_read prints it)")
    p.add_argument("--origin-assistant", help="assistant and model of that chat, e.g. 'Codex gpt-6-astra' (optional)")
    p.add_argument("--origin-collaborator", help="person the chat works with (default: the owner_name setting)")
    p.add_argument("--origin-harness", choices=_m_state.ORIGIN_HARNESSES,
                   help="where the chat runs, so the monitor wakes THAT chat: t3 (thread link or webhook), claude (Claude Code session), codex (Codex session)")
    p.add_argument("--origin-session", help="session id of the claude/codex chat to wake (default: read from CLAUDE_CODE_SESSION_ID / CODEX_THREAD_ID)")
    p.add_argument("--origin-cwd", help="directory the claude/codex chat runs in (default: the current directory); Claude Code finds sessions by it")


def require_origin_note(o, kind, name, always=False):
    """Refuse (always=True, or when NRP_MONITOR_REQUIRE_ORIGIN is set) or warn on stderr; returns nothing."""
    if o:
        return
    msg = ("%s %s has no origin: alerts will say 'origin not recorded' and the person cannot tell which chat owns it. "
           "Add \"origin\": {\"title\": ..., \"link\": ...} (or --origin-title/--origin-link) naming the chat that asked for it; "
           "for existing work: nrp-monitor origin %s %s --title ... --link ... --evidence ..." % (kind, name, kind, name))
    if always or os.environ.get("NRP_MONITOR_REQUIRE_ORIGIN"):
        sys.exit("%s refused: %s" % (kind, msg))
    print("warning: " + msg, file=sys.stderr)


def origin_plain(o, fallback=""):
    """One line for the digest, CLI and banners."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not o:
        return "%s%s" % (_m_state.ORIGIN_MISSING, " (%s)" % fallback if fallback else "")
    who = ", ".join(x for x in (o.get("assistant"), "with " + o["collaborator"] if o.get("collaborator") else "") if x)
    return "chat %s%s%s" % ('"%s"' % o["title"] if o.get("title") else "(untitled)", " (%s)" % who if who else "",
                            " " + o["link"] if o.get("link") else (" %s session %s" % (o.get("harness", ""), o["session"]) if o.get("session") else ""))


def origin_tag(o):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return "[%s]" % ((o or {}).get("title") or (o or {}).get("link") or _m_state.ORIGIN_MISSING)[:40]


def origin_slack(o, fallback=""):
    """Slack lines. The link is a literal code span: Slack does not turn a custom scheme (t3-thread://) into a
    clickable link, so the title is bold and the exact link is copyable; https links get the <url|title> form."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not o:
        return ["*%s*%s" % (_m_state.ORIGIN_MISSING, _m_state.slack_esc(" (%s)" % fallback) if fallback else "")]
    who = ", ".join(x for x in (o.get("assistant"), "working with " + o["collaborator"] if o.get("collaborator") else "") if x)
    title = o.get("title") or "(untitled chat)"
    link = o.get("link", "")
    head = "*Return to chat: %s*%s" % (("<%s|%s>" % (link, _m_state.slack_esc(title)) if link.startswith("http") else _m_state.slack_esc(title)),
                                      _m_state.slack_esc(" (%s)" % who) if who else "")
    out = [head]
    if link and not link.startswith("http"):
        out.append("`%s`" % link)
    return out


def lookup_origin(ref):
    """(origin or None, fallback text) for a ref: 'task NAME' / bare task or legacy-job name / 'chain:NAME' / 'job:NAME'."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not ref or ref == "-":
        return None, ""
    kind, _, name = ref.partition(":") if ref.startswith(("chain:", "job:", "task:")) else ("", "", ref)
    if kind in ("", "task"):
        t = _m_state.task_load(name) if _m_state.TASK_RE.match(name or "") else None
        if t:
            c = t.get("code") or {}
            return t.get("origin"), "task %s: %s%s" % (name, t.get("goal", "")[:70], "; code %s/%s" % (Path(c["repo"]).name, c.get("subdir") or ".") if c.get("repo") else "")
    if kind in ("", "job"):
        rec = _m_state.load()["jobs"].get(name)
        if rec:
            return rec.get("origin"), "job %s: %s" % (name, (rec.get("label") or "")[:70])
    return None, "%s (no such registration)" % ref


def owner_of_job(st, job):
    """Registration that owns Job `job`: 'task:NAME', 'chain:NAME', 'job:NAME' or None."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    tk = _m_state.task_of_job(job) if job else None
    if tk:
        return "task:" + tk[0]
    if job and job in st["jobs"]:
        return "job:" + job
    return None


def slack_text(body, refs):
    """Text of the Slack DM. `refs` = registrations the alert is about; empty = shared/system alert, not one chat's.
    Origin first (what a person needs to act), then the script's own attribution (mission-control skill: identify the
    speaker and collaborator). Everything dynamic is escaped."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    refs = list(dict.fromkeys(refs or []))
    lines = []
    if not refs:
        lines.append("*Not tied to one chat* (account-wide or monitor check; no single chat owns it).")
    for ref in refs[:4]:
        o, fb = lookup_origin(ref)
        pl = origin_slack(o, fb)
        lines += pl if len(refs) == 1 else ["%s %s" % (_m_state.slack_esc(ref), pl[0])] + pl[1:]
    if len(refs) > 4:
        lines.append("(+%d more registrations)" % (len(refs) - 4))
    lines.append("*NRP monitor* (automated script, working with %s; not a chat): " % _m_state.OWNER_NAME + _m_state.slack_esc(body))
    return "\n".join(lines)[:3900]


def short_tag(refs):
    """Prefix for banners and the Claude push (190 chars): the chat title(s), or 'origin not recorded'/'shared'."""
    refs = list(dict.fromkeys(refs or []))
    if not refs:
        return "[shared] "
    return "".join(origin_tag(lookup_origin(r)[0]) for r in refs[:3]) + " "


def handoff_split(text):
    """[(heading|None, body)] split at level-2 headings (`## X`), ignoring ones inside code fences. The first item is the preamble."""
    secs, fence = [[None, []]], False
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence and line.startswith("## "):
            secs.append([line[3:].strip(), []])
        else:
            secs[-1][1].append(line)
    return [(h, "\n".join(b)) for h, b in secs]


def handoff_join(secs):
    out = []
    for h, b in secs:
        b = b.strip("\n")
        if h is None:
            if b.strip():
                out.append(b)
        else:
            out.append("## %s\n\n%s" % (h, b) if b.strip() else "## %s" % h)
    return "\n\n".join(out) + "\n"


def handoff_body(secs, head):
    return next((b for h, b in secs if h == head), None)


def handoff_set(secs, head, body):
    for i, (h, _) in enumerate(secs):
        if h == head:
            secs[i] = (h, body)
            return secs
    secs.append((head, body))
    return secs


def handoff_sha(secs):
    b = handoff_body(secs, "Registrar")
    return hashlib.sha256(b.strip().encode()).hexdigest() if b is not None else None


def handoff_chars(body):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return len(" ".join(_m_state.HANDOFF_COMMENT.sub("", body or "").split()))


def handoff_path(hp, src_file):
    p = Path(str(hp)).expanduser()
    return p if p.is_absolute() else Path(src_file).expanduser().resolve().parent / p


def handoff_load(hp, src_file):
    """Check the task's `handoff` field. -> (text, thin, why). text is the normalised file (all four headings), or None when there is
    nothing usable (why says what is missing). thin: the Registrar exists but is short. ChainError: malformed (too big, duplicate headings)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if hp is None or hp == "":
        return None, False, "the task has no handoff field"
    if not isinstance(hp, str):
        raise _m_state.ChainError("handoff: path to a markdown file (absolute, ~ or relative to the task file's folder)")
    p = handoff_path(hp, src_file)
    if not p.is_file():
        return None, False, "handoff file %s does not exist" % p
    raw = p.read_bytes()
    if len(raw) > _m_state.HANDOFF_MAX_FILE:
        raise _m_state.ChainError("handoff: %s is %d KB; at most %d KB (a fresh agent reads it every time)" % (p, len(raw) // 1024, _m_state.HANDOFF_MAX_FILE // 1024))
    text = raw.decode("utf-8", "replace")
    if not text.strip():
        return None, False, "handoff file %s is empty" % p
    secs = handoff_split(text)
    for h in _m_state.HANDOFF_HEADS:
        if sum(1 for x, _ in secs if x == h) > 1:
            raise _m_state.ChainError("handoff: heading `## %s` appears twice (use ### for sub-headings inside a section)" % h)
    reg = handoff_body(secs, "Registrar")
    if reg is None:
        return None, False, "handoff file %s has no `## Registrar` heading" % p
    if len(reg.strip()) > _m_state.HANDOFF_MAX_REG:
        raise _m_state.ChainError("handoff: the ## Registrar section is %d characters; at most %d (what the next agent needs, not a log)" % (len(reg.strip()), _m_state.HANDOFF_MAX_REG))
    for h in _m_state.HANDOFF_HEADS:
        if handoff_body(secs, h) is None:
            secs.append((h, ""))
    n = handoff_chars(reg)
    thin = n < _m_state.HANDOFF_MIN_REG
    return handoff_join(secs), thin, ("its ## Registrar section is thin (%d characters of text, at least %d expected)" % (n, _m_state.HANDOFF_MIN_REG)) if thin else ""


def handoff_escalation_missing(text):
    """True when an accepted handoff's Registrar never says who handles failures (the monitor's subagents first, the chat as a last resort,
    the owner last). A warning only: the Registrar is the registering agent's own text."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    reg = _m_state.HANDOFF_COMMENT.sub("", handoff_body(handoff_split(text), "Registrar") or "")
    return not _m_state.HANDOFF_ESC_RE.search(reg)


def handoff_write(path, text):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def handoff_attach(t, text, thin, source):
    """Write the task's handoff.md and handoff.orig.md and record them in the task (called before task_write / inside task_txn)."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    d = _m_state.task_dir(t["name"])
    d.mkdir(parents=True, exist_ok=True)
    handoff_write(d / "handoff.md", text)
    handoff_write(d / "handoff.orig.md", text)
    t["handoff"] = {"registrar_sha256": handoff_sha(handoff_split(text)), "thin": thin, "added": _m_state.now(), "source": str(source)}
    _m_state.tev(t, "handoff accepted (%d characters in the Registrar%s)" % (handoff_chars(handoff_body(handoff_split(text), "Registrar")), ", thin" if thin else ""))


def handoff_clean(s, limit):
    """Agent text for the file: control characters out, nothing that can open a heading, a fence or a comment (an entry must not
    be able to start a new section or hide the rest of the file)."""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s.replace("\r\n", "\n")).replace("<!--", "<! --")
    lines = []
    for l in s.split("\n"):
        l = l.rstrip()
        if "```" in l:
            l = l.replace("```", "'''")
        if l.startswith("#"):
            l = "\\" + l
        lines.append(l)
    s = "\n".join(lines).strip()
    return s if len(s) <= limit else s[:limit - 3].rstrip() + "..."


def handoff_extract(text):
    """(entry|None, [owner lines]) from an agent's final answer: what follows the LAST `HANDOFF_ENTRY:` line. A `FOR_OWNER:` line inside
    the block is returned separately and removed from the entry."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    ms = list(_m_state.HANDOFF_ENTRY_RE.finditer(text or ""))
    if not ms:
        return None, []
    m = ms[-1]
    block = (m.group(1) + "\n" + text[m.end():]).replace("\r\n", "\n")
    keep, owner = [], []
    for l in block.split("\n"):
        if l.strip().startswith("```") and l.strip().strip("`") == "":
            continue                                                  # a closing code fence around the block
        o = _m_state.HANDOFF_OWNER_RE.match(l)
        if o:
            if o.group(1).strip():
                owner.append(o.group(1).strip())
        else:
            keep.append(l)
    entry = "\n".join(keep).strip()
    return (handoff_clean(entry, _m_state.HANDOFF_ENTRY_MAX) or None), [handoff_clean(x, _m_state.HANDOFF_OWNER_MAX) for x in owner[:5]]


def handoff_append(t, header, adds):
    """Inside a task transaction. adds = [(section, text)]. Writes the file atomically; the Registrar's hash must be unchanged before
    and after: a changed one (an agent edited the file) is restored from handoff.orig.md and logged. Never raises."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    h = t.get("handoff")
    if not h:
        return
    d = _m_state.task_dir(t["name"])
    p, o, want = d / "handoff.md", d / "handoff.orig.md", h["registrar_sha256"]
    try:
        secs = handoff_split(p.read_text())
    except OSError:
        secs = None
    if secs is None or handoff_sha(secs) != want:
        what = "handoff.md is missing" if secs is None else "the Registrar section was changed"
        try:
            osecs = handoff_split(o.read_text())
        except OSError:
            osecs = None
        if osecs is None or handoff_sha(osecs) != want:
            _m_state.tev(t, "handoff: %s and the original cannot restore it; nothing was appended" % what)
            _m_state.log("task %s: handoff %s and handoff.orig.md does not match either" % (t["name"], what))
            _m_notify.digest("fault", "handoff Registrar for %s is damaged and could not be restored (%s); nothing appended" % (t["name"], what), t["name"])
            return
        secs = osecs if secs is None else handoff_set(secs, "Registrar", handoff_body(osecs, "Registrar"))
        _m_state.tev(t, "handoff: %s; Registrar restored from handoff.orig.md" % what)
        _m_state.log("task %s: handoff %s; Registrar restored" % (t["name"], what))
        _m_notify.digest("fault", "handoff Registrar for %s was changed by an agent and restored from the original" % t["name"], t["name"])
    before = handoff_join(secs)
    for head, text in adds:
        secs = handoff_set(secs, head, (handoff_body(secs, head) or "").rstrip("\n") + "\n\n### %s\n%s" % (header, text))
    after = handoff_join(secs)
    if handoff_sha(handoff_split(after)) != want:                    # cannot happen unless this code is wrong; keep the file as it was
        _m_state.tev(t, "handoff: Registrar hash changed by an append; the append was dropped")
        _m_state.log("task %s: handoff append changed the Registrar hash; dropped" % t["name"])
        handoff_write(p, before)
        return
    handoff_write(p, after)


def handoff_record(n, kind, full, rec, ctx):
    """After a fix / continue agent ran: append its HANDOFF_ENTRY block (or an automatic line) to its own section; FOR_OWNER lines go
    to `## For the owner`."""
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_state.task_load(n)
    if not t or not t.get("handoff") or kind not in _m_state.HANDOFF_APPEND:
        return
    entry, owner = handoff_extract(full)
    rep = t.get("report") or {}
    attempt = sum(1 for r in t.get("agent_runs", []) if r["kind"] == kind)
    if not entry:
        bits = ["failure class %s on stage %s" % (ctx.get("cls", "?"), ctx.get("stage", "?"))] if ctx else []
        bits.append("report %s: %s" % (rep["status"], rep.get("line", "")) if rep else "no nrp-task report")
        bits.append("agent said: %s" % (rec.get("result") or "(nothing)")[:200])
        entry = handoff_clean("(automatic entry: the agent returned no HANDOFF_ENTRY block) " + "; ".join(bits), _m_state.HANDOFF_ENTRY_MAX)
    when = datetime.fromtimestamp(_m_state.now(), timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = "%s | %s agent | attempt %d%s" % (when, kind, attempt, (" | [%s] stage %s" % (ctx.get("cls", "?"), ctx.get("stage", "?"))) if ctx else "")
    adds = [(_m_state.HANDOFF_APPEND[kind], entry)]
    if owner:
        adds.append(("For the owner", "\n".join("- " + x for x in owner)))
    _m_state.task_txn(n, lambda t: handoff_append(t, header, adds))
    if owner:
        _m_notify.digest("handoff-owner", "%s agent asks the owner: %s" % (kind, " / ".join(owner)[:400]), n)


def handoff_prompt(t):
    """Handoff text for an agent prompt: the Registrar whole, the newest log entries of each append section within the cap."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if not t.get("handoff"):
        return _m_state.HANDOFF_NONE
    d = _m_state.task_dir(t["name"])
    try:
        secs = handoff_split((d / "handoff.md").read_text())
    except OSError:
        return _m_state.HANDOFF_NONE
    reg = handoff_body(secs, "Registrar")
    if reg is None or handoff_sha(secs) != t["handoff"]["registrar_sha256"]:       # edited since: show the original
        try:
            reg = handoff_body(handoff_split((d / "handoff.orig.md").read_text()), "Registrar") or reg or ""
        except OSError:
            reg = reg or ""
    reg = _m_state.HANDOFF_COMMENT.sub("", reg).strip()
    per = max(1500, (_m_state.HANDOFF_PROMPT_MAX - len(reg)) // 3)
    out = ["== Registrar (written once by the agent that registered the task; read-only) ==\n" + reg]
    for head in _m_state.HANDOFF_HEADS[1:]:
        body = _m_state.HANDOFF_COMMENT.sub("", handoff_body(secs, head) or "")
        ents = [e.strip() for e in re.split(r"(?m)^(?=### )", body) if e.strip().startswith("### ")]
        keep, size = [], 0
        for e in reversed(ents):
            if keep and size + len(e) > per:
                break
            keep.append(e[:per])
            size += len(e)
        keep.reverse()
        note = "[%d older entr%s omitted; the full file is %s]\n" % (len(ents) - len(keep), "y" if len(ents) - len(keep) == 1 else "ies",
                                                                     d / "handoff.md") if len(ents) > len(keep) else ""
        out.append("== %s (appended by the monitor from agents' answers and coordinator decisions) ==\n%s%s" % (head, note, "\n\n".join(keep) or "(no entries yet)"))
    return "\n\n".join(out)


def wake_target(t):
    """Resume a recorded session, use the preferred T3 webhook, or send to the recorded T3 thread through its CLI."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    o = t.get("origin") or {}
    session = None
    if o.get("harness") in ("claude", "codex") and o.get("session"):
        session = {"harness": o["harness"], "session": o["session"], "cwd": o.get("cwd") or "", "task": t["name"]}
    link = str(o.get("link") or "").strip().strip("<>")
    match = re.fullmatch(r"t3-thread://v2/[^/\s]+/([^/\s]+)", link)
    if match and session:
        # Hunter 2026-11-16: a headless resume never shows in the T3 chat, so a wake that needed him sat unseen. A T3 send is a visible
        # turn in that chat with its normal tools (it can finish the fix); the headless resume is only the fallback when T3 is down.
        return {"harness": "t3-cli", "session": match.group(1), "fallback": session}
    if session:
        return session
    if (_m_state.STATE / "webhooks" / t["name"]).exists():
        return {"harness": "t3"}
    if match:
        return {"harness": "t3-cli", "session": match.group(1)}
    return None


def queue_task_webhook(t, kind, **extra):
    """Called inside the task transaction, so the event and transition are atomic. `extra` (the `summary`) joins the event. The event goes
    to the task's wake target: the T3 webhook, or a Claude Code / Codex session resumed non-interactively (process_task_webhooks)."""
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    if wake_target(t):
        generation = uuid.uuid4().hex
        event = dict({"task": t["name"], "event_type": kind, "event_id": generation, "generation": generation}, **extra)
        t.setdefault("webhook_outbox", []).append(event)
        f = t.get("failure") or {}
        _m_decisions.cost_event(t["name"], "coordinator_wake", "coordinator", "escalated" if kind != "done" else "done",
                   stage=f.get("stage"), event_id=generation, wake_kind=kind, fingerprint=f.get("fingerprint"))
        return event["event_id"]


def webhook_config(n):
    """Only an owner-only regular file can supply config; never log its contents."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    p = _m_state.STATE / "webhooks" / n
    fd = os.open(str(p), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077 or st.st_size > 4096:
            raise ValueError("invalid webhook file")
        with os.fdopen(fd, "r") as f:
            fd = -1
            config = json.load(f)
        url, workstream = config["url"], config["workstream"]
        if not isinstance(workstream, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", workstream):
            raise ValueError("invalid workstream")
        u = urllib.parse.urlsplit(url)
        if not u.hostname or u.username or u.password or u.fragment or (u.scheme != "https" and not
                (u.scheme == "http" and u.hostname in ("127.0.0.1", "::1", "localhost"))):
            raise ValueError("invalid webhook URL")
        return url, workstream
    finally:
        if fd != -1:
            os.close(fd)


class NoWebhookRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def wake_failed(n, event, why):
    """A wake delivery failed (webhook, or a session resume). Count it on the event. After WAKE_MAX_TRIES passes the wake is given up: when
    the task waits on its coordinator chat (Tier 3) it falls back to NEEDS_OWNER so the escalation is never silently lost; any other wake
    (a step's done wake) is dropped with a digest fault line instead of being retried forever."""
    from . import ladder as _m_ladder  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    out = {}

    def f(t):
        eid = event.get("event_id")
        if not any(e.get("event_id") == eid for e in t.get("webhook_outbox") or []):
            return False
        tries = t.setdefault("wake_tries", {})                 # counted beside the outbox, so the delivered payload stays exactly the event
        tries[eid] = out["tries"] = tries.get(eid, 0) + 1
        if out["tries"] >= _m_state.WAKE_MAX_TRIES:
            t["webhook_outbox"] = [e for e in t.get("webhook_outbox") or [] if e.get("event_id") != eid]
            tries.pop(eid, None)
            _m_state.tev(t, "wake %s given up after %d failed deliveries: %s" % (event.get("event_type"), out["tries"], why))
            if event.get("event_type") == "escalation" and t.get("status") == "WITH_COORDINATOR":
                out["reason"] = t.get("reason", "")
            else:
                out["dropped"] = True
    _m_state.task_txn(n, f)
    if event.get("event_type") == "gpu_warning" and out.get("tries") == 1:   # a GPU alarm cannot wait ~30 min of retries: tell the owner now
        _m_notify.push("GPU ALARM NOT DELIVERED to the chat (%s); act yourself: %s" % (why[:40], event.get("summary") or ""),
             "gpu-warn-undelivered:%s" % event.get("event_id"), refs=["task:" + n])
    if out.get("reason") is not None:
        _m_ladder.escalate(n, "the coordinator chat could not be woken (delivery failed %d passes in a row: %s). %s" % (out["tries"], why, out["reason"]))
    elif out.get("dropped"):
        _m_notify.digest("fault", "the %s wake for the coordinator chat was not delivered after %d tries (%s); it is dropped. `nrp-monitor task show %s`"
               % (event.get("event_type"), out["tries"], why, n), n)


class WakeError(Exception):
    pass


def wake_tools(target):
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    tools = list(_m_state.WAKE_TOOLS) + ["Bash(nrp-task:*)", "PushNotification", "Grep", "Glob"] + _m_state.WAKE_GIT
    state = str(_m_state.STATE.resolve())
    tools += ["Read(/%s/**)" % state]
    for sub in ("tasks", "plans"):
        tools += ["Edit(/%s/%s/**)" % (state, sub), "Write(/%s/%s/**)" % (state, sub)]
    cwd = target.get("cwd") or ""
    if cwd and os.path.isabs(cwd) and os.path.isdir(cwd) and os.path.realpath(cwd) != os.path.realpath(str(Path.home())):
        cwd = os.path.realpath(cwd)
        tools += ["Read(/%s/**)" % cwd, "Edit(/%s/**)" % cwd, "Write(/%s/**)" % cwd]
    return tools


def wake_text(t, event, harness="claude"):
    """What a resumed claude/codex chat or a T3 thread reads (a T3 relay composes its own text from the event). Short: summary, pointers and the commands."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    n, kind = t["name"], event.get("event_type")
    if event.get("summary"):
        body = event["summary"]
    elif kind == "done":
        body = ("NRP task %s finished: all %d stage(s) succeeded and their success markers exist. Look: `nrp-monitor task show %s`; "
                "its handoff is %s." % (n, len(t.get("stages") or []), n, _m_state.task_dir(n) / "handoff.md"))
    elif kind == "failure":
        f = t.get("failure") or {}
        body = "NRP task %s: stage %s failed [%s] %s. Look: `nrp-monitor task show %s`." % (n, f.get("stage"), f.get("cls"), (f.get("detail") or "")[:200], n)
    else:
        body = "NRP task %s: %s event. Look: `nrp-monitor task show %s`." % (n, kind, n)
    if kind == "gpu_warning":
        return ("[NRP monitor GPU ALARM: automated, from the monitor script, not from the owner. Highest priority: handle this before anything "
                "else in this chat.]\n%s\nThis is not a judgment call: stopping the Job is required. After you have deleted it and recorded what "
                "must change (LOG/PLAN beside the work), run `nrp-monitor wake-review %s --by coordinator --why TEXT`. Resubmit only with the "
                "changed design and inside the plan's approval; if the redesign is a decision that is Hunter's, say so in one line and use "
                "`nrp-monitor task needs-owner`." % (body, n))[:3000]
    if kind == "red_alert":
        return ("[NRP monitor RED ALERT: automated, from the monitor script, not from the owner. Highest priority: handle this before "
                "anything else in this chat.]\n%s\nAct in this turn: resize or delete the pods, or hand each pod that is not yours to its real "
                "owner with `t3 thread send`. Then record `nrp-monitor wake-review %s --by coordinator --why TEXT`." % (body, n))[:3000]
    head = ("[NRP monitor wake: an automated message from the monitor script, not from the owner. The monitor's own subagents already handled "
            "what they could; you are woken as a last resort, and the owner only after you.]\n")
    tail = ("\nUse your judgment on what to do next. "
            "Usually you can and should keep going now, in this turn: no later turn follows this message, so work you defer will not happen "
            "until someone asks. After handling this wake, record `nrp-monitor wake-review %s --by rule|agent|coordinator --why TEXT`. Continue the plan's next steps inside its approved range and the task's approval (review outputs, fix, "
            "resume, register the next step). Stop only at a stop_for_hunter step, a decision that is Hunter's, or a fix that needs "
            "tools you do not have here; then say in one line what is needed, and use `nrp-monitor task needs-owner` only if he must act.\n" % n) + (
               "This wake is a visible turn in the owner's T3 chat with this chat's normal tools: finish the whole fix yourself (rebuild and "
               "upload pinned code, edit the manifest, resume). If you still cannot finish, put \"NEEDS YOU:\" and the one thing needed at the "
               "top of your reply; the owner sees this chat." if harness == "t3-cli" else
               "Tools in a Claude wake: `nrp-task` (NRP_TASK is set: logs, s3 ls/cat, reship, submit, code-test/commit/ship), Read/Edit/Write in "
               "this task's state folder and this chat's repo, git commit/push to main there, PushNotification. If you cannot finish, put "
               "\"NEEDS YOU:\" and the one thing needed at the top of your reply; this headless reply is not visible in T3, so the monitor "
               "DMs the owner that line.")
    return head + body[:3000 - len(head) - len(tail)] + tail     # trim the summary, never the instructions


def wake_argv(target):
    if target["harness"] == "claude":      # --resume: the same session, so the wake lands in that chat's history; --no-session-persistence is NOT used
        return ["claude", "-p", "--resume", target["session"], "--permission-mode", "dontAsk", "--output-format", "json",
                "--allowedTools"] + wake_tools(target)
    return ["codex", "exec", "resume", "--all", "--skip-git-repo-check", target["session"], "-"]     # prompt on stdin; no --ephemeral (it must persist)


def claude_session_open(session):
    """Conservative guard: headless resume forks when the coordinator is interactive."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    try:
        r = subprocess.run(["ps", "-axo", "command="], capture_output=True, text=True, timeout=10)
        if r.returncode:
            return True  # cannot prove the session closed
        for line in r.stdout.splitlines():
            if "claude" in line and re.search(r"(?:--resume(?:=|\s+)|--session-id(?:=|\s+))" + re.escape(session) + r"(?:\s|$)", line):
                return True
        root = Path.home() / ".claude" / "projects"
        return any(_m_state.now() - p.stat().st_mtime < 300 for p in root.glob("*/%s.jsonl" % session))
    except (OSError, subprocess.TimeoutExpired):
        return True


def wake_session(target, text, timeout=None):
    """Resume the owner's own claude / codex session non-interactively with the wake text, so it lands in that chat's history (never a new
    thread). Raises WakeError with a short reason; the caller counts it toward WAKE_MAX_TRIES."""
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    h = target["harness"]
    if h == "claude" and claude_session_open(target["session"]):
        raise WakeError("claude coordinator session is open or recently active; deferred to avoid a fork")
    cwd = target.get("cwd") if target.get("cwd") and os.path.isdir(target["cwd"]) else str(Path.home())
    binary = wake_binary(h)
    env = _m_agents.clean_env()
    if target.get("task"):
        env["NRP_TASK"] = target["task"]                                 # nrp-task acts on this task only
    try:
        r = subprocess.run([binary] + wake_argv(target)[1:], input=text, capture_output=True, text=True, cwd=cwd, env=env, timeout=timeout or _m_state.WAKE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise WakeError("%s resume timed out after %ds" % (h, timeout or _m_state.WAKE_TIMEOUT_S))
    except OSError as e:
        raise WakeError("%s could not start (%s)" % (h, type(e).__name__))
    out = (r.stdout or "").strip()
    err = " ".join((r.stderr or out).split())[-160:]
    if _m_agents.limit_hit(r.returncode, r.stdout, r.stderr):
        raise WakeError("%s is out of usage" % h)
    if r.returncode:
        raise WakeError("%s resume failed (rc %d): %s" % (h, r.returncode, err))
    if h == "claude" and out.startswith("{"):
        try:
            res = json.loads(out)
        except ValueError:
            return
        if res.get("is_error"):
            raise WakeError("claude resume reported an error: %s" % " ".join(str(res.get("result") or "").split())[:160])
        return res


def wake_test_mode():
    """Scratch state never discovers installed wake clients, even if a harness forgets its environment guard."""
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    return bool(os.environ.get("NRP_MONITOR_TESTING")) or _m_state.STATE.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())


def wake_binary(harness):
    """Tests may execute only an explicit binary. Normal installs retain CLI discovery."""
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    if os.environ.get("NRP_MONITOR_NO_WAKE"):
        raise WakeError("wake delivery disabled")
    override = os.environ.get("NRP_MONITOR_%s_BIN" % harness.upper())
    if override:
        return override
    if wake_test_mode():
        raise WakeError("test wake requires an explicit %s binary" % harness)
    if harness == "t3":
        local = Path.home() / ".t3/bin/t3"
        if local.is_file():
            return str(local)
    binary = shutil.which(harness, path=_m_agents.clean_env().get("PATH"))
    if not binary:
        raise WakeError("%s binary unavailable" % harness)
    return binary


def wake_t3(target, text):
    from . import agents as _m_agents  # Local import breaks orchestration cycle; patches stay on the defining module.
    binary = wake_binary("t3")
    try:
        r = subprocess.run([binary, "thread", "send", target["session"], "-"], input=text,
                           capture_output=True, text=True, env=_m_agents.clean_env(), timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise WakeError("t3 unavailable (%s)" % type(e).__name__)
    if r.returncode:
        raise WakeError("t3 unavailable (rc %d)" % r.returncode)


WAKE_EXEC = {"claude": wake_session, "codex": wake_session, "t3-cli": wake_t3}     # tests replace these; the T3 relay is the webhook path below


def process_task_webhooks(a, st):
    from . import decisions as _m_decisions  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    from . import state as _m_state  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.dry_run or os.environ.get("NRP_MONITOR_NO_WAKE"):
        return
    opener = urllib.request.build_opener(NoWebhookRedirect())
    for n in _m_state.task_names():
        t = _m_state.task_load(n) or {}
        target = wake_target(t) or {"harness": "t3"}                   # no target: the webhook path fails and is counted like any failed wake
        for event in (t.get("webhook_outbox") or [])[:10]:
            current = _m_state.task_load(n) or {}
            if (current.get("status") == "cancelled" and event.get("event_type") != "plan-fallback") or (current.get("status") == "done" and event.get("event_type") not in ("done", "plan-fallback")):
                def discard(cur):
                    cur["webhook_outbox"] = [e for e in cur.get("webhook_outbox", []) if e.get("event_id") != event["event_id"]]
                    (cur.get("wake_tries") or {}).pop(event["event_id"], None)
                    _m_state.tev(cur, "ignored queued %s wake for terminal task" % event.get("event_type"))
                _m_state.task_txn(n, discard)
                _m_notify.digest("wake-ignored", "queued %s wake for terminal task" % event.get("event_type"), n)
                continue
            try:
                usage = None
                if target["harness"] in WAKE_EXEC:                       # t3-cli: visible T3 turn; claude / codex: resume that session
                    try:
                        used = target
                        usage = WAKE_EXEC[target["harness"]](target, wake_text(t, event, target["harness"]))
                    except WakeError as first:
                        if not target.get("fallback"):
                            raise
                        _m_state.log("task %s t3 wake failed (%s); falling back to the headless session" % (n, first))
                        used = target["fallback"]
                        usage = WAKE_EXEC[used["harness"]](used, wake_text(t, event, used["harness"]))
                    reply = str((usage or {}).get("result") or "") if isinstance(usage, dict) else ""
                    if used["harness"] != "t3-cli" and reply.lstrip().startswith("NEEDS YOU:"):
                        # A headless reply is invisible in T3: tell the owner now instead of after the 24h coordinator timeout.
                        _m_notify.push("coordinator chat could not finish: " + reply.strip(), "needs-you:%s:%s" % (n, event["event_id"]), refs=["task:" + n])
                else:
                    url, workstream = webhook_config(n)
                    payload = dict(event, workstream=workstream)
                    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                                 headers={"Content-Type": "application/json", "User-Agent": _m_state.WEBHOOK_USER_AGENT}, method="POST")
                    with opener.open(req, timeout=5) as response:
                        if not 200 <= response.status < 300:
                            raise ValueError("delivery failed")
            except Exception as e:
                if isinstance(e, WakeError):
                    why = str(e)
                else:
                    why = ("HTTP %s" % e.code) if isinstance(e, urllib.error.HTTPError) else type(e).__name__
                    if isinstance(e, urllib.error.URLError) and not isinstance(e, urllib.error.HTTPError):
                        why += " (%s)" % type(e.reason).__name__
                _m_state.log("task %s %s wake delivery failed: %s; will retry" % (n, target["harness"], why))
                wake_failed(n, event, why)
                break
            usage = usage if isinstance(usage, dict) else {}
            _m_decisions.cost_event(n, "coordinator_result", "coordinator", "done", runner=target["harness"],
                       model=usage.get("model"), result=usage, event_id=event["event_id"], wake_kind=event.get("event_type"))
            def ack(t):
                t["webhook_outbox"] = [e for e in t.get("webhook_outbox", []) if e.get("event_id") != event["event_id"]]
                (t.get("wake_tries") or {}).pop(event["event_id"], None)
                _m_state.tev(t, "wake delivered: %s via %s" % (event.get("event_type"), target["harness"]))
            _m_state.task_txn(n, ack)


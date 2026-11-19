"""The one "main chat": the only chat whose session-start status shows global notices (bad nodes, runners out of usage,
tasks that need the owner). Stored as `main_chat` in <state>/config.json; other chats see only their own items."""
import os
import sys

from . import notify as _m_notify
from . import state as _m_state


def _path():
    return _m_state.STATE / "config.json"


def load():
    """The stored main chat dict, or None. Read from disk each time (the cached OWNER dict is from import time)."""
    rec = _m_notify.read_json(_path(), {}).get("main_chat")
    return rec if isinstance(rec, dict) and rec else None


def _store(rec):
    """Atomically set (dict) or remove (None) main_chat, keeping every other config key."""
    _m_state.STATE.mkdir(parents=True, exist_ok=True)
    cfg = _m_notify.read_json(_path(), {})
    cfg = cfg if isinstance(cfg, dict) else {}
    if rec:
        cfg["main_chat"] = rec
    else:
        cfg.pop("main_chat", None)
    _m_notify.write_json(_path(), cfg)


def plain(rec):
    if not rec:
        return "none"
    return "%s (%s)" % (rec.get("title") or rec.get("link") or rec.get("session") or "untitled", rec.get("link") or "session %s" % rec.get("session"))


def is_main(here=None):
    """True when this chat (its session ids) is the stored main chat."""
    from . import cli as _m_cli  # Local import breaks orchestration cycle; patches stay on the defining module.
    here = _m_cli.session_ids() if here is None else here
    rec = load()
    return bool(rec and here and _m_cli.origin_ids(rec) & here)


def acting_by(a=None):
    return (getattr(a, "by", None) or os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CODEX_THREAD_ID") or "cli")


def set_main(link=None, session=None, title=None, by="cli"):
    rec = {"set_at": _m_state.iso(), "by": by}
    if link:
        rec["link"] = link
    if session:
        rec["session"] = session
    if title:
        rec["title"] = _m_state.one_line(title, 120)
    old = load()
    _store(rec)
    _m_state.log("main chat %s -> %s by %s" % (plain(old), plain(rec), by))
    return old, rec


def transfer(old_origin, new_origin, by="cli"):
    """`origin --replace` moved work from old_origin's chat to new_origin's: when old was the main chat, the main chat moves too.
    Returns a one-line message, or None when nothing moved."""
    from . import cli as _m_cli  # Local import breaks orchestration cycle; patches stay on the defining module.
    cur = load()
    old_ids, new_ids = _m_cli.origin_ids(old_origin), _m_cli.origin_ids(new_origin)
    if not cur or not (_m_cli.origin_ids(cur) & old_ids) or (old_ids and new_ids == old_ids):
        return None
    if not new_ids:
        return "main chat NOT moved: the new origin has no link or session (set it with `nrp-monitor main-chat --link ...`)"
    new_origin = new_origin or {}
    old, rec = set_main(link=new_origin.get("link"), session=new_origin.get("session"), title=new_origin.get("title"), by=by)
    return "main chat moved with the work: %s -> %s" % (plain(old), plain(rec))


def cmd_main_chat(a):
    from . import cli as _m_cli  # Local import breaks orchestration cycle; patches stay on the defining module.
    if a.clear and (a.here or a.link or a.title):
        sys.exit("main-chat: --clear takes no other option")
    if a.title and not (a.here or a.link):
        sys.exit("main-chat: --title goes with --here or --link")
    if not (a.here or a.link or a.clear):
        print("main chat: %s" % plain(load()))
        rec = load()
        if rec:
            print("set %s by %s" % (rec.get("set_at", "?"), rec.get("by", "?")))
        else:
            print("no main chat: no chat sees global notices at session start (set one with `nrp-monitor main-chat --here`)")
        return 0
    if a.clear:
        old = load()
        _store(None)
        _m_state.log("main chat %s -> none by %s" % (plain(old), acting_by(a)))
        print("main chat cleared (was %s)" % plain(old))
        return 0
    link = (a.link or "").strip().strip("<>") or None
    if link and not _m_state.ORIGIN_LINK_RE.match(link):
        sys.exit("main-chat: --link must be a t3-thread://... or https://... link without spaces, <, > or |")
    session = None
    if a.here:
        ids = _m_cli.session_ids()
        if not ids:
            sys.exit("main-chat --here: this chat's id is unknown (no T3CODE_THREAD_ID, CLAUDE_CODE_SESSION_ID or CODEX_THREAD_ID); use --link")
        # The T3 thread id is the chat's stable identity; a Claude/Codex session id is the fallback.
        session = next((os.environ[k].strip() for k in ("T3CODE_THREAD_ID", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID") if os.environ.get(k, "").strip()), None)
    old, rec = set_main(link=link, session=session, title=a.title, by=acting_by(a))
    print("main chat set: %s (was %s)" % (plain(rec), plain(old)))
    if a.here and not link:
        print("no T3 link recorded (it cannot be read from the environment); matching uses this chat's id")
    return 0

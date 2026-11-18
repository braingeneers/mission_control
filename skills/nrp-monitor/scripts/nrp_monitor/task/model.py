"""Task status machine: every status change goes through `transition`, checked against TRANSITIONS."""

from .. import state as _m_state

LIVE, HELD = _m_state.TASK_LIVE, _m_state.TASK_HELD
TERMINAL = ("done", "failed", "cancelled")       # "failed" is never entered; older task files may still hold it

_MOVES = {                                        # event: (statuses it may leave, status it enters)
    "submit": (LIVE + HELD, "running"),           # a Job was applied (retrying stays retrying, below)
    "resubmit": (LIVE + HELD, "retrying"),        # a failed stage was applied again
    "block": (LIVE + HELD, "blocked"),            # the submit was refused or held (quota, utilization, RED ALERT)
    "release": (LIVE + HELD, "running"),          # a hold is answered or cleared; queued escalation wakes are dropped
    "escalate": (LIVE + ("WITH_COORDINATOR", "failed"), "NEEDS_OWNER"),
    "coordinate": (LIVE + ("failed",), "WITH_COORDINATOR"),
    "finish": (LIVE, "done"),
    "cancel": (LIVE + HELD + TERMINAL, "cancelled"),
}
TRANSITIONS = {s: {e: to for e, (src, to) in _MOVES.items() if s in src} for s in LIVE + HELD + TERMINAL}
TRANSITIONS["retrying"]["submit"] = "retrying"


class IllegalTransition(Exception):
    pass


def can(t, event):
    return event in TRANSITIONS.get(t.get("status"), {})


def transition(t, event, why=None, **fields):
    """Move task `t` by `event`, set `fields`, and record `why` as a task event. Raises IllegalTransition."""
    nxt = TRANSITIONS.get(t.get("status"), {}).get(event)
    if nxt is None:
        raise IllegalTransition("task %s: %s is not allowed from %s" % (t.get("name"), event, t.get("status")))
    t["status"] = nxt
    t.update(fields)
    if event == "release":
        t["webhook_outbox"] = [e for e in t.get("webhook_outbox") or [] if e.get("event_type") != "escalation"]
    if why:
        _m_state.tev(t, why)
    return nxt


def resize_advice(line):
    out = []
    for kind, use, req, pct, mx in _m_state.FLAG_RES.findall(line):
        use, req = float(use), float(req)
        peak = float(mx) if mx else use
        if kind == "mem":
            new = max(1, -(-peak * 1.5 // 1))
            if new < req:                                                    # no advice when it would not shrink
                out.append("memory %gGi -> %dGi (peak %.1fGi)" % (req, new, peak))
        elif kind == "cpu":
            out.append("cpu %g -> %g (mean %.2f)" % (req, max(0.5, -(-peak * 3 // 1) / 2), use))
        else:
            out.append("gpu at %s%% of %g GPU: run on CPU or bundle more work per GPU" % (pct, req))
    return "; ".join(out) or "see the flag line"


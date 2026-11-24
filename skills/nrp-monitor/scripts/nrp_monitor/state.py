"""NRP monitor state (mechanical extraction; R3a)."""
import contextlib
import fcntl
import getpass
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path


NS = "braingeneers"


for _k in [k for k in os.environ if k.startswith("NRP_WATCHDOG_")]: os.environ.setdefault("NRP_MONITOR_" + _k[13:], os.environ[_k])   # former variable names, honored silently when the new one is unset


def default_state_dir():
    """~/.local/state/nrp-monitor; only when that does not exist yet and a real old nrp-watchdog dir does (install.sh has not migrated it
    yet) is the old dir used, so a pass never splits its state in two."""
    base = Path.home() / ".local/state"
    old = base / "nrp-watchdog"
    return old if not (base / "nrp-monitor").exists() and old.is_dir() and not old.is_symlink() else base / "nrp-monitor"


STATE = Path(os.environ.get("NRP_MONITOR_STATE") or default_state_dir())   # env: tests


def _owner_cfg():
    """Who this installation works for: <state>/config.json, each key overridable by an environment variable. Keys:
    nrp_user_annotation (the nrp.ai/username annotation value on your pods, e.g. http://cilogon.org/serverE/users/NNNN),
    slack_user_id (the Slack user who gets the one DM), owner_label (label value on the monitor's own check Jobs), owner_name (how messages and agent prompts name you),
    skip_limit_fraction (optional; the share of skipped items above which a failure goes to you; default 0.05),
    tier0_mem_cap_gi (optional; the largest memory in GiB the Tier 0 OOM rule may set without asking an agent; default 128),
    util_waiver_max (optional; how many util waivers one task may get before the owner is asked; default 3; 0 = never waive),
    util_waiver_hours (optional; how long one waiver lasts; default 6)."""
    try:
        c = json.loads((STATE / "config.json").read_text())
        return c if isinstance(c, dict) else {}
    except (OSError, ValueError):
        return {}


OWNER = _owner_cfg()

USER_ANN = os.environ.get("NRP_MONITOR_USER_ANNOTATION") or OWNER.get("nrp_user_annotation") or ""

OWNER_LABEL = os.environ.get("NRP_MONITOR_OWNER_LABEL") or OWNER.get("owner_label") or getpass.getuser()

OWNER_NAME = os.environ.get("NRP_MONITOR_OWNER_NAME") or OWNER.get("owner_name") or OWNER_LABEL      # how messages and agent prompts name the person

JOBS, LOG, LOCK = STATE / "jobs.json", STATE / "monitor.log", STATE / "lock"

TPL, WORK = STATE / "templates", STATE / "work"

SLOCK, CHAINS, RESUME_DIR, HEART = STATE / "state.lock", STATE / "chains", STATE / "resume", STATE / "heartbeat"

RESIZE_LOG = STATE / "resize.log"

RESUME_MAX = 20 * 1024                 # bytes: resume notes and chain notes are read by a fresh agent, keep them short

_UTIL = []


DEFAULT_MAX_JOBS = 400                 # the nrp-cluster skill's "max concurrent jobs"


MISSING_GRACE_S = 10 * 60              # a just-submitted chain Job not yet listed is given this long

SUBMIT_TIMEOUT_S = 900

HEART_WARN_S = 25 * 60                 # `status` warns past this when work is active

HEART_STALL_S = 30 * 60                # `chain wait` gives up (exit 5) past this

WAIT_POLL_S = int(os.environ.get("NRP_MONITOR_POLL_S") or 30)

DEFAULT_S3 = "https://s3-west.nrp-nautilus.io"

POD_DEDUPE_S = 30 * 60

GPU_WARN_WINDOW_MIN = 60       # NRP judges a GPU pod on its ~3 h average (warning mail 2026-11-15), not on a 10-min sample.

GPU_ENFORCE_WINDOW_MIN = 90    # Hunter 2026-11-15: warn on the 1 h average under the floor; delete when the 90-min average is under it (30 min to save logs)

GPU_WARN_DEDUPE_S = 60 * 60

STRIKE_GAP_S = 8 * 60          # strike 2 needs a flag this long after the OVERSIZED verdict: the second pass after it (passes run every 5 min)

NOTIFY_DEDUPE_S = 60 * 60

JOB_GRACE_S = 15 * 60          # a registered job not yet visible in the cluster is given this long

MAX_POD_AGENTS = 3

POD_MODEL, POD_TURNS, POD_BUDGET = "sonnet", "15", "1.00"   # runs only at strike 2 / STUCK (owner decision 2026-11-05: a bigger agent)

JOB_MODEL, JOB_TURNS, JOB_BUDGET = "sonnet", "25", "2.00"

TRIAGE_MODEL, TRIAGE_TURNS, TRIAGE_BUDGET, TRIAGE_TIMEOUT = "haiku", "12", "0.50", 600

FOLLOWUP_REPAIR_ATTEMPTS = 2  # after Haiku: at most two Sonnet attempts, then one alert

AUTH_TURNS, AUTH_BUDGET, AUTH_TIMEOUT = "45", "4.00", 2400   # authorized (debug + resubmit) follow-ups

APPROVED = STATE / "approved"                                # per task: manifest.yaml, code/, code.orig/, PATCH.diff

CODE_SNAPSHOT_MAX = 30 * 1024 * 1024

CODE_SKIP = (".git", "__pycache__", ".pytest_cache", "results", "node_modules")

CLONE_SUFFIXES = frozenset({".py", ".yaml", ".yml", ".json", ".lock", ".txt", ".csv", ".ini", ".md", ".R", ".sh"})   # source and config; same idea as pv3 --ship-code

CLONE_MAX_FILE = 2 * 1024 * 1024
CLONE_FULL_MAX = int(os.environ.get("NRP_CLONE_FULL_MAX_MB") or 200) << 20     # whole-repo task clone refused above this unless code.full_checkout
CLONE_KEEP_DAYS = float(os.environ.get("NRP_CLONE_KEEP_DAYS") or 3)            # finished task clones are pruned this long after the end
CLONE_KEEP_CONT_DAYS = float(os.environ.get("NRP_CLONE_KEEP_CONT_DAYS") or 7)  # ...or this long while a plan continuation may still clone it
CLONE_CACHE_WARN = int(os.environ.get("NRP_CLONE_CACHE_WARN_GB") or 20) << 30  # status warns when the task cache passes this

CODE_SKIP_EXT = (".pt", ".npz", ".npy", ".pth", ".safetensors", ".h5", ".nwb", ".fasta", ".fa", ".gz", ".tgz", ".zip")

FLAG = re.compile(r"^(LOW|HIGH|STUCK|FAILED) (?!checked \d+ pods)(\S+?):?(?:\s|$)")

ACCT = re.compile(r"account: (\d+) of (\d+) running pods outside NRP bands(?:, \+(\d+) started)?")  # 3: pods still starting


def now():
    return time.time()


def log(msg):
    STATE.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write("%s %s\n" % (datetime.now().isoformat(timespec="seconds"), " ".join(msg.split())))


def load():
    try:
        d = json.loads(JOBS.read_text())
    except Exception:
        d = {}
    d.setdefault("jobs", {})
    d.setdefault("pods", {})
    d.setdefault("strikes", {})
    d.setdefault("notified", {})
    d.setdefault("errors", 0)
    d.setdefault("kube_errors", 0)
    return d


def save(d):
    tmp = JOBS.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1, sort_keys=True))
    os.replace(tmp, JOBS)

# ---- origin: which chat a person returns to (owner decision 2026-11-05) --------------------------------------------------
# Every alert is sent by this script (or by a repair agent it starts), never by the chat that owns the work. A task, chain or
# legacy registration therefore carries `origin` = {title, link, assistant, collaborator, note?, evidence?, recorded, source}:
# the human-facing chat that asked for the work. It is supplied explicitly (JSON "origin", --origin-* flags, or the
# `origin` command for work registered before this existed) and never guessed: T3CODE_THREAD_ID inside an agent names
# the agent's own (possibly delegated) thread, not the chat the person talks to. No origin -> "origin not recorded" plus
# the goal and code repo so the person can still find the owner.
ORIGIN_MISSING = "origin not recorded"

ORIGIN_FIELDS = ("title", "link", "assistant", "collaborator", "note", "evidence", "harness", "session", "cwd")

# v3: the origin also says HOW to wake that same chat. `harness` is t3 (CLI or webhook, link = the T3 thread), claude (a Claude Code
# session id, resumed with `claude -p --resume ID`) or codex (a Codex session id, `codex exec resume ID`). `session` is that id and `cwd` the
# directory the chat ran in (Claude Code finds a session by its project directory). A wake lands in that chat's own history; it never starts one.
ORIGIN_HARNESSES = ("t3", "claude", "codex")

ORIGIN_SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{3,99}$")

SESSION_ENV = {"claude": "CLAUDE_CODE_SESSION_ID", "codex": "CODEX_THREAD_ID"}   # set in the shell of a Claude Code / Codex session

ORIGIN_LINK_RE = re.compile(r"^(t3-thread://[^\s<>|]+|https?://[^\s<>|]+)$")


def one_line(s, n):
    return " ".join(str(s).replace("`", "'").split())[:n]


def slack_esc(s):
    """Slack mrkdwn escaping (https://api.slack.com/reference/surfaces/formatting#escaping): & < > only."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ---- agent runners: which CLI starts an agent, per-tier models, fallback when one is out of usage ------------------
# `agent_cmd` builds the Claude Code command (a plain list, so dry-runs and tests read it as before) and attaches a spec.
# `run_agent` / `run_task_agent` start it through the first runner in <state>/agents.json "runners" that is not out of
# usage. A usage-limit answer blocks that runner until its reset time (<state>/runners.json) and the next runner takes
# over; with none left the work waits (no retry is used up) and one DM says so. Without agents.json: Claude only, with
# the constants above, exactly as before.
#   {"runners": ["claude", "codex"],
#    "models": {"triage": {"claude": "haiku", "codex": "gpt-6.1-sol"}, "repair": {...}, "task": {...}, "pod": {...}},
#    "limits": {"repair": {"turns": 25, "budget": 2.0, "timeout": 1500}},      # turns/budget apply to Claude only
#    "followup_ladder": ["triage", "repair", "repair"]}                         # what a finished job's follow-up tries, in order
# v3 (`nrp-monitor setup` writes this): each tier names an ordered list of backends, chosen at install time from the subscriptions the
# user has. The next entry is used ONLY when the one before it is unavailable (usage/rate limit, not signed in, CLI missing); a bad
# answer never fails over. Every failover is a line in the task's events and the digest. Without "tiers" the old `runners` x `models`
# form still loads and means the same ordered list per tier.
#   "tiers": {"triage": [{"runner": "agy", "model": "gemini-3.8-flash-low"}, {"runner": "claude", "model": "haiku"}],
#             "task":   [{"runner": "claude", "model": "sonnet"}]}
# Tier 3 is always the task's coordinator chat (no entry); there is no separate Opus tier.
# Codex runs `codex exec` with approvals off, a workspace-write sandbox (no network, writes only to the agent's own
# directories) and an execpolicy rules file generated from the same allowlist: a matching command may use the network,
# anything else stays in the sandbox. Unlike Claude's dontAsk, a Codex agent can still READ any file the user can.
AGENTS_CFG, RUNNER_STATE = STATE / "agents.json", STATE / "runners.json"

KNOWN_RUNNERS = ("claude", "codex", "agy")

READ_ONLY_TIERS = ("triage",)             # the agy runner only runs the read-only verdict tier; config naming it elsewhere is refused

TIERS = ("pod", "triage", "repair", "repair_auth", "task", "deputy")

LADDER_STEPS = ("triage", "repair")

UNAVAILABLE = "AGENT UNAVAILABLE"

LIMIT_ANY = re.compile(r"(hit your (?:weekly |usage |\w+ )?limit|usage limit|weekly limit|rate.?limit|quota (?:exceeded|exhausted)|out of (?:credits|usage)|"
                       r"resource.?exhausted|exceeded your (?:current )?quota|too many requests)", re.I)

AUTH_ANY = re.compile(r"(not (?:logged|signed) in|please (?:log ?in|sign in|run /login)|/login\b|invalid (?:api key|authentication)|api key not valid|"
                      r"authentication (?:failed|error|required)|unauthenticated|failed to (?:log ?in|authenticate)|login required|"
                      r"please set an auth method|GEMINI_API_KEY|credentials? (?:expired|invalid|not found)|oauth\b.*(?:expired|invalid))", re.I)

AUTH_BLOCK_S = 3600                    # a runner that is not signed in is set aside this long, then tried again

LIMIT_START = re.compile(r"^(you['’]ve hit your|you have hit your|claude (?:ai )?usage limit)", re.I)


def iso_at(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")

# Antigravity hooks use camelCase toolCall payloads, unlike Claude hooks.
# The gate is a separate immutable copy in the per-run workspace, never agent-authored.
AGY_GATE = r'''import json, re, shlex, sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text())
call = json.load(sys.stdin).get("toolCall", {})
args = call.get("args") or {}
ok = False
if call.get("name") == "run_command":
    cmd = args.get("CommandLine", "")
    # No shell composition, expansion, redirection, or escaped/newline tokens.
    if not re.search(r"[;&|<>`$\\\n\r]", cmd):
        words = shlex.split(cmd)
        for rule in cfg:
            m = re.fullmatch(r"Bash\((nrp-task (?:show|logs|describe|util|s3).*?)(?::\*)?\)", rule)
            if m:
                prefix = shlex.split(m.group(1))
                ok |= words[:len(prefix)] == prefix
elif call.get("name") == "view_file":
    raw = args.get("AbsolutePath", "")
    if raw and ".." not in Path(raw).parts:
        path = Path(raw).resolve()
        for rule in cfg:
            m = re.fullmatch(r"Read\(/(/.*?)/\*\*\)", rule)
            if m:
                root = Path(m.group(1)).resolve()
                ok |= path.is_relative_to(root)
print(json.dumps({"decision": "allow" if ok else "deny", "reason": "nrp-monitor read-only allowlist"}))
'''


GPU_PCT_RE = re.compile(r"\bgpu (\d+(?:\.\d+)?)% \(gpu")

AGE_RE = re.compile(r"\bage (\d+)m\b")

# ---- chains: model-free multi-step Job pipelines ---------------------------------------------------------------
# A chain is a DAG of steps; each step is one command (e.g. nrp/submit.py ... --apply) that creates one k8s Job.
# State lives in chains/<name>/chain.json (spec + progress), written atomically under state.lock, so `chain add/resume/
# cancel/wait` can run beside a pass. Nothing here ever retries or resizes: a stop is a decision for a person.
STEP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")

JOB_RE = re.compile(r"^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$")

PASS = {}                                   # counters for the heartbeat line


class ChainError(Exception):
    pass


def iso(ts=None):
    return datetime.fromtimestamp(ts if ts else now()).isoformat(timespec="seconds")


def ago(ts):
    s = max(0, int(now() - ts))
    return "%ds" % s if s < 90 else "%dm" % (s // 60) if s < 5400 else "%.1fh" % (s / 3600)


@contextlib.contextmanager
def state_lock(timeout=60):
    """Short lock around read-modify-write of chain files (not the long-held pass lock)."""
    STATE.mkdir(parents=True, exist_ok=True)
    f = open(SLOCK, "a+")
    end = time.time() + timeout
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.time() > end:
                f.close()
                raise RuntimeError("state.lock busy for %ds" % timeout)
            time.sleep(0.05)
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return None


S3_PASS = None            # {uri: True|False} resolved earlier in THIS pass (s3_prepass); None outside a pass

S3_JOB_IMAGE = "amazon/aws-cli:2.22.35"

S3_JOB_ENDPOINT = "http://rook-ceph-rgw-nautiluss3.rook"

S3_JOB_WAIT_S, S3_JOB_POLL_S = 240, 5

S3_JOB_SCRIPT = r'''for u in "$@"; do
  p=${u#s3://}; b=${p%%/*}; k=${p#*/}
  out=$(aws s3api head-object --bucket "$b" --key "$k" --output json 2>&1); rc=$?
  if [ $rc -eq 0 ]; then echo "EXISTS $u"
  elif echo "$out" | grep -q "(404)" && echo "$out" | grep -q HeadObject; then echo "MISSING $u"
  else echo "ERROR $u"; fi
done'''

# ---- chain transitions ----------------------------------------------------------------------------------------




















# ---- digest and push (v2: routine events are silent; one push when the owner is needed) ---------------------------
DIGEST, PUSHED, ORPHANS = STATE / "digest.log", STATE / "pushed.json", STATE / "orphans.json"

SLACK_URL = os.environ.get("NRP_MONITOR_SLACK_URL") or "https://notifications.braingeneers.gi.ucsc.edu/v1/slack"

SLACK_USER = os.environ.get("NRP_MONITOR_SLACK_USER") or OWNER.get("slack_user_id") or ""   # the owner's own DM, never a channel or a chat

JWT_FILE = Path(os.environ.get("NRP_MONITOR_JWT") or Path.home() / ".ssh/braingeneers_jwt_token.json")   # env: tests

# ---- tasks (v2): task-level approval, script-classified failures, silent retries ----------------------------------
# A task = owner-approved work: stages (one k8s Job each, from a manifest), success = S3 keys, an optional code clone.
# The script submits stages, checks success, deletes finished Jobs after saving their logs, and classifies failures.
# A fresh Sonnet agent (templates/task_agent.md) is started only to diagnose and fix a failure; its only shell tool is
# `nrp-task` (this script's `tool` subcommand), which validates every argument. Retries are silent; the task moves to
# NEEDS_OWNER (one push) on a repeated failure, a slow/design failure, a used-up budget or an agent STOP.
TASKS = STATE / "tasks"

TASK_CACHE = Path(os.environ.get("NRP_TASK_CACHE") or Path.home() / ".cache/nrp-tasks")

TASK_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

# Failure classes: per-stage retry budget; Tier 0 rules that may settle it (tier0.RULES, the deadline rule); `systemic`: the same
# signature on several stages is one bug, not several bad shards; `triage`: the Tier 1 judge always looks (others only while the
# Job is alive or done). Whether a stage may be resubmitted to resume is per stage (timeouts.stage_resumable), not per class.
CLASS_DEFAULT = {"budget": 1, "rules": (), "systemic": False, "triage": False}
TIER0_RULES = ("node", "oom", "lost")
CLASSES = {
    "resources": {"budget": 3, "rules": TIER0_RULES},
    "infra": {"budget": 2, "rules": TIER0_RULES},
    "code": {"budget": 3, "rules": TIER0_RULES, "systemic": True},
    "unknown": {"budget": 1, "rules": TIER0_RULES, "systemic": True, "triage": True},
    "outputs": {"budget": 1, "systemic": True},
    "util": {"budget": 3},
    "queue": {"budget": 2},
    "slow": {"rules": ("timeout",), "triage": True},
}


def failure_class(cls):
    return dict(CLASS_DEFAULT, **CLASSES.get(cls, {}))


SYSTEMIC_STAGES = 3                                   # ... on this many distinct stages (or 10% of a fan-out, whichever is larger)

LOST_SIG = "lost-pod"                                 # the container never reported an exit and there is no traceback: our code did not fail


TASK_LIVE = ("running", "retrying", "blocked")

TASK_HELD = ("NEEDS_OWNER", "WITH_COORDINATOR")      # completion is still observed while waiting for a decision

WAKE_MAX_TRIES = 6                                   # a coordinator wake that fails this many passes (~30 min) falls back to NEEDS_OWNER

COORD_STALE_S = 24 * 3600                            # a delivered wake nobody answered for this long falls back to NEEDS_OWNER

# Tier 0 deadline rules (no model). activeDeadlineSeconds counts from Job start INCLUDING time spent Pending.
DEADLINE_EXT_MAX = 2                                 # in-place extensions for a Job that is still progressing near its deadline

DEADLINE_PEND_EXT_MAX = 8                            # in-place extensions that keep a still-Pending Job alive near its deadline

DEADLINE_CREDIT_MIN_S = 10 * 60                      # Pending time shorter than this is not credited back

DEADLINE_RESUBMITS_MAX = 1                           # a dead stage is resubmitted with 2x deadline this many times (resume-capable stages only)


TASK_MODEL, TASK_TURNS, TASK_BUDGET, TASK_TIMEOUT = "sonnet", "60", "6.00", 2700   # alias "sonnet" followed the newest Sonnet: claude-sonnet-5-5 under this scrubbed env on 2026-11-05

CODE_PYTHON = Path(OWNER["code_python"]) if OWNER.get("code_python") else None   # config.json "code_python": interpreter for `nrp-task code-test` (needs pytest) and `reship`; default = the one running this script

BLOCK_ESCALATE_S = 6 * 3600

BLOCK_RECHECK_S = 600       # while pods outside the bands explain a block: re-check the namespace this often, re-apply only if the set changed

LAST_BLOCK = {}             # the raw text of the most recent admission refusal (apply_manifest returns only "blocked")

BLOCK_RE = re.compile(r"utilization (is )?too low|exceeded quota|forbidden:.*quota|denied the request.*utiliz", re.I)

TRANSIENT_RE = re.compile(r"ConnectionError|EndpointConnectionError|ReadTimeout|timed out|Temporary failure in name resolution|"
                          r"SlowDown|503 Service|Connection reset|BrokenPipe|Name or service not known|urlopen error", re.I)

EXC_RE = re.compile(r"^\s*([A-Za-z_][\w.]*(Error|Exception|Interrupt))(:.*)?$")

FLAG_RES = re.compile(r"\b(cpu|mem|gpu)\s+([\d.]+)/([\d.]+)(?:Gi)?\s+\((\d+)%(?:,\s*max\s+([\d.]+))?")

GIT_ID = ["-c", "user.name=nrp-monitor", "-c", "user.email=nrp-monitor@localhost"]


def task_dir(n):
    return TASKS / n


def task_load(n):
    from . import notify as _m_notify  # Local import breaks orchestration cycle; patches stay on the defining module.
    t = _m_notify.read_json(task_dir(n) / "task.json", None) if n else None
    if t and t.get("status") == "NEEDS_HUNTER":          # the status was named after its first user; tasks written before the rename
        t["status"] = "NEEDS_OWNER"
    return t


def task_write(t):
    p = task_dir(t["name"]) / "task.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(t, indent=1, sort_keys=True))
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def task_txn(n, fn):
    from . import plan_wakes as _m_plan_wakes  # Local import breaks orchestration cycle; patches stay on the defining module.
    def modify(t):
        previous = t.get("status")
        completed = set(t.get("completed_stages", [])) | {s["id"] for s in t.get("stages", []) if s["state"] == "done"}
        r = fn(t)
        if r is False:
            return False
        t["completed_stages"] = sorted(completed | {s["id"] for s in t.get("stages", []) if s["state"] == "done"})
        if t.get("status") != previous and t.get("status") in ("done", "failed", "cancelled"):
            t["terminal_at"] = now()
            _m_plan_wakes.terminal_wake(t)
        return r
    return json_txn(lambda: task_load(n), modify, task_write)


def task_names():
    return sorted(p.parent.name for p in TASKS.glob("*/task.json")) if TASKS.is_dir() else []

# ---- handoff: one markdown file per task. The registering agent writes `## Registrar` once; this script is the only writer of
# the append sections (`## Fix log`, `## Continuation`, `## For the owner`), from the HANDOFF_ENTRY block of an agent's final answer.
# Agents never edit the file: the copy in the task dir (handoff.md) is the source of truth, handoff.orig.md the unmodified original.
HANDOFF_HEADS = ("Registrar", "Fix log", "Continuation", "For the owner")

HANDOFF_APPEND = {"deputy": "Fix log", "fix": "Fix log", "continue": "Continuation"}          # agent kind -> the section it may add to

HANDOFF_MIN_REG = 200                  # characters of text (comments and white space excluded) a Registrar section needs

HANDOFF_MAX_FILE, HANDOFF_MAX_REG = 100 * 1024, 16000

HANDOFF_ENTRY_MAX, HANDOFF_OWNER_MAX = 1500, 500

HANDOFF_PROMPT_MAX = 14000             # characters of handoff embedded in an agent prompt (Registrar whole, newest log entries)

HANDOFF_NONE = "(no handoff written)"

HANDOFF_COMMENT = re.compile(r"<!--.*?-->", re.S)

HANDOFF_ENTRY_RE = re.compile(r"^[ \t>*_`#-]*HANDOFF_ENTRY[ \t*_`]*:[ \t*_`]*(.*)$", re.M)

HANDOFF_OWNER_RE = re.compile(r"^[ \t>*_`-]*FOR_OWNER[ \t*_`]*:[ \t*_`]*(.*)$")


HANDOFF_ESC_RE = re.compile(r"last resort|escalat|coordinator|sub-?agent", re.I)

HANDOFF_ESC_ASK = ("In the Registrar, say in your own words how failures are handled: the monitor's script and its subagents (Tier 1 triage, "
                   "Tier 2 fixer) handle failures and fixes; this chat is woken only as a last resort, after them; the owner is notified only "
                   "after this chat decides they are needed (`nrp-monitor task needs-owner`).")

# Python-urllib's default User-Agent is rejected by Cloudflare (error 1010) in front of the relay, so every
# delivery failed with HTTP 403 until a User-Agent of our own was sent.
WEBHOOK_USER_AGENT = "nrp-monitor/1.0"


WAKE_TIMEOUT_S = 600

WAKE_TOOLS = ["Bash(nrp-monitor task show:*)", "Bash(nrp-monitor task resume:*)", "Bash(nrp-monitor task cancel:*)",
              "Bash(nrp-monitor task needs-owner:*)", "Bash(nrp-monitor digest:*)", "Bash(nrp-monitor status:*)"]

# a resumed chat may still run the old command name from its handoff; `nrp-watchdog` is an installed shim of nrp-monitor
WAKE_TOOLS += ["Bash(nrp-monitor decide:*)", "Bash(nrp-monitor wake-review:*)"]

WAKE_TOOLS += [t.replace("nrp-monitor", "nrp-watchdog") for t in WAKE_TOOLS]

# A wake that can only run the commands above cannot read a log or fix a bug, so it can only report (bwb-mtp smoke, 2026-11-15: the
# coordinator saw the cause, could not fix it, and the task sat 24 h until NEEDS_OWNER). A Claude wake also gets: nrp-task scoped to its
# task (logs, s3 reads, reship/submit, code-test/commit/ship), files in that task's and plans' state and in the chat's own repo, a few git
# commands run in that repo, and PushNotification. No arbitrary shell, kubectl, deletes outside nrp-task's rules or other repos.
WAKE_GIT = ["Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)", "Bash(git add:*)", "Bash(git commit:*)",
            "Bash(git pull --ff-only:*)", "Bash(git push origin main:*)"]


def tev(t, msg):
    t.setdefault("events", []).append("%s %s" % (iso(), " ".join(msg.split())[:300]))
    del t["events"][:-80]
    log("task %s: %s" % (t["name"], msg[:300]))


def tstage(t, sid):
    return next(s for s in t["stages"] if s["id"] == sid)


def task_of_job(job):
    """(task name, stage id) of a live task whose stage runs Job `job`."""
    for n in task_names():
        t = task_load(n)
        if t and t["status"] in TASK_LIVE + TASK_HELD:
            for s in t["stages"]:
                if s["job"] == job and s["state"] in ("running", "failed"):
                    return n, s["id"]
    return None


def norm_sig(s):
    s = re.sub(r"0x[0-9a-f]+|\b[0-9a-f]{8,}\b|\d+(\.\d+)?", "N", s.lower())
    return " ".join(s.split())[:140]


def today_iso():
    return os.environ.get("NRP_MONITOR_TODAY") or datetime.now().strftime("%Y-%m-%d")


DECISION_NO_PROGRESS_LIMIT = 3


DECISION_ACTIONS = ("resubmit", "resubmit_with_manifest", "escalate", "skip_reuse")


GPU_USE_RE = re.compile(r"\bgpu (\d+)% \(gpu (\d+)")

# ---- account RED ALERT: NRP's own admission verdict is the signal (Hunter 2026-11-18) ---------------------------------------
# Every RED_PROBE_S a server-side dry-run create of a tiny Job runs NRP's admission webhooks without creating anything. A denial with the
# utilization/quota text (or any real submit refused that way) puts the account in RED ALERT: no task or chain submits anything until a
# probe passes again; the owners of the offending pods are woken once per alert and Hunter is pushed once. Only a passing probe clears it.
RED_ALERT = STATE / "red_alert.json"

RED_PROBE_S = 600

RED_REUSE_S = 3600          # an alert re-entered within this long after clearing keeps its id (no second round of wakes for a flapping block)

RED_PROBE_JOB = {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"generateName": "nrp-monitor-admission-probe-"},
                 "spec": {"backoffLimit": 0, "template": {"spec": {"restartPolicy": "Never", "containers": [{
                     "name": "probe", "image": "busybox", "command": ["true"],
                     "resources": {"requests": {"cpu": "100m", "memory": "64Mi"}, "limits": {"cpu": "100m", "memory": "64Mi"}}}]}}}}

# ---- Tier 1 (triage judge) ----
TRIAGE_VERDICT_RE = re.compile(r"^[ \t>*_`#-]*(CLOSE|ESCALATE)\b[ \t*_`]*:?[ \t*_`]*(.*)$", re.M)

TRIAGE_CLOSE = ("CLOSE",)

# ---- Tier 0: fixed rules, no model (v3 plan) -------------------------------------------------------------------------
# Applied before any agent: OOM -> memory = observed peak x1.3; a known node fault -> exclude that node and resubmit; a long Pending
# reports the scheduler's reason. Every rule goes through do_submit, so retry caps, class budgets, the GPU approval date and the
# manifest rules still hold; anything a rule cannot decide (no peak number, repeat failure, over a cap) falls through to the
# agents (handle_failure) untouched.
OOM_FACTOR = 1.3

OOM_MAX_GI_DEFAULT = 128

NODE_EXCLUDE_MAX = 3                       # nodes excluded per stage by Tier 0; a fourth fault goes to the agents

PENDING_REPORT_S = 30 * 60

PENDING_REREPORT_S = 3600

THANOS_URL = os.environ.get("NRP_MONITOR_THANOS_URL") or "https://thanos.nrp-nautilus.io/api/v1/query"

NODE_FAULT_RE = re.compile(r"uncorrectable ECC|\bXid\b\W*\d+|no CUDA-capable device is detected|nvidia-container-cli|"
                           r"failed to create (?:pod )?sandbox|FailedMount|MountVolume\.\w+ failed|OCI runtime create failed|"
                           r"\bNodeLost\b|ContainerStatusUnknown", re.I)

_MEM_UNITS = {"": 1, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40}


TASK_EXCEPTION_LIMIT = 3


FLAG_RULE_RE = re.compile(r"\brule=(lab|nrp|gpu)\b")


UTIL_OK_RE = re.compile(r"^[ \t>*_`#-]*UTIL_OK[ \t*_`]*:[ \t*_`]*(.*)$", re.M)

UTIL_OK_REASON_MAX = 400


NRP_UTIL_RULE = """NRP VIOLATION (rule=nrp: below NRP's 20% floor, which NRP enforces by refusing new pods on the whole account). "No change
needed" is NOT an allowed outcome. Size from NRP's measured working-set peak (peaks_gi above, Thanos whole-life per pod), never from a
cgroup memory.peak / profile peak, which counts reclaimable page cache: request = ceil(peak x 1.5), limit within 20% of request. Write it
into the manifest; if the stage resumes from saved progress, `nrp-task delete` the running Job and `nrp-task submit` it at the new size now.
If it cannot be restarted safely, say why in one line: the monitor then wakes the coordinator chat."""


MEMORY_RULE = """Memory NRP band is 20–150% of request. Tier 1 is judge only: CLOSE with numbers or ESCALATE with numbers and what looks wrong.
The fixer alone changes resources. need=max(stage whole-life per-pod peaks, recorded OOM limits); right=ceil(need*1.5) Gi.
A recorded OOM limit is a proven lower bound even when sampled usage idles below the band between spikes.
CLOSE with that reason when request <= 1.2*right; never STOP or escalate solely for that low mean.
request <= 1.2*right is sized correctly; above it is oversized. If max/median >3 and low pods remain below 20% of request
through their whole life, split inputs into size groups. Missing peaks or incomparable pods require explicit review.
Fixer: edit manifests structurally (load YAML, change, dump), never by text substitution; every edit is validated. Write right into the manifest for retries/later runs. Leave running work to finish unless measured time remaining >2h
AND the stage is resumable; only then resubmit at right. Never shrink below OOM evidence. UTIL flags alone never hold a task.
GPU (rule gpu) is different: NRP deletes GPU pods whose ~3 h average is under 40% and records a violation (three strikes suspend the
account). For a GPU flag, judge the trend, not one sample: `nrp-util-check --window 60 POD`. If the 1 h mean is under 40%, the fixer
stops the Job (`nrp-task delete`) and restructures before any resubmit (parallel items per pod, CPU phases in a CPU Job); the
"leave running work to finish" rule does not apply to GPU flags. The monitor itself deletes a GPU Job whose 90-min mean is under 40%, 30 min after the 1 h warning."""

# ---- plans: on_done continuation (feature flag, default OFF; design docs/agents/plan-run/WATCHDOG_ON_DONE.md) ----
# A task may carry  "on_done": {"plan": "path/to/PLAN.md#plan-id", "from_step": "2"}.  `task add` copies that plan section
# (and the files its run block lists under `templates`) into plans/<id>/, because launchd cannot read ~/Desktop.
# When the task is done, ONE fresh Sonnet "continue" agent checks the step's "done when" against the outputs and, only for
# next steps inside the approved range that are not stops for the owner and were never started before, registers the next task
# (`nrp-task next-add FILE`). Everything else waits for the owner and is listed in the digest's "Plans" section (morning report).
PLANS = STATE / "plans"

PLAN_MAX = 24 * 1024                     # the plan section a fresh agent reads

PLAN_FILES_MAX = 256 * 1024              # templates copied beside it

ON_DONE_FLAG = STATE / "on_done.enabled"   # `touch` it to turn auto-continue on; delete it to turn it off

PLAN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

CONT_STALE_S = 2 * 3600                  # a continue run that never returned (pass crashed) is closed after this

PLAN_KEYS = ("plan", "approval", "steps", "approved_through", "stop_for_owner", "stop_for_hunter", "may_touch", "next", "templates")

# ---- chain commands --------------------------------------------------------------------------------------------










def heartbeat_age():
    try:
        return HEART.stat().st_mtime
    except OSError:
        return None


def write_heartbeat(text):
    STATE.mkdir(parents=True, exist_ok=True)
    HEART.write_text("%s %s\n" % (iso(), text))

# ---- setup: choose each tier's backend from the subscriptions the user has (writes agents.json) ----------------------
# Tier 1 (triage) and Tier 2 (fixer) are configurable; Tier 3 is always the coordinator chat and there is no separate Opus tier.
SUBSCRIPTIONS = ("claude", "codex", "agy", "t3")          # t3 only changes what is explained: it is a harness for the coordinator chat, not a runner

SETUP_TIERS = (("triage", "Tier 1 triage judge (reads one event, answers CLOSE / ESCALATE)"),
               ("task", "Tier 2 fixer (edits manifests and code, resubmits)"))

SETUP_DEFAULT_MODEL = {("claude", "triage"): "haiku", ("claude", "task"): "sonnet", ("codex", "triage"): "gpt-6.1-sol", ("codex", "task"): "gpt-6.1-sol"}



def json_txn(load, modify, write):
    """One locked read/modify/write. Missing state or literal False aborts without a write.

    Callers own defaults, validation, lifecycle hooks and file formatting. Load and
    write are callables so those policies and their existing patch targets stay local.
    """
    with state_lock():
        value = load()
        if value is None:
            return False
        result = modify(value)
        if result is False:
            return False
        write(value)
        return True if result is None else result

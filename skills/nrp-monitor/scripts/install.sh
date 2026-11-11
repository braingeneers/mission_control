#!/bin/sh
# Install nrp-monitor (and `nrp-watchdog`, a quiet shim for its former name) by COPYING (never symlink: launchd cannot read ~/Desktop, where this repo lives).
#   ./install.sh            script -> ~/.local/bin, templates -> state dir, plist -> ~/Library/LaunchAgents (not loaded)
#   ./install.sh --launchd  also (re)load the launchd agent
# State dir ~/.local/state/nrp-monitor, launchd label edu.ucsc.<user>.nrp-monitor, variables NRP_MONITOR_* (the former NRP_WATCHDOG_* are read as a fallback).
# Records the git commit in ~/.local/state/nrp-monitor/INSTALLED. Never touches jobs.json, chains/, resume/ (except the one-time migration below).
#
# One-time, idempotent migration from the former name (runs before anything else is copied):
#   - the old launchd label is booted out, then waits up to NRP_MONITOR_MIGRATE_WAIT seconds (default 300) for the pass lock;
#     timeout aborts without moving state and reloads the old scheduler. Its plist is archived after successful migration;
#   - ~/.local/state/nrp-watchdog (a real dir, with nrp-monitor absent) is moved to ~/.local/state/nrp-monitor and a symlink
#     nrp-watchdog -> nrp-monitor is left, so absolute paths saved by older runs stay valid; paths inside the JSON state are also rewritten;
#   - if the old label was loaded, the new one is loaded too (even without --launchd) so monitoring never silently stops.
# A fresh install touches none of this and creates nrp-monitor only.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
uid=$(id -u)
user=$(id -un)
base="$HOME/.local/state"
state="$base/nrp-monitor"
old_state="$base/nrp-watchdog"
label=${NRP_MONITOR_LABEL:-edu.ucsc.$user.nrp-monitor}   # set NRP_MONITOR_LABEL to keep an agent you already loaded under another label
old_label=edu.ucsc.$user.nrp-watchdog
plist="$HOME/Library/LaunchAgents/$label.plist"
old_plist="$HOME/Library/LaunchAgents/$old_label.plist"

lock_free() {   # true when no pass holds the pass lock (a missing lock file is free)
  [ -e "$1" ] || return 0
  python3 -c "
import fcntl, sys
try:
    f = open(sys.argv[1], 'a'); fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    sys.exit(1)" "$1"
}
wait_lock() {   # wait_lock FILE SECONDS: 0 once free, 1 when still held after SECONDS
  _end=$(( $(date +%s) + $2 ))
  while ! lock_free "$1"; do
    [ "$(date +%s)" -lt "$_end" ] || return 1
    sleep 2
  done
}
agent_loaded() { command -v launchctl >/dev/null 2>&1 && launchctl print "gui/$uid/$1" >/dev/null 2>&1; }

# Inspect Label values as well as filenames: custom labels need migration too.
old_labels=$(python3 - "$HOME/Library/LaunchAgents" "$old_label" "${NRP_WATCHDOG_LABEL:-}" <<'PYLABELS'
import pathlib, plistlib, subprocess, sys
labels = {sys.argv[2]}
if sys.argv[3].endswith('.nrp-watchdog'): labels.add(sys.argv[3])
for p in pathlib.Path(sys.argv[1]).glob('*.plist'):
    try: label = plistlib.loads(p.read_bytes()).get('Label', '')
    except Exception: label = p.stem
    if label.endswith('.nrp-watchdog') and all(c.isalnum() or c in '._-' for c in label): labels.add(label)
try:
    for line in subprocess.check_output(['launchctl', 'list'], text=True, stderr=subprocess.DEVNULL).splitlines():
        label = line.split()[-1] if line.split() else ''
        if label.endswith('.nrp-watchdog') and all(c.isalnum() or c in '._-' for c in label): labels.add(label)
except (OSError, subprocess.CalledProcessError): pass
print(' '.join(sorted(labels)))
PYLABELS
)
legacy_plist() {
  python3 - "$HOME/Library/LaunchAgents" "$1" <<'PYPATH'
import pathlib, plistlib, sys
root, label = pathlib.Path(sys.argv[1]), sys.argv[2]
for p in root.glob('*.plist'):
    try: matched = plistlib.loads(p.read_bytes()).get('Label') == label
    except Exception: matched = p.stem == label
    if matched:
        print(p); break
else: print(root / (label + '.plist'))
PYPATH
}
loaded_labels=""
old_loaded=0
for candidate in $old_labels; do
  if agent_loaded "$candidate"; then old_loaded=1; loaded_labels="$loaded_labels $candidate"; fi
done
# Any legacy plist triggers migration, including an unloaded custom label.
for candidate in $old_labels; do
  candidate_plist=$(legacy_plist "$candidate")
  if [ -e "$candidate_plist" ]; then
    old_label=$candidate; old_plist=$candidate_plist
  fi
done
migrate_state=0
if [ -d "$old_state" ] && [ ! -L "$old_state" ] && [ ! -e "$state" ] && [ ! -L "$state" ]; then migrate_state=1; fi
if [ "$migrate_state" = 1 ] || [ "$old_loaded" = 1 ] || [ -e "$old_plist" ]; then
  [ "$migrate_state" = 1 ] && lockfile="$old_state/lock" || lockfile="$state/lock"
  wait_s=${NRP_MONITOR_MIGRATE_WAIT:-300}
  if [ "$old_loaded" = 1 ]; then
    for candidate in $loaded_labels; do
    launchctl bootout "gui/$uid/$candidate" || { echo "ABORTED: cannot unload $old_label; state was not moved." >&2; exit 1; }
    echo "migration: booted out the old launchd label $candidate"
    done
  fi
  if ! wait_lock "$lockfile" "$wait_s"; then
    for candidate in $loaded_labels; do
    candidate_plist=$(legacy_plist "$candidate")
    if [ -f "$candidate_plist" ]; then
      launchctl bootstrap "gui/$uid" "$candidate_plist" 2>/dev/null && echo "migration: reloaded the old launchd label $old_label so monitoring continues" >&2
    fi
    done
    echo "ABORTED: pass lock $lockfile is still held after ${wait_s}s; state was not moved and the old scheduler was reloaded. Retry install.sh when the pass finishes." >&2
    exit 1
  fi
  if [ "$migrate_state" = 1 ]; then
    python3 - "$state" "$old_state" "$state" <<'PYMIGRATE'
import fcntl, json, os, sys
root, old, new = sys.argv[1:4]
# Retain the pass lock through the move and JSON rewrite; refuse a racing manual pass.
lock = open(os.path.join(old, "lock"), "a")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    sys.exit("ABORTED: pass lock was acquired by another pass; state was not moved. Retry install.sh.")
os.rename(old, new)
os.symlink("nrp-monitor", old)
print("migration: moved %s to %s (symlink %s -> nrp-monitor left in place)" % (old, new, old))
log = os.path.join(new, "watchdog.log")
if os.path.isfile(log) and not os.path.exists(os.path.join(new, "monitor.log")):
    os.rename(log, os.path.join(new, "monitor.log"))
    print("migration: renamed watchdog.log to monitor.log")
esc = lambda p: json.dumps(p)[1:-1]
old_e, new_e = esc(old), esc(new)
done = 0
for d, _, files in os.walk(root):
    for f in files:
        if not f.endswith(".json"):
            continue
        p = os.path.join(d, f)
        try:
            if os.path.islink(p) or os.path.getsize(p) > 64 << 20:
                continue
            text = open(p, encoding="utf-8").read()
            if old_e not in text:
                continue
            json.loads(text)
            def paths(value):
                if isinstance(value, str):
                    return new + value[len(old):] if value == old or value.startswith(old + "/") else value
                if isinstance(value, list):
                    return [paths(x) for x in value]
                if isinstance(value, dict):
                    return {k: paths(v) for k, v in value.items()}
                return value
            out = json.dumps(paths(json.loads(text)), indent=1)
            if out == text:
                continue
            json.loads(out)
            tmp = p + ".migrate.tmp"
            with open(tmp, "w", encoding="utf-8") as g:
                g.write(out)
            os.chmod(tmp, os.stat(p).st_mode & 0o7777)
            os.replace(tmp, p)
            done += 1
        except (OSError, ValueError):
            continue
print("migration: rewrote the old state path in %d JSON file(s)" % done)
PYMIGRATE
  fi
  for candidate in $old_labels; do
  old_label=$candidate; old_plist=$(legacy_plist "$candidate")
  if [ -e "$old_plist" ] && [ "$old_plist" != "$plist" ]; then
    mkdir -p "$state"
    mv "$old_plist" "$state/$old_label.plist.migrated"
    echo "migration: removed the old plist from ~/Library/LaunchAgents (kept as $state/$old_label.plist.migrated)"
  fi
  done
fi

mkdir -p "$HOME/.local/bin" "$state/templates" "$HOME/Library/LaunchAgents"
for f in nrp-monitor nrp-util-check nrp-s3-read; do python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$here/$f"; done; sh -n "$here/nrp-task"   # syntax check without writing bytecode into the skill
install -m 755 "$here/nrp-monitor" "$HOME/.local/bin/nrp-monitor.new" && mv "$HOME/.local/bin/nrp-monitor.new" "$HOME/.local/bin/nrp-monitor"
# `nrp-watchdog` (the former name) stays a working, quiet command for old handoffs and hooks: a tiny wrapper (a copy, never a symlink into ~/Desktop) that execs the sibling nrp-monitor.
printf '%s\n' '#!/bin/sh' '# former name of nrp-monitor; kept so existing handoffs and hooks keep working.' 'exec "$(dirname "$0")/nrp-monitor" "$@"' > "$HOME/.local/bin/nrp-watchdog.new"
chmod 755 "$HOME/.local/bin/nrp-watchdog.new" && mv "$HOME/.local/bin/nrp-watchdog.new" "$HOME/.local/bin/nrp-watchdog"
install -m 755 "$here/nrp-s3-read" "$HOME/.local/bin/nrp-s3-read.new" && mv "$HOME/.local/bin/nrp-s3-read.new" "$HOME/.local/bin/nrp-s3-read"
install -m 755 "$here/nrp-task" "$HOME/.local/bin/nrp-task.new" && mv "$HOME/.local/bin/nrp-task.new" "$HOME/.local/bin/nrp-task"
install -m 755 "$here/nrp-util-check" "$HOME/.local/bin/nrp-util-check.new" && mv "$HOME/.local/bin/nrp-util-check.new" "$HOME/.local/bin/nrp-util-check"
for t in "$here"/templates/*.md; do
  b=$(basename "$t")
  if [ -f "$state/templates/$b" ] && ! cmp -s "$t" "$state/templates/$b"; then cp "$state/templates/$b" "$state/templates/$b.bak"; fi
  cp "$t" "$state/templates/$b"
done
sed -e "s#@HOME@#$HOME#g" -e "s#@LABEL@#$label#g" "$here/nrp-monitor.plist.template" > "$plist"
commit=$(git -C "$here" rev-parse --short HEAD 2>/dev/null || echo unknown)
dirty=$(git -C "$here" status --porcelain -- . 2>/dev/null | head -1)
echo "commit $commit${dirty:+ (+uncommitted changes)}  installed $(date '+%Y-%m-%dT%H:%M:%S')" > "$state/INSTALLED"
echo "installed: $(cat "$state/INSTALLED")"
[ -f "$state/config.json" ] || echo "NOTE: $state/config.json is missing. Create it with {\"nrp_user_annotation\": \"http://cilogon.org/serverE/users/NNNN\", \"slack_user_id\": \"U...\"}; without it pod checks and the Slack DM are off."
# Which assistant runs each tier (Claude Code / Codex / Gemini CLI): asked once, only when agents.json is missing and a person is at the
# terminal. Otherwise say how to run it. NRP_MONITOR_SETUP=skip never asks. Setup failing never fails the install.
if [ ! -f "$state/agents.json" ]; then
  if [ "${NRP_MONITOR_SETUP:-${NRP_WATCHDOG_SETUP:-auto}}" != "skip" ] && [ -t 0 ]; then
    NRP_MONITOR_STATE="$state" "$HOME/.local/bin/nrp-monitor" setup || echo "NOTE: setup did not finish; run 'nrp-monitor setup' again (until then agents use Claude only, built-in models)."
  else
    echo "NOTE: $state/agents.json is missing, so background agents use Claude only with built-in models. Choose what each tier uses with: nrp-monitor setup"
  fi
fi
want_load=0
[ "${1:-}" = "--launchd" ] && want_load=1
if [ "$want_load" = 1 ] || [ "$old_loaded" = 1 ]; then
  launchctl bootout "gui/$uid/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$uid" "$plist"
  if [ "$want_load" = 1 ]; then
    echo "launchd agent $label loaded (every 5 min; the pass lock keeps it from double-running with a terminal loop)"
  else
    echo "launchd agent $label loaded because the old label $old_label was loaded (monitoring resumes on the new state path)"
  fi
fi

#!/bin/sh
# Install nrp-monitor (and the `nrp-watchdog` alias, its former name) by COPYING (never symlink: launchd cannot read ~/Desktop, where this repo lives).
#   ./install.sh            script -> ~/.local/bin, templates -> state dir, plist -> ~/Library/LaunchAgents (not loaded)
#   ./install.sh --launchd  also (re)load the launchd agent
# Records the git commit in ~/.local/state/nrp-watchdog/INSTALLED. Never touches jobs.json, chains/, resume/.
# Compatibility with the pre-rename install: the state dir (~/.local/state/nrp-watchdog), the launchd label/plist name
# (edu.ucsc.<user>.nrp-watchdog) and the NRP_WATCHDOG_* variables keep their names, so an already loaded agent keeps working.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
state="$HOME/.local/state/nrp-watchdog"
label=${NRP_WATCHDOG_LABEL:-edu.ucsc.$(id -un).nrp-watchdog}   # set NRP_WATCHDOG_LABEL to keep an agent you already loaded under another label
plist="$HOME/Library/LaunchAgents/$label.plist"
mkdir -p "$HOME/.local/bin" "$state/templates" "$HOME/Library/LaunchAgents"
for f in nrp-monitor nrp-util-check nrp-s3-read; do python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$here/$f"; done; sh -n "$here/nrp-task"   # syntax check without writing bytecode into the skill
install -m 755 "$here/nrp-monitor" "$HOME/.local/bin/nrp-monitor.new" && mv "$HOME/.local/bin/nrp-monitor.new" "$HOME/.local/bin/nrp-monitor"
# `nrp-watchdog` stays a working command: a tiny wrapper (a copy, never a symlink into ~/Desktop) that execs the sibling nrp-monitor.
printf '%s\n' '#!/bin/sh' '# nrp-watchdog is the former name of nrp-monitor; kept so existing handoffs, launchd and habits keep working.' 'exec "$(dirname "$0")/nrp-monitor" "$@"' > "$HOME/.local/bin/nrp-watchdog.new"
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
# terminal. Otherwise say how to run it. NRP_WATCHDOG_SETUP=skip never asks. Setup failing never fails the install.
if [ ! -f "$state/agents.json" ]; then
  if [ "${NRP_WATCHDOG_SETUP:-auto}" != "skip" ] && [ -t 0 ]; then
    NRP_WATCHDOG_STATE="$state" "$HOME/.local/bin/nrp-monitor" setup || echo "NOTE: setup did not finish; run 'nrp-monitor setup' again (until then agents use Claude only, built-in models)."
  else
    echo "NOTE: $state/agents.json is missing, so background agents use Claude only with built-in models. Choose what each tier uses with: nrp-monitor setup"
  fi
fi
if [ "${1:-}" = "--launchd" ]; then
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$plist"
  echo "launchd agent loaded (every 5 min; the pass lock keeps it from double-running with a terminal loop)"
fi

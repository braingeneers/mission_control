#!/usr/bin/env bash
set -euo pipefail
SKILL_SRC=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
for base in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  mkdir -p "$base"
  target="$base/summarize-codebase"
  if [[ -e "$target" && ! -L "$target" ]]; then
    echo "Refusing to replace existing directory: $target" >&2
    exit 1
  fi
  ln -sfn "$SKILL_SRC" "$target"
  echo "Installed $target -> $SKILL_SRC"
done

#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PI_SEARCH_DEMO_HOME=$(mktemp -d /tmp/pi-search-demo.XXXXXX)
export PI_SEARCH_DEMO_HOME
trap 'rm -rf "$PI_SEARCH_DEMO_HOME"' EXIT
export HOME="$PI_SEARCH_DEMO_HOME" ZDOTDIR="$PI_SEARCH_DEMO_HOME" PS1='$ '
export XDG_CONFIG_HOME="$HOME/.config" XDG_CACHE_HOME="$HOME/.cache"
export XDG_DATA_HOME="$HOME/.local/share" XDG_STATE_HOME="$HOME/.local/state"
export PI_CODING_AGENT_DIR="$HOME/.pi/agent" PI_OFFLINE=1 PI_TELEMETRY=0
unset PI_SEARCH_EDITOR PI_CODING_AGENT_SESSION_DIR

paths=()
IFS=: read -ra entries <<< "$PATH"
for entry in "${entries[@]}"; do
  case "$entry" in *cmux-cli-shims*) continue ;; esac
  paths+=("$entry")
done
PATH=$(IFS=:; echo "${paths[*]}")
export PATH

python3 -B "$ROOT/tests/fixtures.py" "$HOME"
printf '%s\n' '{"quietStartup":true,"defaultProvider":"openai","defaultModel":"gpt-4.1","extensions":["-builtin:mcp","-builtin:codemode","-builtin:tool-search","-builtin:llama.cpp"],"defaultTools":[]}' > "$PI_CODING_AGENT_DIR/settings.json"
cd "$ROOT"
vhs docs/demo.tape

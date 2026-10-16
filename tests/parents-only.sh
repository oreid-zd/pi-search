#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export PATH="$TMP/bin:$PATH"
export QMD_FIXTURE="$TMP/semantic.json" QMD_LOG="$TMP/qmd.log"
mkdir -p "$HOME/.pi/agent/sessions" "$TMP/bin"

parent='--repo--/2026-01-01T00-00-00_parent.md'
other='--repo--/2026-01-02T00-00-00_other.md'
artifact='--repo--/subagent-artifacts/2026-01-03T00-00-00_worker.md'
run='--repo--/2026-01-04T00-00-00_parent/task/run-0/session.md'
run_other='--repo--/2026-01-04T00-00-00_parent/task/run-12/session.md'

session() {
  local file="$HOME/.pi/agent/sessions/${1%.md}.jsonl"
  mkdir -p "$(dirname "$file")"
  jq -nc --arg text "$2" '
    {type:"session",version:3,id:"fixture"},
    {type:"message",message:{role:"assistant",content:[{type:"text",text:$text}]}},
    {type:"message",message:{role:"toolResult",content:[{type:"text",text:"toolneedle"}]}}
  ' > "$file"
}
session "$parent" $'redis redis\nredis'
session "$other" 'redis'
session "$artifact" 'redis redis redis redis childneedle'
session "$run" 'redis redis redis childneedle'
session "$run_other" 'redis redis redis childneedle'

cat > "$TMP/bin/qmd" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$QMD_LOG"
case "$1" in
  vsearch)
    shift
    n=20
    while [ $# -gt 0 ]; do
      case "$1" in
        --all) n=1000000 ;;
        -n) n="$2"; shift ;;
      esac
      shift
    done
    jq --argjson n "$n" '.[:$n]' "$QMD_FIXTURE"
    ;;
  status) echo 'Updated: fixture' ;;
  update|embed) ;;
  *) exit 1 ;;
esac
EOF
chmod +x "$TMP/bin/qmd"
jq -n --arg parent "$parent" --arg other "$other" --arg artifact "$artifact" --arg run "$run" --arg run_other "$run_other" '
  [$artifact, $run, $run_other, $parent, $parent, $other] | to_entries |
  map({file:("qmd://pi-history/" + .value),line:(.key+1),score:(1-.key/10),snippet:"redis"})
' > "$QMD_FIXTURE"

search() { "$ROOT/pi-search" "$@" </dev/null; }
paths() { printf '%s\n' "$1" | cut -f2; }
assert_eq() {
  [ "$1" = "$2" ] || { printf 'FAIL: %s\nexpected: %s\nactual: %s\n' "$3" "$1" "$2" >&2; exit 1; }
}

rows=$(search --all redis)
assert_eq 6 "$(printf '%s\n' "$rows" | wc -l | tr -d ' ')" 'default includes parents and subagents'
assert_eq "$artifact" "$(paths "$rows" | head -n1)" 'unfiltered ranking unchanged'
rows=$(search --parents-only --all redis)
assert_eq 3 "$(printf '%s\n' "$rows" | wc -l | tr -d ' ')" 'parent filter removes both subagent layouts'
assert_eq "$rows" "$(search -p --all redis)" 'short flag matches long alias'
assert_eq "$parent" "$(paths "$(search redis -p -n 1)")" 'keyword filter before limit; flag after query'
rows=$(search -p -d --all redis)
assert_eq 2 "$(printf '%s\n' "$rows" | wc -l | tr -d ' ')" 'keyword distinct parents'
rows=$(search -p -t -d --all toolneedle)
assert_eq 2 "$(printf '%s\n' "$rows" | wc -l | tr -d ' ')" 'tool-result parents'
if search --parents-only childneedle > "$TMP/no-match" 2>&1; then
  echo 'FAIL: child-only keyword query should have no matches' >&2; exit 1
fi
grep -q 'no matches' "$TMP/no-match"

assert_eq "$artifact" "$(paths "$(search -v -n 1 redis)")" 'semantic default unchanged'
assert_eq "$parent" "$(paths "$(search -v -p -n 1 redis)")" 'semantic filter before limit'
grep -q '^vsearch redis -c pi-history --all --json$' "$QMD_LOG"
rows=$(search -v --parents-only --all redis)
assert_eq "$(printf '%s\n%s\n%s' "$parent" "$parent" "$other")" "$(paths "$rows")" 'semantic parent ordering'
rows=$(search -v --parents-only -d --all redis)
assert_eq "$(printf '%s\n%s' "$parent" "$other")" "$(paths "$rows")" 'semantic distinct parents'
rows=$(search --rows-v --refresh redis --all -p --distinct)
assert_eq "$(printf '%s\n%s' "$parent" "$other")" "$(paths "$rows")" 'semantic refresh keeps parent/distinct filters and row format'
assert_eq "$parent" "$(paths "$(search --rows-v --refresh redis -n 1 -p)")" 'semantic refresh keeps result limit'
assert_eq "$parent" "$(paths "$(search -v --reindex --parents-only -n 1 redis)")" 'reindex keeps parent filter'
if paths "$rows" | grep -Eq '/(subagent-artifacts|run-[0-9]+)/'; then
  echo 'FAIL: semantic refresh leaked a subagent' >&2; exit 1
fi
grep -q '^update -c pi-history$' "$QMD_LOG"
grep -q '^embed -c pi-history$' "$QMD_LOG"
jq '.[0:3]' "$QMD_FIXTURE" > "$TMP/child-only.json"
mv "$TMP/child-only.json" "$QMD_FIXTURE"
if search -v --parents-only redis > "$TMP/no-match" 2>&1; then
  echo 'FAIL: child-only semantic query should have no matches' >&2; exit 1
fi
grep -q 'no semantic matches' "$TMP/no-match"
search --help > "$TMP/help" 2> "$TMP/help-errors"
grep -q -- '-p, --parents-only' "$TMP/help"
assert_eq '' "$(< "$TMP/help-errors")" 'help has no command-substitution errors'
printf 'parents-only tests passed\n'

#!/usr/bin/env sh
# Install pi-search: fetch the scripts into ~/.local/bin.
#   curl -fsSL https://raw.githubusercontent.com/oreid-zd/pi-search/main/install.sh | sh
# Override the version (any git ref) with:  PI_SEARCH_REF=v1.0.0 curl ... | sh
set -eu

OWNER_REPO="oreid-zd/pi-search"
REF="${PI_SEARCH_REF:-main}"
DEST_DIR="${PI_SEARCH_BIN:-$HOME/.local/bin}"
BASE="https://raw.githubusercontent.com/$OWNER_REPO/$REF"

command -v rg  >/dev/null 2>&1 || { echo "error: pi-search needs ripgrep — brew install ripgrep" >&2; exit 1; }
command -v fzf >/dev/null 2>&1 || { echo "error: pi-search needs fzf — brew install fzf" >&2; exit 1; }
command -v jq  >/dev/null 2>&1 || { echo "error: pi-search needs jq — brew install jq" >&2; exit 1; }

mkdir -p "$DEST_DIR"
for f in pi-search pi-export-history pi-search-maintenance; do
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$BASE/$f" -o "$DEST_DIR/$f"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$DEST_DIR/$f" "$BASE/$f"
  else
    echo "error: need curl or wget" >&2; exit 1
  fi
  chmod +x "$DEST_DIR/$f"
  echo "installed $f -> $DEST_DIR/$f ($REF)"
done

case ":$PATH:" in
  *":$DEST_DIR:"*) ;;
  *) echo "note: $DEST_DIR is not on your PATH — add it to your shell rc" ;;
esac

command -v bat  >/dev/null 2>&1 || echo "note: bat enables syntax-highlighted previews — brew install bat"
command -v nvim >/dev/null 2>&1 || echo "note: nvim enables the read-only transcript viewer — brew install neovim"

if command -v qmd >/dev/null 2>&1; then
  if ! qmd collection list 2>/dev/null | grep -q "^pi-history"; then
    qmd collection add "$HOME/.pi/agent/sessions-md" --name pi-history
    qmd embed -c pi-history
  fi
else
  echo "note: semantic search (-v) needs qmd — npm install -g @tobilu/qmd"
  echo "      then: qmd collection add ~/.pi/agent/sessions-md --name pi-history && qmd embed -c pi-history"
fi

cat <<'EOT'

Optional: keep the semantic index fresh with a nightly cron:
  crontab -e
  30 2 * * * $HOME/.local/bin/pi-search-maintenance >/tmp/pi-search-maintenance.log 2>&1

EOT
echo "done — try: pi-search 'a bug you remember fixing'"

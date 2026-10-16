# 1.2.0 integration checks

Verified on 2026-10-16 against executable code in `16c7fa9`. These checks used
real installed tools, separate from the mocked regression suites.

## Results

| Integration | Check | Result |
|---|---|---|
| qmd 2.8.3 | Create a fixture collection, embed four documents with cached local GGUF models, and run parent-only semantic search | Pass |
| qmd + fzf 0.74.3 | Press Ctrl+R after changing a source session; verify the new text enters the index and fzf's actual load events report two rows before and after refresh | Pass |
| Semantic output | Run refresh and `--reindex` with `-p -d -n 2`; check that stdout contains two valid parent rows and embedding progress stays on stderr | Pass |
| fzf + bat 0.26.1 | Display actual picker results and syntax-highlighted transcript previews | Pass |
| fzf + nvim 0.12.5 | Press Ctrl+O; inspect the opened buffer, match line, readonly flag, and literal case-insensitive search pattern | Pass |
| `PI_SEARCH_EDITOR` | Press Ctrl+O with real nvim configured as an external editor; verify the opened file | Pass |
| fzf + pi 1.3.0 | Press Enter for lean and tool-result transcripts; verify resumed history and the session UUID through `/session` | Pass |
| macOS clipboard | Press Ctrl+X and verify the path with pbpaste; press Ctrl+T and read the actual file reference with osascript | Pass |
| Installer + curl + qmd | Download the three scripts from GitHub at `16c7fa9` into a custom directory containing a space; compare each file byte-for-byte with the checkout | Pass |
| Existing installation | Run the real installer again against an existing qmd collection | Pass |
| Maintenance + qmd | Prune an orphan transcript, rebuild a missing corpus, and retain the corpus root after all source sessions have been removed | Pass |
| VHS 0.10.0 | Re-record and inspect the GIF showing unfiltered/parent-only results, Ctrl+O viewing, and Enter resume | Pass |

The parent-filter shell suite and 22 Python regression tests also pass on macOS
and in a Linux container with GNU tools. Bash/sh syntax checks, VHS validation,
and `git diff --check` pass.

## Bug found by live testing

Real qmd writes an embedding status message to stdout, even when no embeddings
need updating. That message appeared as a third picker row after a refresh
requested with `-n 2`. The mocks had not emitted that status text.

Commit `16c7fa9` redirects embedding progress to stderr for refresh and reindex.
A regression test now emits the real status shape, and the live fzf load-event
check confirms that refresh keeps exactly two rows.

## Isolation

- All integration sessions were synthetic fixtures from `tests/fixtures.py`.
- Integration commands used temporary HOME, XDG directories, and QMD_CONFIG_DIR.
  qmd reused cached model files but wrote its collection and index separately.
- The installer check compared the original qmd index/config timestamps and
  sizes before and after. They did not change.
- The pi checks ran offline. They resumed fixture history and used `/session`;
  no model prompt was submitted. No provider credential files were copied.
- The clipboard check saved every available pasteboard type, verified the copy
  actions, and restored the saved contents. The demo does not touch the clipboard.
- Live desktop checks ran on macOS 26.7. External-editor coverage used real nvim,
  not VS Code or Cursor. Linux coverage remains the isolated regression suites.

## Re-record the demo

```sh
bash docs/record-demo.sh
```

The recorder creates and deletes its own fixture history. Its guarded wrapper
fails if the fixture is missing. The resulting GIF is 1450 x 720 and about
22 seconds long.

## Repeat the semantic check

From the repository root, with the same cached models installed:

```sh
(
  root="$PWD"
  cache="${XDG_CACHE_HOME:-$HOME/.cache}"
  fixture=$(mktemp -d)
  trap 'rm -rf "$fixture"' EXIT
  export QMD_EMBED_MODEL="$cache/qmd/models/hf_ggml-org_embeddinggemma-300M-Q8_0.gguf"
  export QMD_GENERATE_MODEL="$cache/qmd/models/hf_tobil_qmd-query-expansion-1.7B-q4_k_m.gguf"
  export HOME="$fixture" XDG_CACHE_HOME="$fixture/.cache"
  export XDG_CONFIG_HOME="$fixture/.config" QMD_CONFIG_DIR="$fixture/.config/qmd"
  export XDG_DATA_HOME="$fixture/.local/share" XDG_STATE_HOME="$fixture/.local/state"
  export PI_CODING_AGENT_DIR="$fixture/.pi/agent" PI_OFFLINE=1 PI_TELEMETRY=0
  export QMD_FORCE_CPU=1
  python3 -B "$root/tests/fixtures.py" "$fixture"
  cd "$fixture"
  "$root/pi-export-history"
  qmd collection add "$fixture/.pi/agent/sessions-md" --name pi-history
  qmd embed -c pi-history
  "$root/pi-search" -v -p -d -n 2 redis
)
```

In the picker, Ctrl+R refreshes the fixture index. Only parent sessions should
appear, with no embedding-status row. Esc returns without opening a session.

# pi-search

Search and read your [pi](https://github.com/badlogic/pi-mono) session history
from the terminal. Sessions are stored by pi as JSONL; pi-search exports them
to readable markdown and searches them with `ripgrep` — results in
milliseconds, even across hundreds of sessions. `-v` adds optional semantic
search ([qmd](https://github.com/tobilu/qmd) embeddings) for when you remember
the conversation but not the words.

Pick a hit and it opens the transcript in a read-only `nvim` viewport, centered
on the match with every occurrence highlighted and `n`/`N` wired up.

![pi-search keyword search, preview, and transcript viewer](docs/demo.gif)

## Requirements

- bash, `rg` (ripgrep), `fzf`, `jq`
- optional: `qmd` (semantic `-v` search), `bat` (previews), `nvim` (transcript viewer)
- clipboard actions (`ctrl-t`, `ctrl-x`) use macOS `osascript` and `pbcopy`

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/oreid-zd/pi-search/main/install.sh | sh
```

Installs three scripts into `~/.local/bin`:

| script | role |
|---|---|
| `pi-search` | the CLI: search, picker, transcript viewer |
| `pi-export-history` | incremental JSONL → markdown export (run automatically on every search) |
| `pi-search-maintenance` | nightly prune + re-embed for the semantic index |

macOS only for relative timestamps (`date -j`); everything else works anywhere
the dependencies do.

## Usage

```sh
pi-search "redis timeout"           # keyword search (ripgrep)
pi-search -n 20 --all refactor      # top 20, or everything with --all
pi-search -t "stack trace"          # include tool results (default: user+assistant only)
pi-search -d "redis timeout"        # one row per session, its strongest match
pi-search -v "that caching bug"     # semantic search (qmd embeddings)
pi-search export                    # re-export all sessions to markdown
pi-search resume <transcript.md>    # resume a session in pi (also: ctrl-o in the picker)
pi-search -v --reindex "query"      # rebuild the semantic index first
pi-search --help
```

The picker is `fzf` — type to narrow further, arrow through results, preview
pane scrolls the surrounding transcript. `enter` opens the transcript at the
match.

`ctrl-v` runs `$PI_SEARCH_EDITOR` with the path appended, e.g. `PI_SEARCH_EDITOR="code -g"`. Unset, it runs `cmux open` (or `open` outside cmux).

Rows show `repo date kind hits`, then the line number and snippet, with columns
padded so they line up. `kind` is `a` for your own sessions and `s` for
delegated subagent runs (`subagent-artifacts/` and `run-0/`). Repo names drop the
`zendesk-` prefix and are capped at 18 characters. Age is relative ("4d ago")
until a session is a week old, then the date. Files without a timestamp in their
name use the source session's last-modified time. In semantic mode rows also show
a match score, color-coded yellow → orange → red as relevance climbs.

Keyword rows show `Nx`: how many times the query appears in that row's text, and
the picker is sorted by it. Ties go to the session with more total hits, then to
line order. Semantic rows keep qmd's score order, which the percentage shows.
Counts only cover the visible snippet, so a second hit past column 110 of a line
is not counted.

### Keys

| key | action |
|---|---|
| `enter` | open the match in the transcript viewer |
| `ctrl-o` | resume the selected session in pi |
| `ctrl-t` | copy the transcript file to the clipboard (paste it as a file) |
| `ctrl-x` | copy the transcript path to the clipboard |
| `ctrl-v` | open the transcript in your editor |
| `esc` | cancel |
| `ctrl-r` | refresh the semantic index (semantic mode) |
| `ctrl-/` | show or hide the preview pane |
| `n` / `N` | next / previous highlighted match (in nvim) |

## How it works

1. `pi-export-history` converts `~/.pi/agent/sessions/**/*.jsonl` to markdown
   under `~/.pi/agent/sessions-md/`, skipping thinking blocks, tool plumbing,
   and HTML blobs. Export is incremental (mtime-guarded), so repeated searches
   only pay for new sessions. By default tool results are omitted — the corpus
   matches what you see in pi; pass `-t` for a full-corpus export
   (`sessions-md-full`).
2. Keyword search is plain `ripgrep` over that markdown, ranked by hit count
   and match strength. No index to maintain, no daemon.
3. Semantic search (`-v`) queries a [qmd](https://github.com/tobilu/qmd)
   collection over the lean corpus. It's a separate, opt-in path: embeddings
   are slow to build, so the index refreshes on demand (`ctrl-r`,
   `--reindex`) or nightly via `pi-search-maintenance`.

## Optional nightly index refresh

```sh
crontab -e
# refresh the semantic index at 2:30am
30 2 * * * $HOME/.local/bin/pi-search-maintenance >/tmp/pi-search-maintenance.log 2>&1
```

Keyword search needs no cron — the export happens on every search.

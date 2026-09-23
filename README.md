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
pi-search -v "that caching bug"     # semantic search (qmd embeddings)
pi-search export                    # re-export all sessions to markdown
pi-search resume <transcript.md>    # resume a session in pi (also: ctrl-o in the picker)
pi-search -v --reindex "query"      # rebuild the semantic index first
pi-search --help
```

The picker is `fzf` — type to narrow further, arrow through results, preview
pane scrolls the surrounding transcript. `enter` opens the transcript at the
match.

Rows show `repo age` — relative ("4d ago") until a session is a week old,
then the date. In semantic mode rows also show a match score, color-coded
yellow → orange → red as relevance climbs.

### Keys

| key | action |
|---|---|
| `enter` | open the match in the transcript viewer |
| `ctrl-o` | resume the selected session in pi |
| `esc` | cancel |
| `ctrl-r` | refresh the semantic index (semantic mode) |
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

# Changelog

## 1.2.0

### Added

- `-p` / `--parents-only` excludes subagent sessions from keyword and semantic
  searches. It works with tool results, distinct sessions, result limits, and
  semantic refresh. Subagent labels recognize numeric `run-N` directories as well
  as `subagent-artifacts`.
- Isolated tests cover search, picker actions, export, installation, and
  maintenance without using real session history or modifying a live index.

### Changed

- Enter resumes the selected session in pi. Ctrl+O opens its transcript.
- Ctrl+O uses `PI_SEARCH_EDITOR` when set, or the built-in match-aware viewer
  otherwise. This replaces Ctrl+V and its automatic `cmux open` / `open` fallback.
  External editors receive only the file path, without match positioning or
  query highlighting.
- Exports keep the full searchable text instead of truncating tool blocks at
  200 characters and other text blocks at 2,000. Picker snippets still stop at
  about 110 characters.
- Exporter updates invalidate cached markdown so existing transcripts pick up
  export fixes.

### Fixed

- Export headers work with GNU tools and preserve cwd paths containing `&`, `|`,
  spaces, or quotes. Failed JSON parses leave existing transcripts intact.
- HTML filtering handles string content and text-block arrays consistently.
  Successful exports with no searchable text remove stale markdown.
- Viewer selection checks which tools are available before starting them.
  Missing nvim or bat no longer prevents fallback to another viewer, and piped
  output avoids nvim. Previews work without bat.
- Keyword matches retain case-insensitive highlighting in nvim.
- Resume handles both lean and tool-result transcripts, including relative paths
  and macOS `/var` symlinks.
- Keyword ties keep the session's hit rank before comparing line order.
- Semantic refresh uses the same row formatting, filtering, and result limits
  as the initial search.
- Installation exports sessions before creating or updating the semantic index.
- Maintenance finds its sibling exporter in custom install locations, creates a
  missing corpus, and keeps the corpus root when pruning empty directories.
- Picker callbacks work when pi-search's directory is absent from `PATH`.
- Session ages support BSD and GNU date/stat commands.
- `--help` no longer executes the command shown in its usage text.
- The demo tape requires its isolated wrapper and invokes it explicitly, rather
  than falling back to an installed pi-search against real session history.

### Upgrading from 1.1.0

Enter and Ctrl+O have swapped actions. Use Ctrl+O instead of Ctrl+V for an
external editor, and set `PI_SEARCH_EDITOR` if you previously relied on the
automatic opener:

```sh
export PI_SEARCH_EDITOR="code -g"
pi-search -p "redis timeout"
```

Each markdown corpus rebuilds the next time it is exported. The first export
may take longer, and the full text can use more disk space. Source JSONL
sessions do not change. Refresh existing embeddings to include the longer text:

```sh
pi-search -v --reindex "query"
```

Clipboard actions still require macOS. Query hit counts still cover only the
visible snippet. The demo tape has changed, but the GIF has not been re-recorded.

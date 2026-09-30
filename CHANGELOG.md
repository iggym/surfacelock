# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Registry data

The bundled registry carries its own `_updated` date inside
`src/surfacelock/registry/models.json`. **Every data-only pull request bumps a
patch release** and adds an entry below, so `surfacelock registry --check`
failures in CI are traceable to a changelog line.

## [Unreleased]

### Added
- Nothing yet.

## [0.1.0] — 2026-09-30

### Added
- **Scanner** for the four finding types: models (F-SCAN-1), prompts
  (F-SCAN-2), tool schemas (F-SCAN-3) and MCP servers (F-SCAN-4), plus a
  performance budget of 5 s for 10k files (F-SCAN-5).
- **Registry** with 176 seeded entries across ten providers, alias-chain
  resolution, floating detection and per-repo overrides via
  `.surfacelock/models.json`.
- **`surface.lock`** — TOML lockfile with deterministic ordering and
  pin-keeping semantics: `init` pins floating aliases, `check` keeps existing
  pins even when the registry moves, `update --resolve` re-pins deliberately.
- **Policy engine** with 13 stable finding codes, inline suppression via
  `surfacelock: allow <CODE> reason="..."`, and a documentation page per code.
- **Commands**: `scan`, `init`, `check`, `update`, `explain`, `registry`,
  `pin`, `doctor`, `findings`, plus a bare invocation that dispatches to
  `check` or `scan`.
- **`explain`** — GitHub-comment-ready Markdown with token and cost deltas.
- **`pin`** — rewrites floating alias literals in source, preserving quotes
  and formatting, with a dry-run diff.
- **GitHub Action** (composite, sticky PR comment) and **pre-commit hooks**.
- **Python API** — `from surfacelock import scan, build_lock, check`, typed
  and shipped with `py.typed`.
- **JSON output schemas** versioned at `docs/schemas/scan.v1.json` and
  `docs/schemas/check.v1.json`.
- Bundled registry updated: 2026-09-30.

[Unreleased]: https://github.com/iggym/surfacelock/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/iggym/surfacelock/releases/tag/v0.1.0

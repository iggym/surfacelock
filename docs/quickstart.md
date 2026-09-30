# Quickstart

## Install

```bash
pipx install surfacelock      # or: pip install surfacelock
```

Python 3.11 or newer. No configuration is required for the first run.

## 1. Look before you leap

```bash
surfacelock scan
```

`scan` writes nothing. It prints what surfacelock believes is part of your AI
surface: model identifiers, prompts, tool schemas and MCP servers.

```text
🔒 surfacelock scan

  🧠 models
     gpt-4o                          src/agent.py:36    openai · floating
     text-embedding-3-small          src/index.py:14    openai · embedding

  📝 prompts
     agent.planner.system            src/agent.py:6     412 chars · ~103 tokens

  🔧 tools
     issue_refund                    src/tools.py:25

  🔌 mcp servers
     crm                             .cursor/mcp.json   http

  19 files scanned · 0 skipped · 41 ms
```

If something is missing, annotate it (see [Detection rules](detection.md)). If
something is a false positive, see [FAQ](faq.md#false-positives).

## 2. Freeze it

```bash
surfacelock init
```

This writes `surface.lock`. Floating aliases are pinned to the registry's
current resolution, so `gpt-4o` becomes `gpt-4o-2024-08-06` in the lockfile.
Your source is untouched — `init` never rewrites code.

## 3. Gate every pull request

```yaml
# .github/workflows/surfacelock.yml
name: AI surface
on: [pull_request]
permissions:
  contents: read
  pull-requests: write
jobs:
  surfacelock:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: iggym/surfacelock@v0.1
        with:
          comment: "true"
```

`check` exits `0` when the AI surface matches the lockfile and policy passes,
`1` on drift or a policy error, and `2` when there is no lockfile yet.

## 4. When drift is intentional

```bash
surfacelock explain          # a PR-ready summary of what changed
surfacelock update           # rewrite surface.lock, keeping existing pins
surfacelock update --resolve all   # deliberately re-pin to current snapshots
```

`update` prints token and cost deltas so the reviewer can judge the change
rather than guess at it.

## Where to go next

- [Configuration](configuration.md) — policy, ignores, prompt directories.
- [CI integration](ci.md) — Action, pre-commit, GitLab and other forges.
- [Python API](python-api.md) — `scan`, `build_lock`, `check`.

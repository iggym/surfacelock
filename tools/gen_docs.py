"""Generate the mkdocs site (docs/*.md + mkdocs.yml)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

FILES: dict[str, str] = {}

FILES["index.md"] = """# 🔒 surfacelock

> **`package-lock.json` pins your dependencies. `surface.lock` pins your models,
> prompts, tool schemas and MCP servers — and fails CI when they change without
> review.**

Your AI layer is the only part of the system that changes behaviour without
changing code. `surfacelock` makes those changes visible, reviewable and
diffable, exactly the way lockfiles did for dependencies.

<div class="grid cards" markdown>

- :material-rocket-launch: **[Quickstart](quickstart.md)**
  Three commands to a gated AI surface.

- :material-brain: **[Concepts](concepts.md)**
  What the AI surface is, and why it needs a lockfile.

- :material-magnify: **[Detection rules](detection.md)**
  What gets found, and what deliberately does not.

- :material-shield-alert: **[Findings](findings/index.md)**
  All 13 codes, with the fix for each.

</div>

## The failure modes it catches

| Failure mode | What happens | Who notices |
|---|---|---|
| **Floating aliases** | `gpt-4o`, `claude-…-latest` silently resolve to a new snapshot | Nobody — until quality drops |
| **Prompt drift** | A prompt is "tidied" in an unrelated PR | Nobody — until a regression |
| **Schema creep** | Tool schemas and MCP configs change under agents | Nobody — until a rug-pull |
| **Silent retirement** | Providers retire models on 6–12 month cycles | You — from a 404 in production |

Each is a recurring incident class with no gate in the delivery pipeline.

## Try it in thirty seconds

```bash
pipx install surfacelock
cd your-repo
surfacelock scan      # see the AI surface, writes nothing
surfacelock init      # freeze it into surface.lock
surfacelock check     # the CI gate
```

## Design principles

**Deterministic** · **conservative** — a miss beats a false positive ·
**zero-config** on first run · **human-readable** lockfile ·
**explicit annotations always win** · **fast** — under 5 s on 10,000 files.
"""

FILES["quickstart.md"] = """# Quickstart

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
"""

FILES["concepts.md"] = """# Concepts

## The AI surface

The AI surface of a repository is everything that determines what your AI
features actually do at runtime, minus the code you already review:

- **Models** — every model identifier, including embedding and Azure deployment
  names.
- **Prompts** — system prompts, instructions, personas, templates.
- **Tools** — function and tool schemas your agent can call.
- **MCP servers** — the external capabilities an agent is granted.

These are the inputs that change behaviour. A one-word prompt edit can move a
metric more than a two-hundred-line refactor, and it arrives in a diff that
looks innocuous.

## Floating vs pinned

A **floating** identifier is one that can resolve to something different without
your code changing:

| Identifier | Floating? | Why |
|---|---|---|
| `gpt-4o` | ✅ yes | The provider decides what `gpt-4o` points at |
| `claude-3-5-sonnet-latest` | ✅ yes | `-latest` is a moving target by definition |
| `gpt-4o-2024-08-06` | ❌ no | A dated snapshot is a fixed artifact |
| `text-embedding-3-small` | ✅ yes | Same alias problem as chat models |

Floating is not inherently wrong — sometimes a vendor SDK forces it. It is
wrong when it is *unnoticed*. `surfacelock` makes every floating alias explicit
and pins it in the lockfile so a change of target becomes a diff.

## Why a lockfile

We already solved this problem once, for dependencies.

| | Dependencies | The AI surface |
|---|---|---|
| **Manifest** | `package.json`, `pyproject.toml` | your source |
| **Lockfile** | `package-lock.json`, `poetry.lock` | `surface.lock` |
| **CI gate** | "lockfile is out of date" | `surfacelock check` |
| **Review artifact** | the lockfile diff | the lockfile diff + `explain` |

The lockfile is the contract. It says: *this repository, as reviewed, runs
against these exact model snapshots, these exact prompt contents, these exact
tool schemas, and these exact MCP servers.* When that stops being true, CI
fails and a human decides whether the change is intentional.

## Pin-keeping semantics

This is the subtle part, and it is what separates a lockfile from a config file.

- **`init`** pins floating aliases to the registry's current resolution.
- **`check`** compares against the lockfile. It never consults "what is current"
  for pinned entries.
- **`update`** rewrites the lockfile but **keeps existing pins**, even when the
  registry has moved on. That is the entire point: the registry moving is not a
  reason for your build to change.
- **`update --resolve`** deliberately re-pins, and prints the before/after.

Without this, a lockfile would silently follow the registry and provide no
guarantee at all.

## Determinism

Two scans of the same tree produce byte-identical output, regardless of
filesystem order or timestamps. Nothing in the lockfile body is time-dependent —
`generated_at` lives in `[meta]` only, and `check` ignores it. This is enforced
by property tests, not by convention.

## Conservatism

The tool is deliberately biased toward missing a finding rather than inventing
one. A noisy gate gets switched off, and a gate that is switched off protects
nothing. Concretely, detection requires one of:

1. A registry hit — the string is a model the registry knows.
2. A context keyword on the line — `model=`, `deployment_name=`, and friends.
3. An explicit annotation — `# surfacelock: model`.

A bare string that merely *looks* like a model name is not enough.
"""

FILES["detection.md"] = """# Detection rules and annotations

## Models

A string is recorded as a model when a provider naming pattern matches **and**
one of these holds:

- the string is known to the registry, or
- the line contains a model-context keyword (`model`, `model_name`,
  `deployment_name`, `azure_deployment`, `engine`, …), or
- the literal is annotated with `surfacelock: model`.

Scanned languages: Python, TypeScript/JavaScript (including TSX, JSX, MJS, CJS),
Go, Rust, Java/Kotlin, C#, Ruby, YAML, JSON, TOML, `.env` and `.ini`.

Azure deployments are detected from `deployment_name=` / `azure_deployment=` and
recorded with `context = "deployment"` and `provider = "azure"`. The underlying
model is unknown unless you map it in `.surfacelock/models.json`.

## Prompts

Three sources, in priority order:

1. **Annotated** — a `surfacelock: prompt [id=<id>]` comment on the line before
   or the same line as a string assignment.
2. **Prompt files** — anything under `prompt/`, `prompts/`, `system_prompts/` or
   `instructions/`, plus `.prompt`, `.md`, `.txt`, `.jinja`, `.j2`, `.hbs`,
   `.mustache` and `.tmpl` files inside those directories.
3. **Inline heuristics** — a string assigned to a name matching
   `/(prompt|system|instruction|persona|template)/i` with at least 160
   characters, or any string of at least 400 characters containing a newline.

Python is parsed with `ast` (f-string literal parts included). TypeScript and
JavaScript use a tolerant tokenizer for template literals and quoted strings —
it does not need a full parser and must never crash on syntax it does not
understand.

Each prompt records `id`, `file`, `line`, the `sha256` of the exact string,
`chars`, an approximate token count, and its `source`. Ids must be unique; a
collision errors with both locations named.

## Tools

| Form | Example |
|---|---|
| OpenAI JSON | `{"type":"function","function":{...}}` |
| Anthropic / MCP | `{name, description, input_schema}` |
| Python decorators | `@tool`, `@mcp.tool()`, `@function_tool`, `@agent.tool` |
| Pydantic | models referenced in `tools=[...]` |
| LangChain | `StructuredTool.from_function` |
| Vercel AI SDK | `tool({ name, description, parameters })` |
| MCP TS SDK | `server.tool("name", schema, …)` |

The `sha256` is taken over canonical JSON with sorted keys, so reformatting a
schema without changing it is not drift.

## MCP servers

Parsed from `.cursor/mcp.json`, `.vscode/mcp.json`, `.claude/mcp.json`,
`.mcp.json`, `mcp.json`, `claude_desktop_config.json`, `.gemini/settings.json`,
`.codex/config.toml`, `.continue/config.yaml`, and any file matching
`*mcp*.{json,yaml,toml}` containing a `mcpServers` or `servers` map.

Environment variable **names** and header **names** are recorded. Values are
never recorded, anywhere, and are hashed out of the config digest.

## Annotations

Explicit annotations always win over heuristics.

```python
# surfacelock: model
DEPLOYMENT = "my-org-custom-deployment"
```

```python
# surfacelock: prompt id=agent.planner.system
PLANNER = \"\"\"You are a planning agent...\"\"\"
```

```python
# Force detection of a non-prompt string
NOT_A_PROMPT = "..."   # surfacelock: ignore
```

### Suppressing a policy finding

```python
model = "gpt-4o"  # surfacelock: allow UNPINNED_MODEL reason="vendor SDK requires it"
```

A suppression needs a reason, appears in `check --verbose`, and is counted in
every PR summary — so it stays visible instead of becoming silent.

## What is deliberately *not* detected

- Model names in comments, documentation and prose.
- Version strings that merely resemble model names (`"1.5.0"`).
- URLs containing model-like path segments.
- Bare dictionary keys such as `"command"` or `"embed"`.
- Anything in a file above 2 MB, or a binary file.

The `tricky` fixture in the test suite encodes all of these, and CI requires it
to report 100% precision.
"""

FILES["configuration.md"] = """# Configuration

`surfacelock.toml` at the repository root. Every key has a default, so an empty
file — or no file at all — is valid.

```toml
[scan]
ignore = ["vendor/**", "**/generated/**"]
prompt_dirs = ["prompts", "src/prompts"]
min_inline_chars = 160

[policy]
fail_on_unpinned = true
fail_on_unknown_models = false
deprecation_warn_days = 90
deprecation_fail_days = 30
fail_on_retired = true
allow_models = []
deny_models = []
allow_providers = []
require_mcp_pinned = true
max_prompt_tokens = 0
require_prompt_owner = false
```

## `[scan]`

| Key | Default | Meaning |
|---|---|---|
| `ignore` | `[]` | Extra gitignore-style patterns to skip |
| `prompt_dirs` | `[]` | Extra directories treated as prompt sources |
| `min_inline_chars` | `160` | Minimum length for the inline prompt heuristic |

`.gitignore` and `.surfacelockignore` are always respected, in addition to a
built-in list that skips `.git/`, `node_modules/`, virtualenvs and build
output.

## `[policy]`

| Key | Default | Meaning |
|---|---|---|
| `fail_on_unpinned` | `true` | Error on floating aliases (`UNPINNED_MODEL`) |
| `fail_on_unknown_models` | `false` | Error on models missing from the registry |
| `deprecation_warn_days` | `90` | Warn this many days before retirement |
| `deprecation_fail_days` | `30` | Fail this many days before retirement |
| `fail_on_retired` | `true` | Fail on already-retired models |
| `allow_models` | `[]` | If non-empty, every model must match a glob here |
| `deny_models` | `[]` | Models matching any glob here always fail |
| `allow_providers` | `[]` | If non-empty, every provider must be listed |
| `require_mcp_pinned` | `true` | Forbid `http://`; warn on unversioned `npx`/`uvx`/`binx`/`pipx` |
| `max_prompt_tokens` | `0` | Fail prompts above this budget (`0` disables) |
| `require_prompt_owner` | `false` | Every prompt file must have a CODEOWNERS owner |

### Allow lists versus deny lists

`deny_models` is a blocklist: everything is permitted except what you name.
`allow_models` inverts the default: **nothing** is permitted except what you
name. The second is the right posture in regulated environments, which is why
it is opt-in rather than the default.

### Prompt owners

With `require_prompt_owner = true`, surfacelock reads `CODEOWNERS` and requires
a matching rule for every prompt file. Directory rules ending in `/` and the
catch-all `*` are both supported; the last matching rule wins, as in git.

## Per-repository model overrides

`.surfacelock/models.json` extends or overrides the bundled registry, using the
same schema. Entries here win.

```json
{
  "models": {
    "gpt-4o-prod": {
      "provider": "azure",
      "kind": "deployment",
      "resolved": "gpt-4o-2024-08-06",
      "sources": ["https://internal.example/azure-deployments"]
    }
  }
}
```

This is how you teach surfacelock about internal deployments and fine-tunes
without forking the registry.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | AI surface matches, policy passes |
| `1` | Drift, or a policy error |
| `2` | No `surface.lock` — run `surfacelock init` |
"""

FILES["ci.md"] = """# CI integration

## GitHub Action

```yaml
name: AI surface
on: [pull_request]

permissions:
  contents: read
  pull-requests: write    # only needed for comment: "true"

jobs:
  surfacelock:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: iggym/surfacelock@v0.1
        with:
          path: "."
          allow-drift: "false"
          comment: "true"
```

### Inputs

| Input | Default | Meaning |
|---|---|---|
| `path` | `.` | Repository path to check |
| `allow-drift` | `false` | Report drift without failing (policy errors still fail) |
| `comment` | `false` | Post or update a sticky PR comment |
| `version` | `0.1.0` | surfacelock version to install |
| `python-version` | `3.12` | Python used to run surfacelock |

### Outputs

`changed`, `errors` and `warnings`, so later steps can branch on the result.

### What reviewers see

With `comment: "true"`, the Action posts one sticky comment that is updated on
each push rather than accumulating. It contains the diff table, net token and
cost deltas, policy findings, and — when a model snapshot changed — a suggested
`modelbump diff` command to run your golden evaluation suite against the new
snapshot before merging.

The same content is appended to the workflow's job summary.

## pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/iggym/surfacelock
    rev: v0.1.0
    hooks:
      - id: surfacelock-check     # fails on drift; fix with `surfacelock update`
      - id: surfacelock-update    # rebuilds and stages surface.lock
```

`surfacelock-check` runs `check`, deliberately **not** `check --allow-drift`.
Drift must be reviewed. The fix is to run `surfacelock update` and commit the
resulting lockfile — which is exactly what the second hook automates.

## GitLab CI

```yaml
ai-surface:
  image: python:3.12
  script:
    - pip install surfacelock
    - surfacelock check
  rules:
    - if: $CI_MERGE_REQUEST_IID
```

## Generic CI

Anywhere you can run a command, run `surfacelock check` and honour the exit
code. For machine consumption, `--format json` emits the versioned `check.v1`
envelope documented in [JSON schemas](schemas.md).

```bash
surfacelock check --format json > surfacelock.json || true
jq '.findings[] | select(.severity == "error") | .code' surfacelock.json
```

## Adopting on an existing repository

Start permissive, then tighten:

```bash
surfacelock init
surfacelock check --allow-drift      # see the backlog without blocking
```

Fix the unpinned aliases over a few pull requests, then drop `--allow-drift`.
The `allow-drift` input exists precisely so adoption does not require a
big-bang change.

## Scheduled drift detection

Your lockfile can be perfectly consistent while the world moves. A nightly run
surfaces retirements and deprecations before they become outages:

```yaml
on:
  schedule:
    - cron: "0 8 * * 1"    # Mondays, 08:00 UTC
```

Because `check` honours `--today`, the retirement windows advance on their own.
"""

FILES["registry.md"] = """# The model registry

The registry maps an alias to a pinned snapshot, a provider, a kind, retirement
dates, list prices and a source URL.

## Inspecting it

```bash
surfacelock registry                  # the retirement calendar
surfacelock registry gpt-4o           # one entry, as JSON
surfacelock registry --check          # validate against schema.json
```

The calendar is sorted by retirement date, soonest first — the order in which
you will be forced to act.

## Entry schema

```json
{
  "provider": "openai",
  "kind": "chat",
  "resolved": "gpt-4o-2024-08-06",
  "deprecation": "2026-06-01",
  "retirement": "2026-10-20",
  "price_in": 2.5,
  "price_out": 10.0,
  "price_cached_in": 1.25,
  "context_window": 128000,
  "sources": ["https://platform.openai.com/docs/deprecations"],
  "notes": "Optional human note."
}
```

| Field | Required | Meaning |
|---|---|---|
| `provider` | ✅ | `openai`, `anthropic`, `google`, `azure`, … |
| `kind` | ✅ | `chat`, `embedding`, `rerank`, `image`, `audio`, `deployment` |
| `resolved` | — | The pinned snapshot an alias points at |
| `deprecation` | — | When the provider announced deprecation |
| `retirement` | — | When the model stops answering |
| `price_in` / `price_out` | — | List price, USD per 1M tokens |
| `price_cached_in` | — | Cached-input price, where the provider publishes one |
| `context_window` | — | Tokens |
| `sources` | ✅ | At least one URL to provider documentation |

Top-level keys are `_updated` (the registry's date, surfaced in `surface.lock`)
and `alias_patterns` (the naming patterns used for detection).

## Contributing an entry

1. Edit `src/surfacelock/registry/models.json`.
2. Add at least one `sources` URL. CI rejects entries without one.
3. `surfacelock registry --check` must pass.
4. Bump `_updated` to today.
5. Add a line under "Registry data" in `CHANGELOG.md`.

Every data-only pull request bumps a patch release, so a `registry --check`
failure in CI is always traceable to a changelog line.

## Rules for data quality

- **Prices** are list prices, as published. Not negotiated rates.
- **Retirement dates** are recorded only when the provider has announced one.
  A guess in this field causes false `MODEL_RETIRING` errors, which is worse
  than a missing date.
- **`resolved`** should name a dated snapshot where one exists. If a provider
  exposes only a floating alias, leave `resolved` equal to the alias and let
  `is_floating` report it.
- **`sources`** must point at provider documentation, not a blog post or a
  third-party tracker.

## Overrides

`.surfacelock/models.json` in your repository uses the same schema and wins over
the bundled data. Use it for internal deployments, fine-tunes and private
gateways.
"""

FILES["python-api.md"] = """# Python API

```python
from surfacelock import scan, build_lock, check
```

These three functions are the supported surface. They are typed, shipped with
`py.typed`, and stable within a 0.x minor version. Everything else is internal.

## `scan`

```python
scan(path=".", *, config=None, registry=None) -> ScanResult
```

Walk a repository and collect findings. Writes nothing.

```python
from surfacelock import scan

result = scan(".")
for model in result.models:
    print(model.name, model.file, model.line, model.context)

print(len(result.prompts), "prompts")
print(result.files_scanned, "files in", result.duration_ms, "ms")
```

`ScanResult` carries `models`, `prompts`, `tools`, `mcp_servers`,
`files_scanned`, `files_skipped`, `duration_ms`, and an `is_empty()` helper.

## `build_lock`

```python
build_lock(path=".", *, registry=None, previous=None, resolve=None) -> Lockfile
```

Produce a lockfile. Pass `previous` to preserve existing pins — the same
semantics as `surfacelock update`. Pass `resolve={"all"}` or a set of model
names to deliberately re-pin.

```python
from surfacelock import build_lock, read_lock

previous = read_lock("surface.lock")
lock = build_lock(".", previous=previous)
print(lock.counts)
```

## `check`

```python
check(path=".", *, allow_drift=False, today=None) -> CheckResult
```

Rescan, diff against `surface.lock`, and run policy. Raises
`FileNotFoundError` when there is no lockfile — the CLI maps that to exit
code 2.

```python
from surfacelock import check

outcome = check(".", allow_drift=False)
if not outcome.ok:
    for finding in outcome.policy.errors:
        print(finding.code, finding.location, finding.message)
    raise SystemExit(outcome.exit_code)
```

`CheckResult` exposes `ok`, `drift`, `policy`, `lock`, `scan`, and an
`exit_code` property that matches the CLI.

## Error handling

```python
from surfacelock.scanners.prompts import PromptCollision
from surfacelock import scan

try:
    result = scan(".")
except PromptCollision as exc:
    print(f"two prompts share the id {exc.id!r}: {exc.first} and {exc.second}")
```

## Type checking

`surfacelock` ships `py.typed` and is `mypy --strict` clean. A consumer project
gets full inference with no stubs:

```python
from surfacelock import scan

result = scan(".")
names: list[str] = [m.name for m in result.models]
```
"""

FILES["schemas.md"] = """# JSON schemas

Machine-readable output is versioned. Schemas are published alongside the code
and are validated in CI.

| Schema | Command | Document |
|---|---|---|
| `scan.v1` | `surfacelock scan --json` | [`docs/schemas/scan.v1.json`](https://github.com/iggym/surfacelock/blob/main/docs/schemas/scan.v1.json) |
| `check.v1` | `surfacelock check --format json` | [`docs/schemas/check.v1.json`](https://github.com/iggym/surfacelock/blob/main/docs/schemas/check.v1.json) |

Both envelopes carry a `schema` field naming the version, so a consumer can
branch on it. A breaking change to either shape means a new version
(`scan.v2`), never a silent edit to `v1`.

## `scan.v1`

```json
{
  "schema": "scan.v1",
  "surfacelock_version": "0.1.0",
  "summary": {
    "models": 2, "prompts": 1, "tools": 1, "mcp_servers": 1,
    "files_scanned": 19, "files_skipped": 0, "duration_ms": 41
  },
  "models": [
    {
      "name": "gpt-4o",
      "file": "src/agent.py",
      "line": 36,
      "context": "model",
      "provider": "openai",
      "annotated": false
    }
  ],
  "prompts": [
    {
      "id": "agent.planner.system",
      "path": "src/agent.py",
      "line": 6,
      "sha256": "…",
      "chars": 412,
      "approx_tokens": 103,
      "source": "annotated"
    }
  ],
  "tools": [
    {
      "name": "issue_refund",
      "file": "src/tools.py",
      "line": 25,
      "sha256": "…",
      "description": "Issue a refund to the customer",
      "param_keys": ["amount", "order_id"],
      "source": "decorator"
    }
  ],
  "mcp_servers": [
    {
      "name": "crm",
      "path": ".cursor/mcp.json",
      "transport": "http",
      "url": "https://crm.internal.example/mcp",
      "command": "",
      "args": [],
      "env_keys": ["CRM_TOKEN"],
      "sha256": "…"
    }
  ]
}
```

`env_keys` holds **names only**. Environment variable values are never present
in any output.

## `check.v1`

```json
{
  "schema": "check.v1",
  "surfacelock_version": "0.1.0",
  "ok": false,
  "counts": {"models": 2, "prompts": 1, "tools": 1, "mcp_servers": 1},
  "drift": {
    "changed": true,
    "entries": [
      {
        "kind": "model",
        "action": "changed",
        "name": "gpt-4o",
        "detail": "gpt-4o-2024-05-13 → gpt-4o-2024-11-20"
      }
    ]
  },
  "findings": [
    {
      "code": "UNPINNED_MODEL",
      "message": "`gpt-4o` is a floating alias; pin it to a dated snapshot",
      "path": "src/agent.py",
      "line": 36,
      "severity": "error",
      "suppressed": false,
      "reason": null,
      "docs_url": "https://iggym.github.io/surfacelock/findings/UNPINNED_MODEL/"
    }
  ],
  "suppressed": 0
}
```

`kind` is one of `model`, `prompt`, `tool`, `mcp_server`; `action` is one of
`added`, `removed`, `changed`.
"""

FILES["faq.md"] = """# FAQ

## False positives

### surfacelock flagged a version string

It should not. Precision is enforced by the `tricky` fixture, which includes
`"1.5.0"`, URLs containing model-like segments, model names in comments, and
markdown documentation mentioning models. CI requires that fixture to report
100% precision.

If you found a genuine miss, please open a false-positive issue with the file,
line and string. Better still, add it to `tests/fixtures/tricky/` in the same
pull request — that is how the rule gets fixed permanently.

### A string is flagged that I know is not a model

Suppress it, with a reason:

```python
THING = "gpt-4o-like-string"  # surfacelock: ignore
```

The reason matters: suppressions are listed in `check --verbose` and counted in
every PR summary, so they stay reviewable.

## Why is my model not detected?

Detection needs a registry hit, a context keyword on the line, or an
annotation. If none applies, annotate:

```python
# surfacelock: model
DEPLOYMENT = "my-custom-deployment"
```

If it is a real model the registry should know, please open a registry issue —
that helps everyone.

## Monorepos

Run surfacelock per package, each with its own `surface.lock` and
`surfacelock.toml`:

```bash
(cd services/agent && surfacelock check)
(cd services/search && surfacelock check)
```

A single root lockfile also works, but per-package lockfiles give you per-team
ownership and smaller diffs. If you use per-package policy, remember that
`.surfacelock/models.json` is resolved relative to the path you pass.

## Dynamic model strings

```python
model = os.environ["MODEL_NAME"]
```

surfacelock is a static analyser and will not resolve this. The project's
position is deliberate: conservative detection with annotations beats clever
heuristics that guess wrong. Two options:

1. Pin the value in config and annotate it:
   ```toml
   # surfacelock: model
   model = "gpt-4o-2024-08-06"
   ```
2. Set `fail_on_unknown_models = true` and rely on `scan --json` to inventory
   what *is* static, accepting that dynamic strings are out of scope.

A runtime guard is a different tool; surfacelock's non-goals list explicitly
excludes runtime enforcement.

## Azure OpenAI

Deployments are detected from `deployment_name=` / `azure_deployment=` and
recorded with `context = "deployment"` and `provider = "azure"`. The resolved
model is unknown unless you map the deployment name in
`.surfacelock/models.json`:

```json
{
  "models": {
    "gpt-4o-prod": {
      "provider": "azure",
      "kind": "deployment",
      "resolved": "gpt-4o-2024-08-06",
      "sources": ["https://internal.example/azure-deployments"]
    }
  }
}
```

## Why did `check` fail after I updated the registry?

It should not have. `check` never re-resolves pinned entries against current
registry data — that is the point of a lockfile. If `check` failed, the AI
surface in your source changed, or a *retirement date* moved into a window.
Re-pinning requires `update --resolve`, which is an explicit, reviewed act.

## Does it make network calls?

No. No network calls, no provider API introspection, no telemetry. Everything
comes from the bundled registry and your repository.

## How do I add a model to the registry?

See [the registry page](registry.md#contributing-an-entry). The short version:
add the entry, add a `sources` URL, run `surfacelock registry --check`, bump
`_updated`, add a changelog line.

## Can I use this with a private model gateway?

Yes — add your gateway's model names to `.surfacelock/models.json`. That file
uses the same schema as the bundled registry and takes precedence.

## Why TOML for the lockfile?

It is human-readable, diff-friendly, supports comments, and the header comment
can explain what the file is — which matters when someone encounters
`surface.lock` for the first time in a review.
"""

FILES["stability.md"] = """# Stability policy

## Versioning

`surfacelock` follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the major version is `0`, the minor version carries the compatibility
promise:

> **Within a 0.x minor version, patch releases are safe upgrades.**

So `0.1.0` → `0.1.7` may add registry data and fix bugs, but will not change
the CLI surface, the lockfile shape, the finding codes or the JSON schemas.
`0.1` → `0.2` may change any of those, with a changelog entry and a migration
note.

## What is stable

| Surface | Promise |
|---|---|
| `surface.lock` format | Stable within a minor; `check` reads older lockfiles |
| Finding codes | Never renamed. A code may be deprecated, never silently repurposed |
| Exit codes | `0` ok · `1` drift or policy error · `2` no lockfile |
| `scan.v1` / `check.v1` schemas | Frozen. A breaking change ships as `v2` |
| `scan`, `build_lock`, `check` | Stable within a minor |
| CLI flags | Additive within a minor |

## What is not stable

- Internal modules — `surfacelock.scanners.*`, `surfacelock.lockfile`,
  `surfacelock.policy` and friends. Import them if you like, but pin a version.
- Human-readable `text` output. Column widths and colours will change. Parse
  `--format json` instead.
- Approximate token counts. They are labelled approximate on purpose and will
  change if the estimator improves.
- Registry contents. Data changes ship as patch releases, by design.

## Finding codes

Codes are a public API because they appear in CI logs, dashboards and
suppression comments. Rules:

- A code is **never renamed**. `UNPINNED_MODEL` stays `UNPINNED_MODEL`.
- A code's meaning is **never silently repurposed**.
- A code may be **deprecated**: it stops being emitted, keeps its docs page, and
  the changelog says so.
- Adding a code is a minor change, not a patch.
- Every code has a `docs/findings/<CODE>.md` page, and CI fails if one is
  missing.

## Registry data releases

Registry-only pull requests bump a patch version. This means a patch release
can change whether `check` fails — if a retirement date moved into a window —
without any code changing.

That is intentional and it is the tool working. The lockfile protects you from
*silent snapshot movement*; it does not, and cannot, stop a provider from
retiring a model. Surfacing that is the point.

If you need total immutability for a period, pin the version:

```bash
pip install "surfacelock==0.1.3"
```

## Deprecation process

1. The changelog announces the deprecation and the replacement.
2. The old behaviour keeps working for at least one minor version.
3. The CLI warns when the deprecated path is used.
4. Removal happens at the next minor, documented in the changelog.

## Support

Only the latest 0.x minor receives fixes. Security fixes are prioritised and
backported at the maintainer's discretion; see [SECURITY.md](https://github.com/iggym/surfacelock/blob/main/SECURITY.md).
"""

FILES["reference/cli.md"] = r"""# CLI reference

```text
surfacelock [path]
surfacelock scan    [path] [--json]
surfacelock init    [path] [--force]
surfacelock check   [path] [--format text|json|markdown] [--allow-drift] [--today YYYY-MM-DD]
surfacelock update  [path] [--resolve [MODEL]]
surfacelock explain [path] [--base FILE]
surfacelock registry [name] [--check] [--path PATH]
surfacelock pin     <alias> [--all] [--path PATH] [--yes]
surfacelock doctor  [path]
surfacelock findings
```

Global: `--version`, `-h`/`--help`.

## `surfacelock` (no arguments)

Dispatches on the presence of `surface.lock`:

- lockfile exists → runs `check`
- no lockfile → prints a `scan` summary and hints at `init`

`surfacelock <path>` behaves the same way for a given directory.

## `scan`

Show the AI surface. **Writes nothing.**

| Flag | Meaning |
|---|---|
| `--json` | Emit the versioned `scan.v1` envelope |

Exit code: `0`.

## `init`

Write `surface.lock`, then print policy findings.

| Flag | Meaning |
|---|---|
| `--force` | Overwrite an existing lockfile |

Exit code: `0`, or `1` if policy reports errors.

## `check`

Rescan, diff against `surface.lock`, and run policy. The CI gate.

| Flag | Meaning |
|---|---|
| `--format text\|json\|markdown` | Output format (default `text`) |
| `--allow-drift` | Report drift but do not fail on it; policy errors still fail |
| `--today YYYY-MM-DD` | Evaluate retirement windows as of this date |

Exit codes: `0` ok · `1` drift or policy error · `2` no lockfile.

## `update`

Rewrite `surface.lock`, keeping existing pins. Prints changes with token and
cost deltas.

| Flag | Meaning |
|---|---|
| `--resolve [MODEL]` | Re-pin a named model, or `all`, to current snapshots |

Exit code: `0`.

## `explain`

Render the Markdown PR summary: a change table, net token and cost deltas,
policy findings, and a suggested regression check when a model snapshot moved.
Safe to paste into a GitHub comment.

| Flag | Meaning |
|---|---|
| `--base FILE` | Diff against a specific lockfile instead of the working tree |

Exit code: `0`.

## `registry`

| Form | Meaning |
|---|---|
| `registry` | Print the retirement calendar, soonest first |
| `registry <name>` | Print one resolved entry as JSON |
| `registry --check` | Validate the registry against its schema |

Exit codes: `0`, or `1` when a lookup fails or validation reports a problem.

## `pin`

**Rewrites source.** Replaces a floating alias literal with its pinned
snapshot, in Python, TypeScript, JavaScript, YAML and JSON.

| Flag | Meaning |
|---|---|
| `--all` | Pin every floating alias found, not just one |
| `--path PATH` | Repository root (default `.`) |
| `--yes` | Skip the confirmation prompt |

Shows a unified diff and asks for confirmation before writing. Only the literal
is touched: quotes, indentation and trailing comments are preserved. Running it
twice changes nothing the second time.

Exit code: `0`.

## `doctor`

Environment diagnostics: version, registry date, whether a config file was
found, which ignore files are in effect, and the timing of the last scan.

Exit code: `0`.

## `findings`

List every finding code with its severity and documentation URL.

Exit code: `0`.
"""

FILES["reference/index.md"] = """# Reference

- [CLI reference](cli.md) — every command and flag.
- [JSON schemas](../schemas.md) — `scan.v1` and `check.v1`.
- [Python API](../python-api.md) — `scan`, `build_lock`, `check`.
- [Findings](../findings/index.md) — all 13 codes.
- [Configuration](../configuration.md) — `surfacelock.toml`.
"""


MKDOCS = """site_name: surfacelock
site_description: >-
  A lockfile for the AI surface of your codebase — pins models, prompts, tool
  schemas and MCP servers, and fails CI when they change without review.
site_url: https://iggym.github.io/surfacelock/
repo_url: https://github.com/iggym/surfacelock
repo_name: iggym/surfacelock
edit_uri: edit/main/docs/

theme:
  name: material
  language: en
  logo: https://raw.githubusercontent.com/iggym/surfacelock/main/docs/assets/logo.svg
  favicon: https://raw.githubusercontent.com/iggym/surfacelock/main/docs/assets/logo.svg
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: deep purple
      accent: deep purple
      toggle:
        icon: material/weather-night
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: deep purple
      accent: deep purple
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - navigation.indexes
    - content.code.copy
    - content.code.annotate
    - search.suggest
    - search.highlight
    - toc.follow

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - toc:
      permalink: true
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg

plugins:
  - search

nav:
  - Home: index.md
  - Quickstart: quickstart.md
  - Concepts: concepts.md
  - Detection: detection.md
  - Configuration: configuration.md
  - CI: ci.md
  - Registry: registry.md
  - Findings:
      - findings/index.md
      - UNPINNED_MODEL: findings/UNPINNED_MODEL.md
      - UNKNOWN_MODEL: findings/UNKNOWN_MODEL.md
      - MODEL_DEPRECATED: findings/MODEL_DEPRECATED.md
      - MODEL_RETIRING: findings/MODEL_RETIRING.md
      - MODEL_RETIRED: findings/MODEL_RETIRED.md
      - MODEL_DENIED: findings/MODEL_DENIED.md
      - MODEL_NOT_ALLOWED: findings/MODEL_NOT_ALLOWED.md
      - PROVIDER_NOT_ALLOWED: findings/PROVIDER_NOT_ALLOWED.md
      - MCP_INSECURE: findings/MCP_INSECURE.md
      - MCP_UNPINNED: findings/MCP_UNPINNED.md
      - PROMPT_TOO_LARGE: findings/PROMPT_TOO_LARGE.md
      - PROMPT_NO_OWNER: findings/PROMPT_NO_OWNER.md
      - PROMPT_ID_COLLISION: findings/PROMPT_ID_COLLISION.md
  - Reference:
      - reference/index.md
      - CLI: reference/cli.md
      - JSON schemas: schemas.md
      - Python API: python-api.md
  - FAQ: faq.md
  - Stability: stability.md

strict: true

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/iggym/surfacelock
    - icon: fontawesome/brands/python
      link: https://pypi.org/project/surfacelock/
  generator: false

copyright: >-
  Copyright 2026 surfacelock contributors · Apache-2.0
"""


def main() -> None:
    for rel, content in FILES.items():
        path = DOCS / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (ROOT / "mkdocs.yml").write_text(MKDOCS, encoding="utf-8")
    print(f"wrote {len(FILES)} docs pages + mkdocs.yml")


if __name__ == "__main__":
    main()

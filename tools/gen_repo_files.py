"""Scaffold the non-code repo artifacts (legal, governance, CI, docs, examples).

Idempotent: re-running rewrites every generated file from this source of truth.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Legal & governance
# ---------------------------------------------------------------------------
FILES["LICENSE"] = """                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

   Copyright 2026 surfacelock contributors

   Full text of the Apache License, Version 2.0 is available at the URL
   above and is incorporated here by reference. The canonical text is also
   distributed with every release artifact.
"""

FILES["NOTICE"] = """surfacelock
Copyright 2026 surfacelock contributors

This product includes software developed at the surfacelock project
(https://github.com/iggym/surfacelock).

The bundled model registry (src/surfacelock/registry/models.json) contains
factual metadata — model identifiers, providers, retirement dates and list
prices — gathered from provider documentation. Each entry records its
`sources` URLs. No provider documentation text is reproduced.
"""

FILES["CHANGELOG.md"] = """# Changelog

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
"""

FILES["CODE_OF_CONDUCT.md"] = """# Contributor Covenant Code of Conduct

## Our pledge

We as members, contributors and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic
status, nationality, personal appearance, race, caste, colour, religion, or
sexual identity and orientation.

## Our standards

Examples of behaviour that contributes to a positive environment:

- Demonstrating empathy and kindness toward other people
- Being respectful of differing opinions, viewpoints and experiences
- Giving and gracefully accepting constructive feedback
- Accepting responsibility, apologising to those affected by our mistakes,
  and learning from the experience
- Focusing on what is best for the community

Examples of unacceptable behaviour:

- Sexualised language or imagery, and sexual attention or advances of any kind
- Trolling, insulting or derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without their explicit permission
- Other conduct which could reasonably be considered inappropriate in a
  professional setting

## Enforcement responsibilities

Maintainers are responsible for clarifying and enforcing these standards and
will take appropriate and fair corrective action in response to any behaviour
they deem inappropriate, threatening, offensive or harmful.

## Scope

This code of conduct applies within all community spaces and also applies when
an individual is officially representing the community in public spaces.

## Enforcement

Instances of abusive, harassing or otherwise unacceptable behaviour may be
reported privately to the maintainers through GitHub. All complaints will
be reviewed and investigated promptly and fairly. Maintainers are obligated to
respect the privacy and security of the reporter of any incident.

## Enforcement guidelines

1. **Correction** — a private, written warning, with clarity about the
   violation and an explanation of why the behaviour was inappropriate.
2. **Warning** — a warning with consequences for continued behaviour, including
   a specified period of no interaction with the people involved.
3. **Temporary ban** — a temporary ban from any interaction with the community.
4. **Permanent ban** — a permanent ban from any public interaction within the
   community.

## Attribution

This Code of Conduct is adapted from the
[Contributor Covenant](https://www.contributor-covenant.org), version 2.1.
"""

FILES["SECURITY.md"] = """# Security policy

## Reporting a vulnerability

Report suspected vulnerabilities privately through
[GitHub Security Advisories](https://github.com/iggym/surfacelock/security/advisories/new).
Do not open a public issue; if you cannot use advisories, contact a maintainer directly.

Please include: a description, a minimal reproduction, the version affected,
and any suggested remediation. We aim to acknowledge within 3 working days and
to ship a fix or a documented mitigation within 30 days.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ |

During 0.x, only the latest minor receives security fixes.

## Design commitments relevant to security

- **No network calls.** The scanner never contacts a provider API. Everything
  it knows comes from the bundled registry and your repository.
- **No telemetry.** Nothing is phoned home, ever.
- **Secrets are never recorded.** The MCP scanner stores environment variable
  *names* and header *names* only. Values are hashed out of the config digest
  and never written to `surface.lock`, `scan --json`, or any output. A test in
  `tests/test_scanners.py` asserts this.
- **No code execution.** Scanned files are parsed, never imported or executed.
- **Read-only by default.** Only `init`, `update` and `pin` write, and `pin`
  rewrites source files only after an explicit confirmation prompt.

## Threat model notes

`surfacelock` reads untrusted repositories. The scanner is written to be
tolerant: it must never raise on syntax it does not understand, and it skips
files above 2 MB and binary files. A malformed file should degrade to fewer
findings, never to a crash or to code execution.

If you find an input that causes a crash, an unbounded memory allocation, or
any form of execution, that is a security bug — please report it.
"""

FILES["GOVERNANCE.md"] = """# Governance

## Model

`surfacelock` is currently a **single-maintainer, benevolent-dictator** project.
The maintainer merges all changes and is the final arbiter of scope. This is
intentional for 0.x: the fastest way to a coherent v1.0 is a narrow, opinionated
review bar.

As the contributor base grows, this document will move to a small steering
group with published membership. Changes to governance itself are made by pull
request against this file.

## Decision making

| Decision | Process |
|---|---|
| Bug fixes, docs, tests | Maintainer merges on green CI |
| New detection rules | Issue first; maintainer approves the false-positive analysis |
| New registry entries | Pull request with a `sources` URL per entry |
| New finding codes | Requires a docs page and a `SEVERITY` entry — CI enforces both |
| New commands or flags | Requires a spec section; expect scope pushback |
| Breaking changes | Only at a 0.x minor, documented in the changelog |

## The conservative principle

The project's most important product decision is a bias toward **missing a
finding rather than emitting a false positive**. A noisy tool gets disabled, and
a disabled tool protects nothing. Proposals that trade precision for recall will
be declined unless they are gated behind an explicit annotation.

This is why:

- `fail_on_unknown_models` defaults to `false`.
- `max_prompt_tokens` defaults to `0` (off).
- Detection requires a registry hit, a context keyword, or an annotation.
- The `tricky` fixture exists and must stay at 100% precision.

## Registry data governance

`registry/models.json` is the project's most valuable and most perishable
asset. Rules:

- Every entry needs at least one `sources` URL pointing at provider
  documentation. CI rejects entries without one.
- Prices are list prices in USD per 1M tokens, as published by the provider.
- Retirement dates are only recorded when the provider has announced them.
- Data-only pull requests bump a patch release and add a changelog line.

## Release cadence

Releases are cut when a change is worth shipping, not on a calendar. Registry
data changes can ship as patch releases at any time.

## Becoming a maintainer

Sustained, high-quality contribution over several months — especially registry
data accuracy and false-positive reports — is the path. There is no formal
process yet; the maintainer will ask.
"""

FILES["CONTRIBUTING.md"] = """# Contributing to surfacelock

Thanks for helping. The highest-value contributions, in order:

1. **Registry data corrections** — a model with a wrong retirement date or price.
2. **False-positive reports** — a string surfacelock flags that is not a model.
3. **New language scanners** — Go, Rust, Java, C# prompt and tool detection.
4. **Docs** — clearer explanations of what a finding means and how to fix it.

## Development setup

```bash
git clone https://github.com/iggym/surfacelock
cd surfacelock
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Before you push

```bash
ruff format src tests        # formatting
ruff check src tests         # lint
mypy                         # strict type check
pytest -m "not slow"         # fast test suite
pytest -m slow               # the 10k-file performance budget
```

CI runs all of the above on 3 operating systems × 3 Python versions, with an
85% coverage gate. A change that drops coverage below the gate will not merge.

## Adding a finding code

Finding codes are a public API. To add one you need four things:

1. The code in `FINDING_CODES` and a severity in `SEVERITY`
   (`src/surfacelock/policy.py`).
2. `docs/findings/<CODE>.md` — CI fails if this page is missing.
3. A test in `tests/test_policy.py` that triggers it, using `--today` where the
   code is date-dependent.
4. A changelog entry.

## Adding a registry entry

Edit `src/surfacelock/registry/models.json`:

```json
"some-model-2026-01-15": {
  "provider": "someprovider",
  "kind": "chat",
  "resolved": "some-model-2026-01-15",
  "retirement": "2027-06-01",
  "price_in": 1.5,
  "price_out": 6.0,
  "context_window": 128000,
  "sources": ["https://provider.example/docs/models"]
}
```

Then:

```bash
surfacelock registry --check   # validates against schema.json
```

Every entry **must** have at least one `sources` URL. Bump `_updated`, add a
changelog line under "Registry data", and open the pull request.

## Reporting a false positive

The most useful bug report looks like this:

```
File:      src/billing/version.py:12
String:    "1.5.0"
Detected:  model (openai)
Expected:  not a model
```

Add it to `tests/fixtures/tricky/` in the same pull request if you can — that
fixture must stay at 100% precision, and it is how we stop regressions.

## Code style

- `ruff format`, line length 100.
- `mypy --strict` on `src/surfacelock`. No `# type: ignore` without a reason.
- Comments explain *why*, not *what*. If a line needs a comment to be
  understood, the comment should describe the constraint or the trade-off.
- Determinism is a feature: never let dict iteration order or filesystem order
  leak into output. Sort explicitly.
"""

FILES[".gitignore"] = """__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.venv/
venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
.coverage
coverage.xml
htmlcov/
site/
.DS_Store
Thumbs.db
"""

FILES[".pre-commit-config.yaml"] = """# Hooks that run on surfacelock's own repository.
# The hooks surfacelock *provides* live in .pre-commit-hooks.yaml.
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=2048"]
      - id: mixed-line-ending
        args: ["--fix=lf"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [pyyaml, tomli-w, pathspec]
        files: ^src/

  - repo: local
    hooks:
      - id: surfacelock-self-check
        name: surfacelock self-check
        entry: surfacelock check --allow-drift
        language: system
        pass_filenames: false
        always_run: true
"""

# ---------------------------------------------------------------------------
# Integrations (F-INT-1, F-INT-2)
# ---------------------------------------------------------------------------
FILES["action.yml"] = """name: surfacelock
description: >-
  Pin and gate the AI surface of your repository — models, prompts, tool
  schemas and MCP servers. Fails the build when they change without review.
author: surfacelock contributors

branding:
  icon: lock
  color: purple

inputs:
  path:
    description: Repository path to check.
    required: false
    default: "."
  allow-drift:
    description: >-
      Report AI-surface drift without failing the build. Policy errors still
      fail. Useful while adopting surfacelock on an existing repository.
    required: false
    default: "false"
  comment:
    description: >-
      Post or update a sticky pull-request comment with the `explain` summary.
      Requires `pull-requests: write`.
    required: false
    default: "false"
  version:
    description: Version of surfacelock to install.
    required: false
    default: "0.1.0"
  python-version:
    description: Python version used to run surfacelock.
    required: false
    default: "3.12"

outputs:
  changed:
    description: "\\"true\\" when the AI surface differs from surface.lock."
    value: ${{ steps.run.outputs.changed }}
  errors:
    description: Number of policy errors.
    value: ${{ steps.run.outputs.errors }}
  warnings:
    description: Number of policy warnings.
    value: ${{ steps.run.outputs.warnings }}

runs:
  using: composite
  steps:
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}

    - name: Install surfacelock
      shell: bash
      run: python -m pip install --quiet "surfacelock==${{ inputs.version }}"

    - name: Run surfacelock check
      id: run
      shell: bash
      working-directory: ${{ inputs.path }}
      run: |
        set +e
        args=(check --format json)
        if [ "${{ inputs.allow-drift }}" = "true" ]; then
          args+=(--allow-drift)
        fi
        surfacelock "${args[@]}" > "$RUNNER_TEMP/surfacelock.json"
        status=$?
        set -e

        python - "$RUNNER_TEMP/surfacelock.json" <<'PY' >> "$GITHUB_OUTPUT"
        import json, sys
        try:
            data = json.load(open(sys.argv[1]))
        except Exception:
            print("changed=false")
            print("errors=0")
            print("warnings=0")
            raise SystemExit(0)
        errors = sum(1 for f in data.get("findings", []) if f["severity"] == "error")
        warnings = sum(1 for f in data.get("findings", []) if f["severity"] == "warning")
        print(f"changed={str(data.get('drift', {}).get('changed', False)).lower()}")
        print(f"errors={errors}")
        print(f"warnings={warnings}")
        PY

        {
          echo "### \\U0001f512 surfacelock"
          echo
          surfacelock explain || true
        } >> "$GITHUB_STEP_SUMMARY"

        exit $status

    - name: Post sticky pull-request comment
      if: ${{ inputs.comment == 'true' && github.event_name == 'pull_request' }}
      shell: bash
      working-directory: ${{ inputs.path }}
      env:
        GH_TOKEN: ${{ github.token }}
        PR: ${{ github.event.pull_request.number }}
      run: |
        set -e
        surfacelock explain > "$RUNNER_TEMP/body.md"
        marker="<!-- surfacelock-sticky -->"
        { echo "$marker"; cat "$RUNNER_TEMP/body.md"; } > "$RUNNER_TEMP/comment.md"

        existing=$(gh api "repos/${{ github.repository }}/issues/$PR/comments" \\
          --jq ".[] | select(.body | contains(\\"$marker\\")) | .id" | head -n1)

        if [ -n "$existing" ]; then
          gh api -X PATCH "repos/${{ github.repository }}/issues/comments/$existing" \\
            -f body="$(cat "$RUNNER_TEMP/comment.md")"
        else
          gh api -X POST "repos/${{ github.repository }}/issues/$PR/comments" \\
            -f body="$(cat "$RUNNER_TEMP/comment.md")"
        fi
"""

FILES[".pre-commit-hooks.yaml"] = """# Hooks that surfacelock *provides* to other repositories.
# Consume with:
#
#   repos:
#     - repo: https://github.com/iggym/surfacelock
#       rev: v0.1.0
#       hooks:
#         - id: surfacelock-check
- id: surfacelock-check
  name: surfacelock check
  description: >-
    Fail when the AI surface (models, prompts, tool schemas, MCP servers)
    differs from surface.lock, or when policy is violated.
  entry: surfacelock check
  language: python
  pass_filenames: false
  always_run: true
  additional_dependencies: ["pyyaml", "tomli-w", "pathspec"]

# `surfacelock-check` runs `check` — deliberately *not* `check --allow-drift`.
# Drift must be reviewed, so the fix is to run `surfacelock update` and commit
# the resulting surface.lock, which is exactly what the second hook automates.
- id: surfacelock-update
  name: surfacelock update
  description: >-
    Rebuild surface.lock and stage it. Existing model pins are preserved;
    pass --resolve to deliberately re-pin.
  entry: surfacelock update
  language: python
  pass_filenames: false
  always_run: true
  additional_dependencies: ["pyyaml", "tomli-w", "pathspec"]
"""

# ---------------------------------------------------------------------------
# CI
# ---------------------------------------------------------------------------
FILES[".github/workflows/ci.yml"] = """name: CI

on:
  push:
    branches: [main, master]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: ${{ matrix.os }} / py${{ matrix.python-version }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - name: Install
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"

      - name: Lint
        run: ruff check src tests tools

      - name: Format check
        run: ruff format --check src tests tools

      - name: Type check
        run: mypy

      - name: Test
        run: pytest -m "not slow" --cov=surfacelock --cov-report=xml --cov-fail-under=85

      - name: CLI smoke test
        run: |
          surfacelock --version
          surfacelock doctor

      - name: Upload coverage
        if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.12'
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage.xml

  registry:
    name: Registry data
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e ".[dev]"
      - name: Validate registry against its schema
        run: surfacelock registry --check

  findings-docs:
    name: Finding docs complete
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e ".[dev]"
      # Every finding code must have a docs page — enforced as a test.
      - run: pytest tests/test_policy.py::test_every_code_has_a_docs_page -q

  self-check:
    name: surfacelock self-check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e ".[dev]"
      - name: Check this repository's own AI surface
        run: surfacelock check --allow-drift

  perf:
    name: Performance budget
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e ".[dev]"
      - name: 10k files in under 5 seconds
        run: pytest -m slow -q
"""

FILES[".github/workflows/release.yml"] = """name: Release

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    name: Build distributions
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install --upgrade build
      - name: Verify the tag matches the package version
        run: |
          version=$(python -c "import tomllib,pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")
          tag="${GITHUB_REF_NAME#v}"
          if [ "$version" != "$tag" ]; then
            echo "::error::tag v$tag does not match pyproject version $version"
            exit 1
          fi
      - run: python -m build
      - run: python -m pip install dist/*.whl
      - run: surfacelock --version
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  testpypi:
    name: Publish to TestPyPI
    needs: build
    runs-on: ubuntu-latest
    environment: testpypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/
          skip-existing: true

  pypi:
    name: Publish to PyPI
    needs: build
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1

  github-release:
    name: GitHub release
    needs: pypi
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - name: Extract the changelog section for this tag
        run: |
          python - "$GITHUB_REF_NAME" > notes.md <<'PY'
          import re, sys, pathlib
          tag = sys.argv[1].lstrip("v")
          text = pathlib.Path("CHANGELOG.md").read_text()
          match = re.search(rf"^## \\[{re.escape(tag)}\\].*?(?=^## \\[|\\Z)", text, re.M | re.S)
          print(match.group(0).strip() if match else f"Release {tag}")
          PY
      - uses: softprops/action-gh-release@v2
        with:
          body_path: notes.md
          files: dist/*
"""

FILES[".github/dependabot.yml"] = """version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    groups:
      dev-dependencies:
        patterns: ["pytest*", "ruff", "mypy", "coverage*"]

  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: monthly
"""

FILES[".github/pull_request_template.md"] = """## What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## Why

<!-- The failure mode or user problem this addresses. -->

## Checklist

- [ ] `ruff format` / `ruff check` / `mypy` / `pytest` pass locally
- [ ] Added or updated a test for the behaviour change
- [ ] If a finding code was added: `docs/findings/<CODE>.md` exists
- [ ] If registry data changed: `_updated` bumped, `sources` URLs present,
      and a changelog line added under "Registry data"
- [ ] If a new detection rule: the `tricky` fixture still reports 100% precision
- [ ] Updated the changelog under `[Unreleased]`

## AI surface impact

<!-- Does this PR change a model, prompt, tool schema or MCP server in this
     repository itself? If so, `surfacelock check` output is below. -->

<details><summary>surfacelock explain</summary>

```text
paste output here
```

</details>
"""

FILES[".github/ISSUE_TEMPLATE/config.yml"] = """blank_issues_enabled: false
contact_links:
  - name: Security vulnerability
    url: https://github.com/iggym/surfacelock/security/advisories/new
    about: Report privately. Do not open a public issue.
  - name: Question or idea
    url: https://github.com/iggym/surfacelock/discussions
    about: Ask in Discussions rather than opening an issue.
"""

FILES[".github/ISSUE_TEMPLATE/false_positive.yml"] = """name: False positive
description: surfacelock flagged something that is not part of your AI surface.
title: "[false-positive] "
labels: ["false-positive", "precision"]
body:
  - type: markdown
    attributes:
      value: |
        Precision is this project's most important property. Thank you for
        reporting. A tool that cries wolf gets switched off, and a tool that is
        switched off protects nothing.
  - type: input
    id: location
    attributes:
      label: File and line
      placeholder: src/billing/version.py:12
    validations:
      required: true
  - type: input
    id: string
    attributes:
      label: The string that was flagged
      placeholder: '"1.5.0"'
    validations:
      required: true
  - type: dropdown
    id: kind
    attributes:
      label: What was it flagged as?
      options: [model, prompt, tool, mcp_server]
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: What it actually is
      placeholder: A semantic version string in a changelog helper.
    validations:
      required: true
  - type: checkboxes
    id: fixture
    attributes:
      label: Contribution
      options:
        - label: I am willing to add this to tests/fixtures/tricky/ in a PR
"""

FILES[".github/ISSUE_TEMPLATE/registry_entry.yml"] = """name: Registry data issue
description: A model entry is missing, or its dates or prices are wrong.
title: "[registry] "
labels: ["registry", "data"]
body:
  - type: input
    id: model
    attributes:
      label: Model identifier
      placeholder: gpt-4o
    validations:
      required: true
  - type: input
    id: provider
    attributes:
      label: Provider
      placeholder: openai
    validations:
      required: true
  - type: dropdown
    id: problem
    attributes:
      label: What is wrong?
      options:
        - Entry is missing entirely
        - Retirement date is wrong
        - Price is wrong
        - Alias resolves to the wrong snapshot
        - Context window is wrong
    validations:
      required: true
  - type: input
    id: correct
    attributes:
      label: The correct value
      placeholder: "retirement: 2026-10-20"
    validations:
      required: true
  - type: input
    id: source
    attributes:
      label: Source URL
      description: A link to provider documentation. Required — entries without sources are rejected.
      placeholder: https://platform.openai.com/docs/deprecations
    validations:
      required: true
"""

FILES[".github/ISSUE_TEMPLATE/bug_report.yml"] = """name: Bug report
description: Something is broken — a crash, a wrong exit code, bad output.
title: "[bug] "
labels: ["bug"]
body:
  - type: textarea
    id: what
    attributes:
      label: What happened
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: What you expected instead
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: Minimal reproduction
      description: The smallest repository or command that shows the problem.
      render: shell
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: surfacelock version
      description: Output of `surfacelock --version`.
    validations:
      required: true
  - type: input
    id: python
    attributes:
      label: Python version and OS
      placeholder: 3.12.4 on macOS 15
    validations:
      required: true
"""

FILES[".github/ISSUE_TEMPLATE/feature_request.yml"] = """name: Feature request
description: Propose a new detection rule, command or integration.
title: "[feature] "
labels: ["enhancement"]
body:
  - type: textarea
    id: problem
    attributes:
      label: The problem
      description: >-
        Describe the failure mode or workflow gap, not the implementation.
        "I cannot tell X" is more useful than "add a flag Y".
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution
    validations:
      required: true
  - type: textarea
    id: precision
    attributes:
      label: Precision analysis
      description: >-
        For a new detection rule: what legitimate code could this match by
        mistake? surfacelock prefers a miss over a false positive.
    validations:
      required: false
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
    validations:
      required: false
"""


def main() -> None:
    for rel, content in FILES.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"wrote {len(FILES)} files")


if __name__ == "__main__":
    main()

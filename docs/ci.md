# CI integration

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

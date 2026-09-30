# Contributing to surfacelock

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

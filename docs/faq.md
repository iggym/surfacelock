# FAQ

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

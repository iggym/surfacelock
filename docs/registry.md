# The model registry

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

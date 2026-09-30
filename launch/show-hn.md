# Show HN

## Title

Show HN: surfacelock – a lockfile for your models, prompts, tools and MCP servers

## Body

I kept hitting the same class of bug: an AI feature regresses and the git
history is clean. The model alias resolved to a new snapshot, or someone tidied
a prompt in a typo-fix PR, or an MCP server's `npx` package changed under us.

We solved this for dependencies years ago — lockfile plus a CI check — so I
built the same thing for the AI surface.

`surfacelock scan` finds model identifiers, prompts, tool schemas and MCP
server configs. `surfacelock init` writes `surface.lock`. `surfacelock check`
fails CI when they drift, and `surfacelock explain` produces a PR comment with
token and cost deltas.

Two design choices I would especially like feedback on:

1. **Pins are kept, not followed.** `check` and `update` never re-resolve an
   existing pin against current registry data — only `update --resolve` does,
   deliberately. My reasoning is that a lockfile which follows the registry
   guarantees nothing, but I would like to hear counterarguments.

2. **Conservative detection.** A string is only a model if the registry knows
   it, or the line has a model-context keyword, or it is annotated. I would
   rather miss a dynamic model string than flood a repo with false positives,
   because a noisy gate gets switched off. There is a fixture of
   false-positive traps and CI requires 100% precision on it.

No network calls, no telemetry, no provider API introspection — the registry is
a bundled JSON file with source URLs per entry.

Apache-2.0, Python 3.11+. Happy to answer anything about the detection rules,
the registry data, or where this overlaps with what you already do.

## First comment (post immediately)

Registry accuracy is the thing most likely to be wrong, and it is the thing I
can least fix alone. If a model's retirement date or price is off, the entries
live in `src/surfacelock/registry/models.json` and each one carries a `sources`
URL — issues or PRs both welcome.

The bundled registry ships with 176 entries across ten providers. Prices are
list prices per 1M tokens as published; retirement dates are only recorded when
the provider has announced them, because a guessed date produces false
`MODEL_RETIRING` errors.

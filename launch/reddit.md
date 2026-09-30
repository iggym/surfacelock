# Reddit posts

## r/LocalLLaMA

**Title:** I built a lockfile for the AI layer of a repo (models, prompts, tools, MCP servers)

**Body:**

Local models have the same problem as hosted ones, and in some ways a worse
one: a GGUF gets requantised, a tag moves, an Ollama model is re-pulled and the
behaviour shifts. There is nothing in the repository that records what you were
actually running.

`surfacelock` scans for model references, prompts, tool schemas and MCP server
configs, writes a `surface.lock`, and fails CI when any of them change without
review. It works with any provider name — including local ones, if you add them
to `.surfacelock/models.json`, which is how you teach it about your own
gateway or a fine-tune.

It is a static analyser: no network calls, no telemetry, and it never imports
or executes anything it scans.

Apache-2.0, `pipx install surfacelock`. Feedback on the detection rules
especially welcome — precision matters more to me than recall here.

## r/MLOps

**Title:** Lockfiles for the AI surface: pinning models, prompts and MCP servers the way we pin dependencies

**Body:**

The recurring incident class on our team was "the AI feature changed and the
diff was empty". Four flavours:

1. Model aliases resolving to new snapshots.
2. Prompts edited in unrelated PRs.
3. Tool schemas and MCP configs widening an agent's permissions.
4. Provider retirements discovered from a production 404.

`surfacelock` treats all four as one problem and applies the dependency-lockfile
pattern: scan, freeze into `surface.lock`, gate in CI, review the diff.

Things I would particularly like MLOps feedback on:

- **Pin-keeping semantics.** `check`/`update` never re-resolve an existing pin
  against current registry data. Only `update --resolve` re-pins, explicitly.
- **Retirement windows.** Defaults are warn at 90 days, fail at 30. `check
  --today` lets a scheduled nightly run advance the window without any code
  change.
- **Registry data as a release artifact.** Registry-only changes bump a patch
  version, so a `check` failure can appear from a version bump alone. I think
  this is correct, but it is a sharp edge worth documenting loudly.

Apache-2.0, no telemetry, no network calls. `surfacelock scan --json` emits a
versioned schema if you want to feed an inventory system.

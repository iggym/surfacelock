# 🔒 surfacelock

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

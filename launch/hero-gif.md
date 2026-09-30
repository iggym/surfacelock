# Hero GIF storyboard

Target: 12–18 seconds, 1200×700, dark terminal, no audio. Loops cleanly.

## Frame 1 — the problem (0–3 s)

```
$ surfacelock scan
```

Output reveals a floating alias three weeks from retirement:

```
🧠 models
   claude-3-5-sonnet-latest   src/support.py:21   anthropic · floating
                              ⚠ retires 2026-10-20 (21 days)
```

## Frame 2 — freeze it (3–6 s)

```
$ surfacelock init
```

The alias is pinned in the lockfile; source is untouched.

```
wrote surface.lock · 3 models · 4 prompts · 2 tools · 2 mcp servers
```

## Frame 3 — the drift (6–11 s)

A prompt is edited and the model snapshot is bumped. Run `check`:

```
$ surfacelock check

  AI surface drift:
  ✏️  model   claude-3-5-sonnet-latest  claude-3-5-sonnet-20241022 → …
  ✏️  prompt  support.system            412 → 453 tokens (+41)

  ✖ MODEL_RETIRING  src/support.py:21
      `claude-3-5-sonnet-latest` retires on 2026-10-20 (21 days)
      https://iggym.github.io/surfacelock/findings/MODEL_RETIRING/

  1 errors · 0 warnings · 0 suppressed
  ✖ check failed
```

## Frame 4 — the review artifact (11–15 s)

```
$ surfacelock explain
```

Cut to the rendered GitHub comment: the change table, `+41 tokens/call`,
`+$0.0001/call`, and the suggested regression check.

```
<details><summary>Suggested regression check</summary>
modelbump diff --from claude-3-5-sonnet-20241022 --to … --suite golden/
</details>
```

## Frame 5 — resolution (15–17 s)

```
$ surfacelock update --resolve claude-3-5-sonnet-latest
```

Before/after printed. `check` passes. Cut to the logo.

## Production notes

- Use a real repository, not a mock — the realism is the point.
- Keep the prompt-token delta at `+41`: specific numbers read as evidence,
  round numbers read as marketing.
- No narration. If a caption is needed, use one line: *"The AI layer changed.
  The diff was empty. Now it is not."*

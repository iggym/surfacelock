# MODEL_DEPRECATED

> **Model retiring soon (warning window)** — warning

## What it means

The pinned model has a retirement date inside the warning window — 90 days by default.

## Why it matters

Providers announce retirements months ahead. A warning here means you have time to plan a migration rather than discover it from a 404. Nothing is broken yet.

## How to fix it

Schedule the migration. When you are ready, move to a successor snapshot and re-pin:

```bash
surfacelock registry <model>           # see the retirement date and pricing
surfacelock update --resolve <model>   # re-pin to the current snapshot
```

Tune the window with `deprecation_warn_days` in `surfacelock.toml`.

---

<sub>[← all findings](index.md)</sub>

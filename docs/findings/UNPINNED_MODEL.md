# UNPINNED_MODEL

> **Floating model alias** — error

## What it means

A model identifier in your code is an alias that can resolve to a different snapshot over time.

## Why it matters

`gpt-4o`, `claude-3-5-sonnet-latest` and friends are moving targets. The provider can point them at a new snapshot whenever it likes. Your code does not change, your tests do not change, but the model answering your users does. That is the most common way an AI feature regresses with a clean git history.

## How to fix it

Pin the alias to a dated snapshot, in code or in the lockfile:

```bash
surfacelock pin gpt-4o                 # rewrites the literal in your source
surfacelock update --resolve gpt-4o    # re-pins only in surface.lock
```

If you genuinely need the alias, suppress the finding with a reason:

```python
model = "gpt-4o"  # surfacelock: allow UNPINNED_MODEL reason="SDK requires the alias"
```

---

<sub>[← all findings](index.md)</sub>

# UNKNOWN_MODEL

> **Model not in the registry** — warning

## What it means

The identifier looks like a model but the registry has never heard of it.

## Why it matters

This usually means one of three things: a brand new model the registry has not caught up with, an internal or fine-tuned deployment, or a false positive from a string that merely looks like a model name. The finding is off by default because none of those are necessarily wrong.

## How to fix it

Add the model to `.surfacelock/models.json` with its provider, kind and a source URL:

```json
{
  "models": {
    "acme-internal-20250101": {
      "provider": "acme",
      "kind": "chat",
      "sources": ["https://internal.example/models"]
    }
  }
}
```

Or annotate the literal with `surfacelock: model` to mark it as intentional.

---

<sub>[← all findings](index.md)</sub>

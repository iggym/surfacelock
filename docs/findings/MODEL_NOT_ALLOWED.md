# MODEL_NOT_ALLOWED

> **Model not on the allow list** — error

## What it means

An allow list is configured and this model is not on it.

## Why it matters

Allow lists invert the default: rather than blocking known-bad models, they require every model to be explicitly approved. That is the right posture in regulated environments, and it is why the list is opt-in.

## How to fix it

Add the model to `allow_models` after review:

```toml
[policy]
allow_models = ["gpt-4.1-*", "claude-sonnet-4-*"]
```

Patterns use shell glob syntax.

---

<sub>[← all findings](index.md)</sub>

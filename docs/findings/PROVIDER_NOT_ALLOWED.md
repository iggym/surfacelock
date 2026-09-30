# PROVIDER_NOT_ALLOWED

> **Provider not on the allow list** — error

## What it means

An allow list is configured and this model's provider is not on it.

## Why it matters

Sometimes the constraint is the vendor, not the model: data residency, procurement, or a security review that has only cleared certain providers.

## How to fix it

Add the provider to `allow_providers`, or route the call through an approved provider.

```toml
[policy]
allow_providers = ["openai", "anthropic"]
```

---

<sub>[← all findings](index.md)</sub>

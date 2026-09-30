# MODEL_RETIRED

> **Model already retired** — error

## What it means

The pinned model's retirement date has passed. Calls to it will fail.

## Why it matters

This is the failure mode surfacelock exists to prevent: a production 404 caused by a calendar event rather than a code change. If your lockfile still pins this model, no PR in your history explains the breakage.

## How to fix it

Move to a supported model immediately:

```bash
surfacelock registry             # find a replacement and its pricing
surfacelock update --resolve all
```

If the deployment genuinely still works, set `fail_on_retired = false`.

---

<sub>[← all findings](index.md)</sub>

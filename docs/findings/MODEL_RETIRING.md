# MODEL_RETIRING

> **Model retiring imminently** — error

## What it means

The pinned model retires inside the fail window — 30 days by default.

## Why it matters

Inside 30 days a retirement stops being a planning problem and becomes an outage waiting to happen. Requests to a retired model fail outright, usually with a 404 that surfaces in production rather than CI.

## How to fix it

Migrate now. Identify the successor, run your golden evaluation suite against it, then re-pin:

```bash
modelbump diff --from <current> --to <successor> --suite golden/
surfacelock update --resolve <model>
```

---

<sub>[← all findings](index.md)</sub>

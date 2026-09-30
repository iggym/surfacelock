# PROMPT_ID_COLLISION

> **Two prompts share one id** — error

## What it means

Two different prompt contents claim the same id.

## Why it matters

Prompt ids are the stable key in `surface.lock` and in every diff. If two prompts share an id, the lockfile silently tracks only one of them and drift in the other becomes invisible.

## How to fix it

Give one of them an explicit, unique id:

```python
# surfacelock: prompt id=agent.planner.system
PLANNER = "..."
```

The error message names both colliding locations.

---

<sub>[← all findings](index.md)</sub>

# PROMPT_TOO_LARGE

> **Prompt exceeds the token budget** — error

## What it means

The prompt's approximate token count is above `max_prompt_tokens`.

## Why it matters

Prompt size drives cost and latency, and an unnoticed prompt edit is a silent price rise. A budget turns that into a reviewable number instead of a surprise on the invoice.

## How to fix it

Trim the prompt, or raise the limit if the growth is intentional:

```toml
[policy]
max_prompt_tokens = 2000
```

The default is `0`, which disables the check.

---

<sub>[← all findings](index.md)</sub>

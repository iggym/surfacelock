# PROMPT_NO_OWNER

> **Prompt has no owner** — warning

## What it means

No CODEOWNERS rule matches the prompt's file and `require_prompt_owner` is enabled.

## Why it matters

Prompts are behaviour. Behaviour with no owner is behaviour nobody is accountable for when it drifts. Requiring an owner means a prompt edit requests the right review automatically.

## How to fix it

Add a CODEOWNERS rule:

```text
prompts/        @platform-ai
src/agent.py    @platform-ai
```

Then enable the check:

```toml
[policy]
require_prompt_owner = true
```

---

<sub>[← all findings](index.md)</sub>

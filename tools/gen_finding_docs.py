"""Generate docs/findings/*.md — one page per stable finding code."""

from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs" / "findings"

PAGES = {
    "UNPINNED_MODEL": (
        "Floating model alias",
        "A model identifier in your code is an alias that can resolve to a different snapshot over time.",
        "`gpt-4o`, `claude-3-5-sonnet-latest` and friends are moving targets. The provider can point them at a new snapshot whenever it likes. Your code does not change, your tests do not change, but the model answering your users does. That is the most common way an AI feature regresses with a clean git history.",
        'Pin the alias to a dated snapshot, in code or in the lockfile:\n\n```bash\nsurfacelock pin gpt-4o                 # rewrites the literal in your source\nsurfacelock update --resolve gpt-4o    # re-pins only in surface.lock\n```\n\nIf you genuinely need the alias, suppress the finding with a reason:\n\n```python\nmodel = "gpt-4o"  # surfacelock: allow UNPINNED_MODEL reason="SDK requires the alias"\n```',
    ),
    "UNKNOWN_MODEL": (
        "Model not in the registry",
        "The identifier looks like a model but the registry has never heard of it.",
        "This usually means one of three things: a brand new model the registry has not caught up with, an internal or fine-tuned deployment, or a false positive from a string that merely looks like a model name. The finding is off by default because none of those are necessarily wrong.",
        'Add the model to `.surfacelock/models.json` with its provider, kind and a source URL:\n\n```json\n{\n  "models": {\n    "acme-internal-20250101": {\n      "provider": "acme",\n      "kind": "chat",\n      "sources": ["https://internal.example/models"]\n    }\n  }\n}\n```\n\nOr annotate the literal with `surfacelock: model` to mark it as intentional.',
    ),
    "MODEL_DEPRECATED": (
        "Model retiring soon (warning window)",
        "The pinned model has a retirement date inside the warning window — 90 days by default.",
        "Providers announce retirements months ahead. A warning here means you have time to plan a migration rather than discover it from a 404. Nothing is broken yet.",
        "Schedule the migration. When you are ready, move to a successor snapshot and re-pin:\n\n```bash\nsurfacelock registry <model>           # see the retirement date and pricing\nsurfacelock update --resolve <model>   # re-pin to the current snapshot\n```\n\nTune the window with `deprecation_warn_days` in `surfacelock.toml`.",
    ),
    "MODEL_RETIRING": (
        "Model retiring imminently",
        "The pinned model retires inside the fail window — 30 days by default.",
        "Inside 30 days a retirement stops being a planning problem and becomes an outage waiting to happen. Requests to a retired model fail outright, usually with a 404 that surfaces in production rather than CI.",
        "Migrate now. Identify the successor, run your golden evaluation suite against it, then re-pin:\n\n```bash\nmodelbump diff --from <current> --to <successor> --suite golden/\nsurfacelock update --resolve <model>\n```",
    ),
    "MODEL_RETIRED": (
        "Model already retired",
        "The pinned model's retirement date has passed. Calls to it will fail.",
        "This is the failure mode surfacelock exists to prevent: a production 404 caused by a calendar event rather than a code change. If your lockfile still pins this model, no PR in your history explains the breakage.",
        "Move to a supported model immediately:\n\n```bash\nsurfacelock registry             # find a replacement and its pricing\nsurfacelock update --resolve all\n```\n\nIf the deployment genuinely still works, set `fail_on_retired = false`.",
    ),
    "MODEL_DENIED": (
        "Model on the deny list",
        "The model matches an entry in `deny_models`.",
        "Organisations have legitimate reasons to forbid a model: an unresolved data-processing agreement, a compliance boundary, a known jailbreak surface, or a cost blowout. Encoding that in policy means it is enforced on every PR rather than remembered in a wiki.",
        "Replace the model with an approved one. If the ban no longer applies, remove the pattern from `deny_models` in `surfacelock.toml` — as a reviewed change, with a reason in the PR.",
    ),
    "MODEL_NOT_ALLOWED": (
        "Model not on the allow list",
        "An allow list is configured and this model is not on it.",
        "Allow lists invert the default: rather than blocking known-bad models, they require every model to be explicitly approved. That is the right posture in regulated environments, and it is why the list is opt-in.",
        'Add the model to `allow_models` after review:\n\n```toml\n[policy]\nallow_models = ["gpt-4.1-*", "claude-sonnet-4-*"]\n```\n\nPatterns use shell glob syntax.',
    ),
    "PROVIDER_NOT_ALLOWED": (
        "Provider not on the allow list",
        "An allow list is configured and this model's provider is not on it.",
        "Sometimes the constraint is the vendor, not the model: data residency, procurement, or a security review that has only cleared certain providers.",
        'Add the provider to `allow_providers`, or route the call through an approved provider.\n\n```toml\n[policy]\nallow_providers = ["openai", "anthropic"]\n```',
    ),
    "MCP_INSECURE": (
        "Insecure MCP transport",
        "An MCP server is configured over plaintext `http://`.",
        "An MCP server is a capability grant. Over plaintext HTTP, anyone on the network path can read the tool calls and their arguments, and can modify the responses your agent then acts on. It is one man-in-the-middle away from arbitrary tool execution.",
        'Switch the endpoint to `https://`:\n\n```json\n{ "mcpServers": { "crm": { "url": "https://crm.internal.example/mcp" } } }\n```\n\nIf the server only speaks plaintext, put it behind a TLS-terminating proxy on localhost rather than exposing it on the network.',
    ),
    "MCP_UNPINNED": (
        "Unpinned MCP server package",
        "A `npx`/`uvx`/`bunx`/`pipx` server is launched without a version.",
        "`npx -y some-mcp-server` fetches whatever is latest at the moment your agent starts. The maintainer — or someone who compromises the package — can change what code your agent runs, with no diff anywhere in your repository. This is a supply-chain rug-pull.",
        'Pin the version, or pin a container digest:\n\n```json\n{ "args": ["-y", "@modelcontextprotocol/server-git@1.2.3"] }\n```\n\nSet `require_mcp_pinned = false` if you accept the risk.',
    ),
    "PROMPT_TOO_LARGE": (
        "Prompt exceeds the token budget",
        "The prompt's approximate token count is above `max_prompt_tokens`.",
        "Prompt size drives cost and latency, and an unnoticed prompt edit is a silent price rise. A budget turns that into a reviewable number instead of a surprise on the invoice.",
        "Trim the prompt, or raise the limit if the growth is intentional:\n\n```toml\n[policy]\nmax_prompt_tokens = 2000\n```\n\nThe default is `0`, which disables the check.",
    ),
    "PROMPT_NO_OWNER": (
        "Prompt has no owner",
        "No CODEOWNERS rule matches the prompt's file and `require_prompt_owner` is enabled.",
        "Prompts are behaviour. Behaviour with no owner is behaviour nobody is accountable for when it drifts. Requiring an owner means a prompt edit requests the right review automatically.",
        "Add a CODEOWNERS rule:\n\n```text\nprompts/        @platform-ai\nsrc/agent.py    @platform-ai\n```\n\nThen enable the check:\n\n```toml\n[policy]\nrequire_prompt_owner = true\n```",
    ),
    "PROMPT_ID_COLLISION": (
        "Two prompts share one id",
        "Two different prompt contents claim the same id.",
        "Prompt ids are the stable key in `surface.lock` and in every diff. If two prompts share an id, the lockfile silently tracks only one of them and drift in the other becomes invisible.",
        'Give one of them an explicit, unique id:\n\n```python\n# surfacelock: prompt id=agent.planner.system\nPLANNER = "..."\n```\n\nThe error message names both colliding locations.',
    ),
}

HEADER = """# {code}

> **{title}** — {severity}

## What it means

{what}

## Why it matters

{why}

## How to fix it

{how}

---

<sub>[← all findings](index.md)</sub>
"""

SEV = {
    "UNPINNED_MODEL": "error",
    "UNKNOWN_MODEL": "warning",
    "MODEL_DEPRECATED": "warning",
    "MODEL_RETIRING": "error",
    "MODEL_RETIRED": "error",
    "MODEL_DENIED": "error",
    "MODEL_NOT_ALLOWED": "error",
    "PROVIDER_NOT_ALLOWED": "error",
    "MCP_INSECURE": "error",
    "MCP_UNPINNED": "warning",
    "PROMPT_TOO_LARGE": "error",
    "PROMPT_NO_OWNER": "warning",
    "PROMPT_ID_COLLISION": "error",
}

DOCS.mkdir(parents=True, exist_ok=True)
for code, (title, what, why, how) in PAGES.items():
    (DOCS / f"{code}.md").write_text(
        HEADER.format(code=code, title=title, severity=SEV[code], what=what, why=why, how=how),
        encoding="utf-8",
    )

rows = "\n".join(f"| [`{c}`]({c}.md) | {SEV[c]} | {PAGES[c][0]} |" for c in PAGES)
(DOCS / "index.md").write_text(
    f"""# Findings reference

Every surfacelock finding has a stable code, a fixed severity, and a page
explaining what it means and how to fix it. The CLI prints the URL next to each
finding.

| Code | Severity | Meaning |
|---|---|---|
{rows}

## Suppressing a finding

Put an `allow` directive on the offending line, with a reason:

```python
model = "gpt-4o"  # surfacelock: allow UNPINNED_MODEL reason="vendor SDK requires it"
```

Suppressions appear in `check --verbose` and are counted in every PR summary, so
they stay visible rather than becoming silent.
""",
    encoding="utf-8",
)

print("wrote", len(PAGES) + 1, "docs pages to", DOCS)

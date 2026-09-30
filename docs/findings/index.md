# Findings reference

Every surfacelock finding has a stable code, a fixed severity, and a page
explaining what it means and how to fix it. The CLI prints the URL next to each
finding.

| Code | Severity | Meaning |
|---|---|---|
| [`UNPINNED_MODEL`](UNPINNED_MODEL.md) | error | Floating model alias |
| [`UNKNOWN_MODEL`](UNKNOWN_MODEL.md) | warning | Model not in the registry |
| [`MODEL_DEPRECATED`](MODEL_DEPRECATED.md) | warning | Model retiring soon (warning window) |
| [`MODEL_RETIRING`](MODEL_RETIRING.md) | error | Model retiring imminently |
| [`MODEL_RETIRED`](MODEL_RETIRED.md) | error | Model already retired |
| [`MODEL_DENIED`](MODEL_DENIED.md) | error | Model on the deny list |
| [`MODEL_NOT_ALLOWED`](MODEL_NOT_ALLOWED.md) | error | Model not on the allow list |
| [`PROVIDER_NOT_ALLOWED`](PROVIDER_NOT_ALLOWED.md) | error | Provider not on the allow list |
| [`MCP_INSECURE`](MCP_INSECURE.md) | error | Insecure MCP transport |
| [`MCP_UNPINNED`](MCP_UNPINNED.md) | warning | Unpinned MCP server package |
| [`PROMPT_TOO_LARGE`](PROMPT_TOO_LARGE.md) | error | Prompt exceeds the token budget |
| [`PROMPT_NO_OWNER`](PROMPT_NO_OWNER.md) | warning | Prompt has no owner |
| [`PROMPT_ID_COLLISION`](PROMPT_ID_COLLISION.md) | error | Two prompts share one id |

## Suppressing a finding

Put an `allow` directive on the offending line, with a reason:

```python
model = "gpt-4o"  # surfacelock: allow UNPINNED_MODEL reason="vendor SDK requires it"
```

Suppressions appear in `check --verbose` and are counted in every PR summary, so
they stay visible rather than becoming silent.

# JSON schemas

Machine-readable output is versioned. Schemas are published alongside the code
and are validated in CI.

| Schema | Command | Document |
|---|---|---|
| `scan.v1` | `surfacelock scan --json` | [`docs/schemas/scan.v1.json`](https://github.com/iggym/surfacelock/blob/main/docs/schemas/scan.v1.json) |
| `check.v1` | `surfacelock check --format json` | [`docs/schemas/check.v1.json`](https://github.com/iggym/surfacelock/blob/main/docs/schemas/check.v1.json) |

Both envelopes carry a `schema` field naming the version, so a consumer can
branch on it. A breaking change to either shape means a new version
(`scan.v2`), never a silent edit to `v1`.

## `scan.v1`

```json
{
  "schema": "scan.v1",
  "surfacelock_version": "0.1.0",
  "summary": {
    "models": 2, "prompts": 1, "tools": 1, "mcp_servers": 1,
    "files_scanned": 19, "files_skipped": 0, "duration_ms": 41
  },
  "models": [
    {
      "name": "gpt-4o",
      "file": "src/agent.py",
      "line": 36,
      "context": "model",
      "provider": "openai",
      "annotated": false
    }
  ],
  "prompts": [
    {
      "id": "agent.planner.system",
      "path": "src/agent.py",
      "line": 6,
      "sha256": "…",
      "chars": 412,
      "approx_tokens": 103,
      "source": "annotated"
    }
  ],
  "tools": [
    {
      "name": "issue_refund",
      "file": "src/tools.py",
      "line": 25,
      "sha256": "…",
      "description": "Issue a refund to the customer",
      "param_keys": ["amount", "order_id"],
      "source": "decorator"
    }
  ],
  "mcp_servers": [
    {
      "name": "crm",
      "path": ".cursor/mcp.json",
      "transport": "http",
      "url": "https://crm.internal.example/mcp",
      "command": "",
      "args": [],
      "env_keys": ["CRM_TOKEN"],
      "sha256": "…"
    }
  ]
}
```

`env_keys` holds **names only**. Environment variable values are never present
in any output.

## `check.v1`

```json
{
  "schema": "check.v1",
  "surfacelock_version": "0.1.0",
  "ok": false,
  "counts": {"models": 2, "prompts": 1, "tools": 1, "mcp_servers": 1},
  "drift": {
    "changed": true,
    "entries": [
      {
        "kind": "model",
        "action": "changed",
        "name": "gpt-4o",
        "detail": "gpt-4o-2024-05-13 → gpt-4o-2024-11-20"
      }
    ]
  },
  "findings": [
    {
      "code": "UNPINNED_MODEL",
      "message": "`gpt-4o` is a floating alias; pin it to a dated snapshot",
      "path": "src/agent.py",
      "line": 36,
      "severity": "error",
      "suppressed": false,
      "reason": null,
      "docs_url": "https://iggym.github.io/surfacelock/findings/UNPINNED_MODEL/"
    }
  ],
  "suppressed": 0
}
```

`kind` is one of `model`, `prompt`, `tool`, `mcp_server`; `action` is one of
`added`, `removed`, `changed`.

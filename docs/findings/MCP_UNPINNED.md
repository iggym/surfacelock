# MCP_UNPINNED

> **Unpinned MCP server package** — warning

## What it means

A `npx`/`uvx`/`bunx`/`pipx` server is launched without a version.

## Why it matters

`npx -y some-mcp-server` fetches whatever is latest at the moment your agent starts. The maintainer — or someone who compromises the package — can change what code your agent runs, with no diff anywhere in your repository. This is a supply-chain rug-pull.

## How to fix it

Pin the version, or pin a container digest:

```json
{ "args": ["-y", "@modelcontextprotocol/server-git@1.2.3"] }
```

Set `require_mcp_pinned = false` if you accept the risk.

---

<sub>[← all findings](index.md)</sub>

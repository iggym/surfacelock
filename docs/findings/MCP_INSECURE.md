# MCP_INSECURE

> **Insecure MCP transport** — error

## What it means

An MCP server is configured over plaintext `http://`.

## Why it matters

An MCP server is a capability grant. Over plaintext HTTP, anyone on the network path can read the tool calls and their arguments, and can modify the responses your agent then acts on. It is one man-in-the-middle away from arbitrary tool execution.

## How to fix it

Switch the endpoint to `https://`:

```json
{ "mcpServers": { "crm": { "url": "https://crm.internal.example/mcp" } } }
```

If the server only speaks plaintext, put it behind a TLS-terminating proxy on localhost rather than exposing it on the network.

---

<sub>[← all findings](index.md)</sub>

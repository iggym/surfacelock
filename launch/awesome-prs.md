# awesome-list pull requests

## awesome-llmops

**Entry** (alphabetical, under *Evaluation / Governance*, or wherever lockfiles
and supply-chain tooling live):

```markdown
- [surfacelock](https://github.com/iggym/surfacelock) — A lockfile for
  the AI surface of your codebase. Pins models, prompts, tool schemas and MCP
  servers, and fails CI when they change without review. Apache-2.0, Python.
```

**PR body:**

Adds surfacelock, a CI gate for the AI layer. It applies the dependency-lockfile
pattern to model identifiers, prompt contents, tool schemas and MCP server
configs: scan the repository, freeze the result into `surface.lock`, and fail
the build when the AI surface changes without the lockfile changing.

Distinct from prompt registries and eval tools — this is supply-chain
governance for the AI layer, not a runtime or evaluation product. No network
calls, no telemetry. It is static analysis: scanned files are parsed, never
executed.

```bash
pipx install surfacelock
surfacelock scan      # writes nothing
surfacelock init      # writes surface.lock
surfacelock check     # the CI gate
```

## awesome-mcp

**Entry:**

```markdown
- [surfacelock](https://github.com/iggym/surfacelock) — Inventories and
  pins MCP server configurations, flags plaintext `http://` transports, and
  warns when `npx`/`uvx` servers are launched without a version.
```

**PR body:**

Adds surfacelock to the tooling section. Relevant to MCP users specifically for
two checks:

- **`MCP_INSECURE`** — flags a server configured over plaintext `http://`. An
  MCP server is a capability grant, and over plaintext anyone on the network
  path can read the tool calls and rewrite the responses the agent acts on.
- **`MCP_UNPINNED`** — flags `npx -y some-mcp-server` with no version. That
  fetches whatever is latest at agent start, which is a supply-chain rug-pull
  vector with no diff anywhere in the repository.

It also records which env var and header *names* a server needs, and hashes
them into the lockfile so a new secret requirement is visible in review.
Values are never recorded.

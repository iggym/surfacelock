# Detection rules and annotations

## Models

A string is recorded as a model when a provider naming pattern matches **and**
one of these holds:

- the string is known to the registry, or
- the line contains a model-context keyword (`model`, `model_name`,
  `deployment_name`, `azure_deployment`, `engine`, …), or
- the literal is annotated with `surfacelock: model`.

Scanned languages: Python, TypeScript/JavaScript (including TSX, JSX, MJS, CJS),
Go, Rust, Java/Kotlin, C#, Ruby, YAML, JSON, TOML, `.env` and `.ini`.

Azure deployments are detected from `deployment_name=` / `azure_deployment=` and
recorded with `context = "deployment"` and `provider = "azure"`. The underlying
model is unknown unless you map it in `.surfacelock/models.json`.

## Prompts

Three sources, in priority order:

1. **Annotated** — a `surfacelock: prompt [id=<id>]` comment on the line before
   or the same line as a string assignment.
2. **Prompt files** — anything under `prompt/`, `prompts/`, `system_prompts/` or
   `instructions/`, plus `.prompt`, `.md`, `.txt`, `.jinja`, `.j2`, `.hbs`,
   `.mustache` and `.tmpl` files inside those directories.
3. **Inline heuristics** — a string assigned to a name matching
   `/(prompt|system|instruction|persona|template)/i` with at least 160
   characters, or any string of at least 400 characters containing a newline.

Python is parsed with `ast` (f-string literal parts included). TypeScript and
JavaScript use a tolerant tokenizer for template literals and quoted strings —
it does not need a full parser and must never crash on syntax it does not
understand.

Each prompt records `id`, `file`, `line`, the `sha256` of the exact string,
`chars`, an approximate token count, and its `source`. Ids must be unique; a
collision errors with both locations named.

## Tools

| Form | Example |
|---|---|
| OpenAI JSON | `{"type":"function","function":{...}}` |
| Anthropic / MCP | `{name, description, input_schema}` |
| Python decorators | `@tool`, `@mcp.tool()`, `@function_tool`, `@agent.tool` |
| Pydantic | models referenced in `tools=[...]` |
| LangChain | `StructuredTool.from_function` |
| Vercel AI SDK | `tool({ name, description, parameters })` |
| MCP TS SDK | `server.tool("name", schema, …)` |

The `sha256` is taken over canonical JSON with sorted keys, so reformatting a
schema without changing it is not drift.

## MCP servers

Parsed from `.cursor/mcp.json`, `.vscode/mcp.json`, `.claude/mcp.json`,
`.mcp.json`, `mcp.json`, `claude_desktop_config.json`, `.gemini/settings.json`,
`.codex/config.toml`, `.continue/config.yaml`, and any file matching
`*mcp*.{json,yaml,toml}` containing a `mcpServers` or `servers` map.

Environment variable **names** and header **names** are recorded. Values are
never recorded, anywhere, and are hashed out of the config digest.

## Annotations

Explicit annotations always win over heuristics.

```python
# surfacelock: model
DEPLOYMENT = "my-org-custom-deployment"
```

```python
# surfacelock: prompt id=agent.planner.system
PLANNER = """You are a planning agent..."""
```

```python
# Force detection of a non-prompt string
NOT_A_PROMPT = "..."   # surfacelock: ignore
```

### Suppressing a policy finding

```python
model = "gpt-4o"  # surfacelock: allow UNPINNED_MODEL reason="vendor SDK requires it"
```

A suppression needs a reason, appears in `check --verbose`, and is counted in
every PR summary — so it stays visible instead of becoming silent.

## What is deliberately *not* detected

- Model names in comments, documentation and prose.
- Version strings that merely resemble model names (`"1.5.0"`).
- URLs containing model-like path segments.
- Bare dictionary keys such as `"command"` or `"embed"`.
- Anything in a file above 2 MB, or a binary file.

The `tricky` fixture in the test suite encodes all of these, and CI requires it
to report 100% precision.

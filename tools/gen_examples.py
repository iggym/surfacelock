"""Generate examples/demo-app, launch assets and the logo (CI diffs the demo)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "examples" / "demo-app"

FILES: dict[str, str] = {}

FILES["README.md"] = """# demo-app

A tiny repository with a realistic AI surface, used to prove surfacelock's
output is stable. CI regenerates `surface.lock` and `explain.md` here and fails
if they differ from what is committed.

```bash
cd examples/demo-app
surfacelock scan                 # what is in here
surfacelock check                # must pass against the committed lock
surfacelock explain > /tmp/x.md  # compare with explain.md
```

The surface here is deliberately mixed: a pinned chat snapshot, a floating
embedding alias, an annotated system prompt, an inline prompt, a prompt file,
a decorated tool, an OpenAI-style JSON schema, and two MCP servers — one HTTP
with a pinned package, one stdio.

`surfacelock check` passes on this directory, which is what makes it useful as
a golden file: any change to detection or lockfile rendering shows up as a diff.
"""

FILES["pyproject.toml"] = """[project]
name = "demo-app"
version = "0.1.0"
description = "Example repository used by surfacelock's golden-file tests."
requires-python = ">=3.11"
dependencies = ["openai>=1.0", "anthropic>=0.30"]
"""

FILES["surfacelock.toml"] = """# Example policy. Every key here is a default except the allow list.
[scan]
ignore = ["build/**"]

[policy]
fail_on_unpinned = true
deprecation_warn_days = 90
deprecation_fail_days = 30
require_mcp_pinned = true
"""

FILES["CODEOWNERS"] = """*                 @demo-owners
prompts/          @platform-ai
src/support.py    @platform-ai
"""

FILES["src/support.py"] = '''"""A support agent with a realistic AI surface."""

from anthropic import Anthropic

client = Anthropic()

# surfacelock: prompt id=support.system
SYSTEM = """You are a support agent for an online store.

Rules:
  1. Always verify the order id before discussing an order.
  2. Never promise a refund you cannot issue; use the issue_refund tool.
  3. If the customer is upset, acknowledge the problem before troubleshooting.
  4. Escalate to a human when the customer asks twice for one.
"""

CHAT_MODEL = "claude-sonnet-4-20250514"
EMBED_MODEL = "text-embedding-3-small"

FALLBACK_TEMPLATE = (
    "The customer said: {message}. Summarise the complaint in one sentence, "
    "then list the two most likely causes and the next diagnostic step to take. "
    "Keep the whole reply under 80 words and never invent an order id."
)


def ask(message: str) -> str:
    response = client.messages.create(
        model=CHAT_MODEL,
        system=SYSTEM,
        messages=[{"role": "user", "content": FALLBACK_TEMPLATE.format(message=message)}],
    )
    return response.content[0].text
'''

FILES["src/tools.py"] = '''"""Tool schemas the support agent can call."""

from dataclasses import dataclass

from anthropic import beta_tool

REFUND_SCHEMA = {
    "type": "function",
    "function": {
        "name": "issue_refund",
        "description": "Issue a refund to the customer",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order to refund"},
                "amount": {"type": "number", "description": "Amount in USD"},
                "reason": {"type": "string", "enum": ["damaged", "late", "wrong_item"]},
            },
            "required": ["order_id", "amount"],
        },
    },
}


@dataclass
class LookupOrder:
    """Look up an order by its identifier."""

    order_id: str


@beta_tool
def lookup_order(order_id: str) -> dict:
    """Look up an order by its identifier."""
    return {"order_id": order_id, "status": "shipped"}
'''

FILES["prompts/triage.prompt"] = """You triage incoming support tickets.

Given a ticket, output a single line: the category, then a pipe, then a
priority from P0 to P3. Categories are billing, shipping, account, product.
Do not explain your reasoning. Do not add punctuation. If the ticket mentions
a security issue, use category=account and priority=P0 regardless of tone.
"""

FILES[".cursor/mcp.json"] = """{
  "mcpServers": {
    "crm": {
      "url": "https://crm.internal.example/mcp",
      "headers": { "Authorization": "Bearer ${CRM_TOKEN}" }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem@0.6.2", "./data"],
      "env": { "FS_ROOT": "/srv/data" }
    }
  }
}
"""

FILES["src/index.py"] = '''"""Embedding pipeline."""

from openai import OpenAI

client = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-small"


def embed(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
'''

# ---------------------------------------------------------------------------
# Launch assets (spec §11)
# ---------------------------------------------------------------------------
LAUNCH: dict[str, str] = {}

LAUNCH["README.md"] = """# Launch assets — v0.1.0

Everything needed to announce surfacelock, in one place.

| File | What it is |
|---|---|
| `blog-post.md` | The long-form post |
| `show-hn.md` | Show HN title, body and first-comment |
| `reddit.md` | r/LocalLLaMA and r/MLOps posts |
| `awesome-prs.md` | PR descriptions for awesome-llmops and awesome-mcp |
| `seeded-issues.md` | The 10 issues to open on day one |
| `hero-gif.md` | Storyboard for the terminal GIF |

## Launch checklist

- [ ] `pipx install surfacelock` verified on a clean VM
- [ ] TestPyPI dry run green, then PyPI
- [ ] `v0.1.0` tag pushed; GitHub release published from the changelog
- [ ] mkdocs site deployed to GitHub Pages; link check passes
- [ ] Demo app committed with `surface.lock` and `explain.md`; CI diffs them
- [ ] 10 seeded issues opened with labels
- [ ] Discussions enabled; topics set
- [ ] Cross-linked from sibling repositories
- [ ] Hero GIF recorded from the storyboard
- [ ] Blog post published; Show HN posted; subreddits posted
- [ ] awesome-llmops and awesome-mcp PRs opened
"""

LAUNCH[
    "blog-post.md"
] = """# Your codebase has a lockfile for everything except the part that changes the most

*Draft — v0.1.0*

---

We lock our dependencies. `package-lock.json`, `poetry.lock`, `Cargo.lock` —
every ecosystem eventually admits that "we resolved it once, and we would like
it to stay resolved" is a requirement, not a nicety.

Then there is the AI layer, which we pin with a string.

```python
model = "gpt-4o"
```

That is not a pin. It is a hope. The provider can point `gpt-4o` at a different
snapshot on a Tuesday, and nothing in your repository records that it happened.
Your tests still pass because your tests were written against the old
behaviour — or, more likely, against no behaviour at all. The first symptom is
a customer saying the assistant got worse.

## Four ways this bites

**Floating aliases.** `gpt-4o`, `claude-3-5-sonnet-latest`, `gemini-1.5-pro`.
Every one of these is a moving target. Behaviour changes with no diff in the PR.

**Prompt drift.** Prompts are strings, so they get edited like strings — in
unrelated PRs, by people reviewing for typos. A prompt is not a string. It is
the closest thing your product has to a specification, and it usually has no
owner, no tests, and no diff review.

**Schema creep.** An agent's tool schema is a permission grant. Widen one
parameter and the agent can do more than it could yesterday. MCP servers make
this worse: an `npx` server is unpinned code that runs inside your agent's
trust boundary.

**Silent retirement.** Providers retire models on 6–12 month cycles, announced
months ahead. Teams discover it from a 404 in production, because the calendar
is not in the repository.

## The fix is boring, which is why it will work

`surfacelock` scans a repository, finds the AI surface — models, prompts, tool
schemas, MCP servers — and writes a lockfile.

```toml
[[model]]
name = "gpt-4o"
provider = "openai"
resolved = "gpt-4o-2024-08-06"
floating = true

[[prompt]]
id = "support.system"
path = "src/support.py"
sha256 = "…"
approx_tokens = 128
```

Then CI runs `surfacelock check`, which fails when the AI surface changes
without the lockfile changing. The diff you review is a diff of the AI layer.

The design decisions worth calling out:

**Pins are kept, not followed.** On `check` and `update`, an existing pin stays
pinned even when the registry has moved. Re-pinning is `update --resolve`, an
explicit reviewed act. Without this a lockfile would silently track the
registry and guarantee nothing.

**Conservative beats clever.** A tool that cries wolf gets switched off, and a
switched-off gate protects nothing. Detection needs a registry hit, a context
keyword, or an annotation. A string that merely looks like a model name is not
enough. There is a fixture full of false-positive traps, and CI requires 100%
precision on it.

**No network calls, no telemetry.** Everything comes from a bundled registry
and your repository. Secrets are never recorded: MCP env var *names* only.

**Deterministic output.** Two scans of the same tree are byte-identical. This
is enforced by property tests, not by hope.

## What it costs

About a second on a small repository. Under five on ten thousand files.

```bash
pipx install surfacelock
cd your-repo
surfacelock scan      # see it, writes nothing
surfacelock init      # freeze it
surfacelock check     # gate it
```

Apache-2.0. No accounts, no service, no telemetry.

## What it is not

It is not a prompt registry, not an eval tool, not runtime enforcement. Those
are different problems with different shapes. This one is narrow on purpose:
make the AI surface visible and reviewable, the way we already do for
dependencies.

Because the part of your system that changes the most deserves the same
protection as the part that changes the least.
"""

LAUNCH["show-hn.md"] = """# Show HN

## Title

Show HN: surfacelock – a lockfile for your models, prompts, tools and MCP servers

## Body

I kept hitting the same class of bug: an AI feature regresses and the git
history is clean. The model alias resolved to a new snapshot, or someone tidied
a prompt in a typo-fix PR, or an MCP server's `npx` package changed under us.

We solved this for dependencies years ago — lockfile plus a CI check — so I
built the same thing for the AI surface.

`surfacelock scan` finds model identifiers, prompts, tool schemas and MCP
server configs. `surfacelock init` writes `surface.lock`. `surfacelock check`
fails CI when they drift, and `surfacelock explain` produces a PR comment with
token and cost deltas.

Two design choices I would especially like feedback on:

1. **Pins are kept, not followed.** `check` and `update` never re-resolve an
   existing pin against current registry data — only `update --resolve` does,
   deliberately. My reasoning is that a lockfile which follows the registry
   guarantees nothing, but I would like to hear counterarguments.

2. **Conservative detection.** A string is only a model if the registry knows
   it, or the line has a model-context keyword, or it is annotated. I would
   rather miss a dynamic model string than flood a repo with false positives,
   because a noisy gate gets switched off. There is a fixture of
   false-positive traps and CI requires 100% precision on it.

No network calls, no telemetry, no provider API introspection — the registry is
a bundled JSON file with source URLs per entry.

Apache-2.0, Python 3.11+. Happy to answer anything about the detection rules,
the registry data, or where this overlaps with what you already do.

## First comment (post immediately)

Registry accuracy is the thing most likely to be wrong, and it is the thing I
can least fix alone. If a model's retirement date or price is off, the entries
live in `src/surfacelock/registry/models.json` and each one carries a `sources`
URL — issues or PRs both welcome.

The bundled registry ships with 176 entries across ten providers. Prices are
list prices per 1M tokens as published; retirement dates are only recorded when
the provider has announced them, because a guessed date produces false
`MODEL_RETIRING` errors.
"""

LAUNCH["reddit.md"] = """# Reddit posts

## r/LocalLLaMA

**Title:** I built a lockfile for the AI layer of a repo (models, prompts, tools, MCP servers)

**Body:**

Local models have the same problem as hosted ones, and in some ways a worse
one: a GGUF gets requantised, a tag moves, an Ollama model is re-pulled and the
behaviour shifts. There is nothing in the repository that records what you were
actually running.

`surfacelock` scans for model references, prompts, tool schemas and MCP server
configs, writes a `surface.lock`, and fails CI when any of them change without
review. It works with any provider name — including local ones, if you add them
to `.surfacelock/models.json`, which is how you teach it about your own
gateway or a fine-tune.

It is a static analyser: no network calls, no telemetry, and it never imports
or executes anything it scans.

Apache-2.0, `pipx install surfacelock`. Feedback on the detection rules
especially welcome — precision matters more to me than recall here.

## r/MLOps

**Title:** Lockfiles for the AI surface: pinning models, prompts and MCP servers the way we pin dependencies

**Body:**

The recurring incident class on our team was "the AI feature changed and the
diff was empty". Four flavours:

1. Model aliases resolving to new snapshots.
2. Prompts edited in unrelated PRs.
3. Tool schemas and MCP configs widening an agent's permissions.
4. Provider retirements discovered from a production 404.

`surfacelock` treats all four as one problem and applies the dependency-lockfile
pattern: scan, freeze into `surface.lock`, gate in CI, review the diff.

Things I would particularly like MLOps feedback on:

- **Pin-keeping semantics.** `check`/`update` never re-resolve an existing pin
  against current registry data. Only `update --resolve` re-pins, explicitly.
- **Retirement windows.** Defaults are warn at 90 days, fail at 30. `check
  --today` lets a scheduled nightly run advance the window without any code
  change.
- **Registry data as a release artifact.** Registry-only changes bump a patch
  version, so a `check` failure can appear from a version bump alone. I think
  this is correct, but it is a sharp edge worth documenting loudly.

Apache-2.0, no telemetry, no network calls. `surfacelock scan --json` emits a
versioned schema if you want to feed an inventory system.
"""

LAUNCH["awesome-prs.md"] = """# awesome-list pull requests

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
"""

LAUNCH["seeded-issues.md"] = """# Seeded issues for v0.1.0

Open these with the labels shown. They signal the project is alive and that
specific kinds of contribution are welcome.

## Registry (6)

1. **Verify Azure OpenAI deployment naming across regions**
   `labels: registry, data, good first issue`
   Azure deployment names are customer-chosen, so the registry records the
   underlying model only when we can. Six azure entries need a second pair of
   eyes on their `resolved` values and sources.

2. **Audit Google Gemini retirement dates**
   `labels: registry, data`
   Google's model lifecycle page moved. Confirm the 20 google entries still
   match published dates and that every one has a current `sources` URL.

3. **Confirm Bedrock cross-region inference profile IDs**
   `labels: registry, data`
   The 16 bedrock entries use model IDs; cross-region profiles prefix them with
   a region group. Decide whether to record both forms.

4. **Mistral pricing includes cached-input?**
   `labels: registry, data, question`
   Some Mistral tiers publish a cached-input rate and some do not. Establish a
   rule for `price_cached_in` and apply it consistently.

5. **Add xAI Grok context windows**
   `labels: registry, data, good first issue`
   Several xAI entries are missing `context_window`.

6. **Define a policy for models with no announced retirement**
   `labels: registry, data, discussion`
   Should `retirement` be absent, or set to a conservative estimate? Current
   answer is absent. Confirm and document.

## New scanners (2)

7. **Go: prompt annotations and tool detection**
   `labels: scanner, enhancement`
   Detect `surfacelock: prompt` annotations on Go string assignments and
   `//go:generate`-style tool registration. Follow the pattern in
   `scanners/prompts.py` and add a fixture.

8. **Rust: prompt annotations and model literals**
   `labels: scanner, enhancement`
   Rust string literals and doc comments. The tolerant-tokenizer approach used
   for TS/JS is the model to follow.

## Docs (2)

9. **Document the `explain` output for a real PR**
   `labels: docs, good first issue`
   Add a screenshot or verbatim comment to `docs/ci.md` so reviewers know what
   they are about to install.

10. **Write the monorepo guide**
    `labels: docs`
    `docs/faq.md#monorepos` is a paragraph. It needs per-package lockfiles,
    CODEOWNERS interaction, and a shared-registry-override example.

## Labels to create

`bug` · `enhancement` · `docs` · `registry` · `data` · `scanner` ·
`false-positive` · `precision` · `good first issue` · `help wanted` ·
`discussion` · `question`

## Discussions to seed

- Announcements → "surfacelock v0.1.0"
- Ideas → "Should `check` ever auto-fix?"
- Q&A → "Post your false positives here"
- Show and tell → "What is in your `surface.lock`?"
"""

LAUNCH["hero-gif.md"] = """# Hero GIF storyboard

Target: 12–18 seconds, 1200×700, dark terminal, no audio. Loops cleanly.

## Frame 1 — the problem (0–3 s)

```
$ surfacelock scan
```

Output reveals a floating alias three weeks from retirement:

```
🧠 models
   claude-3-5-sonnet-latest   src/support.py:21   anthropic · floating
                              ⚠ retires 2026-10-20 (21 days)
```

## Frame 2 — freeze it (3–6 s)

```
$ surfacelock init
```

The alias is pinned in the lockfile; source is untouched.

```
wrote surface.lock · 3 models · 4 prompts · 2 tools · 2 mcp servers
```

## Frame 3 — the drift (6–11 s)

A prompt is edited and the model snapshot is bumped. Run `check`:

```
$ surfacelock check

  AI surface drift:
  ✏️  model   claude-3-5-sonnet-latest  claude-3-5-sonnet-20241022 → …
  ✏️  prompt  support.system            412 → 453 tokens (+41)

  ✖ MODEL_RETIRING  src/support.py:21
      `claude-3-5-sonnet-latest` retires on 2026-10-20 (21 days)
      https://iggym.github.io/surfacelock/findings/MODEL_RETIRING/

  1 errors · 0 warnings · 0 suppressed
  ✖ check failed
```

## Frame 4 — the review artifact (11–15 s)

```
$ surfacelock explain
```

Cut to the rendered GitHub comment: the change table, `+41 tokens/call`,
`+$0.0001/call`, and the suggested regression check.

```
<details><summary>Suggested regression check</summary>
modelbump diff --from claude-3-5-sonnet-20241022 --to … --suite golden/
</details>
```

## Frame 5 — resolution (15–17 s)

```
$ surfacelock update --resolve claude-3-5-sonnet-latest
```

Before/after printed. `check` passes. Cut to the logo.

## Production notes

- Use a real repository, not a mock — the realism is the point.
- Keep the prompt-token delta at `+41`: specific numbers read as evidence,
  round numbers read as marketing.
- No narration. If a caption is needed, use one line: *"The AI layer changed.
  The diff was empty. Now it is not."*
"""

LOGO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128"
     role="img" aria-label="surfacelock">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#7c3aed"/>
      <stop offset="55%" stop-color="#4f46e5"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
  </defs>
  <rect x="4" y="4" width="120" height="120" rx="26" fill="url(#g)"/>
  <g fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round">
    <path d="M46 60v-9a18 18 0 0 1 36 0v9" opacity="0.95"/>
  </g>
  <rect x="34" y="60" width="60" height="46" rx="10" fill="#ffffff" opacity="0.95"/>
  <circle cx="64" cy="80" r="6.5" fill="#4f46e5"/>
  <rect x="61" y="83" width="6" height="12" rx="3" fill="#4f46e5"/>
</svg>
"""


def main() -> None:
    for rel, content in FILES.items():
        path = DEMO / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for rel, content in LAUNCH.items():
        path = ROOT / "launch" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    assets = ROOT / "docs" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "logo.svg").write_text(LOGO, encoding="utf-8")
    print(f"wrote {len(FILES)} demo files, {len(LAUNCH)} launch files, 1 logo")


if __name__ == "__main__":
    main()

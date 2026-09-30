# Your codebase has a lockfile for everything except the part that changes the most

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

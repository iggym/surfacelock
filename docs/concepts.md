# Concepts

## The AI surface

The AI surface of a repository is everything that determines what your AI
features actually do at runtime, minus the code you already review:

- **Models** — every model identifier, including embedding and Azure deployment
  names.
- **Prompts** — system prompts, instructions, personas, templates.
- **Tools** — function and tool schemas your agent can call.
- **MCP servers** — the external capabilities an agent is granted.

These are the inputs that change behaviour. A one-word prompt edit can move a
metric more than a two-hundred-line refactor, and it arrives in a diff that
looks innocuous.

## Floating vs pinned

A **floating** identifier is one that can resolve to something different without
your code changing:

| Identifier | Floating? | Why |
|---|---|---|
| `gpt-4o` | ✅ yes | The provider decides what `gpt-4o` points at |
| `claude-3-5-sonnet-latest` | ✅ yes | `-latest` is a moving target by definition |
| `gpt-4o-2024-08-06` | ❌ no | A dated snapshot is a fixed artifact |
| `text-embedding-3-small` | ✅ yes | Same alias problem as chat models |

Floating is not inherently wrong — sometimes a vendor SDK forces it. It is
wrong when it is *unnoticed*. `surfacelock` makes every floating alias explicit
and pins it in the lockfile so a change of target becomes a diff.

## Why a lockfile

We already solved this problem once, for dependencies.

| | Dependencies | The AI surface |
|---|---|---|
| **Manifest** | `package.json`, `pyproject.toml` | your source |
| **Lockfile** | `package-lock.json`, `poetry.lock` | `surface.lock` |
| **CI gate** | "lockfile is out of date" | `surfacelock check` |
| **Review artifact** | the lockfile diff | the lockfile diff + `explain` |

The lockfile is the contract. It says: *this repository, as reviewed, runs
against these exact model snapshots, these exact prompt contents, these exact
tool schemas, and these exact MCP servers.* When that stops being true, CI
fails and a human decides whether the change is intentional.

## Pin-keeping semantics

This is the subtle part, and it is what separates a lockfile from a config file.

- **`init`** pins floating aliases to the registry's current resolution.
- **`check`** compares against the lockfile. It never consults "what is current"
  for pinned entries.
- **`update`** rewrites the lockfile but **keeps existing pins**, even when the
  registry has moved on. That is the entire point: the registry moving is not a
  reason for your build to change.
- **`update --resolve`** deliberately re-pins, and prints the before/after.

Without this, a lockfile would silently follow the registry and provide no
guarantee at all.

## Determinism

Two scans of the same tree produce byte-identical output, regardless of
filesystem order or timestamps. Nothing in the lockfile body is time-dependent —
`generated_at` lives in `[meta]` only, and `check` ignores it. This is enforced
by property tests, not by convention.

## Conservatism

The tool is deliberately biased toward missing a finding rather than inventing
one. A noisy gate gets switched off, and a gate that is switched off protects
nothing. Concretely, detection requires one of:

1. A registry hit — the string is a model the registry knows.
2. A context keyword on the line — `model=`, `deployment_name=`, and friends.
3. An explicit annotation — `# surfacelock: model`.

A bare string that merely *looks* like a model name is not enough.

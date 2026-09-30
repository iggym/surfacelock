# CLI reference

```text
surfacelock [path]
surfacelock scan    [path] [--json]
surfacelock init    [path] [--force]
surfacelock check   [path] [--format text|json|markdown] [--allow-drift] [--today YYYY-MM-DD]
surfacelock update  [path] [--resolve [MODEL]]
surfacelock explain [path] [--base FILE]
surfacelock registry [name] [--check] [--path PATH]
surfacelock pin     <alias> [--all] [--path PATH] [--yes]
surfacelock doctor  [path]
surfacelock findings
```

Global: `--version`, `-h`/`--help`.

## `surfacelock` (no arguments)

Dispatches on the presence of `surface.lock`:

- lockfile exists → runs `check`
- no lockfile → prints a `scan` summary and hints at `init`

`surfacelock <path>` behaves the same way for a given directory.

## `scan`

Show the AI surface. **Writes nothing.**

| Flag | Meaning |
|---|---|
| `--json` | Emit the versioned `scan.v1` envelope |

Exit code: `0`.

## `init`

Write `surface.lock`, then print policy findings.

| Flag | Meaning |
|---|---|
| `--force` | Overwrite an existing lockfile |

Exit code: `0`, or `1` if policy reports errors.

## `check`

Rescan, diff against `surface.lock`, and run policy. The CI gate.

| Flag | Meaning |
|---|---|
| `--format text\|json\|markdown` | Output format (default `text`) |
| `--allow-drift` | Report drift but do not fail on it; policy errors still fail |
| `--today YYYY-MM-DD` | Evaluate retirement windows as of this date |

Exit codes: `0` ok · `1` drift or policy error · `2` no lockfile.

## `update`

Rewrite `surface.lock`, keeping existing pins. Prints changes with token and
cost deltas.

| Flag | Meaning |
|---|---|
| `--resolve [MODEL]` | Re-pin a named model, or `all`, to current snapshots |

Exit code: `0`.

## `explain`

Render the Markdown PR summary: a change table, net token and cost deltas,
policy findings, and a suggested regression check when a model snapshot moved.
Safe to paste into a GitHub comment.

| Flag | Meaning |
|---|---|
| `--base FILE` | Diff against a specific lockfile instead of the working tree |

Exit code: `0`.

## `registry`

| Form | Meaning |
|---|---|
| `registry` | Print the retirement calendar, soonest first |
| `registry <name>` | Print one resolved entry as JSON |
| `registry --check` | Validate the registry against its schema |

Exit codes: `0`, or `1` when a lookup fails or validation reports a problem.

## `pin`

**Rewrites source.** Replaces a floating alias literal with its pinned
snapshot, in Python, TypeScript, JavaScript, YAML and JSON.

| Flag | Meaning |
|---|---|
| `--all` | Pin every floating alias found, not just one |
| `--path PATH` | Repository root (default `.`) |
| `--yes` | Skip the confirmation prompt |

Shows a unified diff and asks for confirmation before writing. Only the literal
is touched: quotes, indentation and trailing comments are preserved. Running it
twice changes nothing the second time.

Exit code: `0`.

## `doctor`

Environment diagnostics: version, registry date, whether a config file was
found, which ignore files are in effect, and the timing of the last scan.

Exit code: `0`.

## `findings`

List every finding code with its severity and documentation URL.

Exit code: `0`.

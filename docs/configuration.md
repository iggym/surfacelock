# Configuration

`surfacelock.toml` at the repository root. Every key has a default, so an empty
file — or no file at all — is valid.

```toml
[scan]
ignore = ["vendor/**", "**/generated/**"]
prompt_dirs = ["prompts", "src/prompts"]
min_inline_chars = 160

[policy]
fail_on_unpinned = true
fail_on_unknown_models = false
deprecation_warn_days = 90
deprecation_fail_days = 30
fail_on_retired = true
allow_models = []
deny_models = []
allow_providers = []
require_mcp_pinned = true
max_prompt_tokens = 0
require_prompt_owner = false
```

## `[scan]`

| Key | Default | Meaning |
|---|---|---|
| `ignore` | `[]` | Extra gitignore-style patterns to skip |
| `prompt_dirs` | `[]` | Extra directories treated as prompt sources |
| `min_inline_chars` | `160` | Minimum length for the inline prompt heuristic |

`.gitignore` and `.surfacelockignore` are always respected, in addition to a
built-in list that skips `.git/`, `node_modules/`, virtualenvs and build
output.

## `[policy]`

| Key | Default | Meaning |
|---|---|---|
| `fail_on_unpinned` | `true` | Error on floating aliases (`UNPINNED_MODEL`) |
| `fail_on_unknown_models` | `false` | Error on models missing from the registry |
| `deprecation_warn_days` | `90` | Warn this many days before retirement |
| `deprecation_fail_days` | `30` | Fail this many days before retirement |
| `fail_on_retired` | `true` | Fail on already-retired models |
| `allow_models` | `[]` | If non-empty, every model must match a glob here |
| `deny_models` | `[]` | Models matching any glob here always fail |
| `allow_providers` | `[]` | If non-empty, every provider must be listed |
| `require_mcp_pinned` | `true` | Forbid `http://`; warn on unversioned `npx`/`uvx`/`binx`/`pipx` |
| `max_prompt_tokens` | `0` | Fail prompts above this budget (`0` disables) |
| `require_prompt_owner` | `false` | Every prompt file must have a CODEOWNERS owner |

### Allow lists versus deny lists

`deny_models` is a blocklist: everything is permitted except what you name.
`allow_models` inverts the default: **nothing** is permitted except what you
name. The second is the right posture in regulated environments, which is why
it is opt-in rather than the default.

### Prompt owners

With `require_prompt_owner = true`, surfacelock reads `CODEOWNERS` and requires
a matching rule for every prompt file. Directory rules ending in `/` and the
catch-all `*` are both supported; the last matching rule wins, as in git.

## Per-repository model overrides

`.surfacelock/models.json` extends or overrides the bundled registry, using the
same schema. Entries here win.

```json
{
  "models": {
    "gpt-4o-prod": {
      "provider": "azure",
      "kind": "deployment",
      "resolved": "gpt-4o-2024-08-06",
      "sources": ["https://internal.example/azure-deployments"]
    }
  }
}
```

This is how you teach surfacelock about internal deployments and fine-tunes
without forking the registry.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | AI surface matches, policy passes |
| `1` | Drift, or a policy error |
| `2` | No `surface.lock` — run `surfacelock init` |

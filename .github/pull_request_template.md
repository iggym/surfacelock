## What this changes

<!-- One or two sentences. Link the issue if there is one. -->

## Why

<!-- The failure mode or user problem this addresses. -->

## Checklist

- [ ] `ruff format` / `ruff check` / `mypy` / `pytest` pass locally
- [ ] Added or updated a test for the behaviour change
- [ ] If a finding code was added: `docs/findings/<CODE>.md` exists
- [ ] If registry data changed: `_updated` bumped, `sources` URLs present,
      and a changelog line added under "Registry data"
- [ ] If a new detection rule: the `tricky` fixture still reports 100% precision
- [ ] Updated the changelog under `[Unreleased]`

## AI surface impact

<!-- Does this PR change a model, prompt, tool schema or MCP server in this
     repository itself? If so, `surfacelock check` output is below. -->

<details><summary>surfacelock explain</summary>

```text
paste output here
```

</details>

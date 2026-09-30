# Stability policy

## Versioning

`surfacelock` follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the major version is `0`, the minor version carries the compatibility
promise:

> **Within a 0.x minor version, patch releases are safe upgrades.**

So `0.1.0` → `0.1.7` may add registry data and fix bugs, but will not change
the CLI surface, the lockfile shape, the finding codes or the JSON schemas.
`0.1` → `0.2` may change any of those, with a changelog entry and a migration
note.

## What is stable

| Surface | Promise |
|---|---|
| `surface.lock` format | Stable within a minor; `check` reads older lockfiles |
| Finding codes | Never renamed. A code may be deprecated, never silently repurposed |
| Exit codes | `0` ok · `1` drift or policy error · `2` no lockfile |
| `scan.v1` / `check.v1` schemas | Frozen. A breaking change ships as `v2` |
| `scan`, `build_lock`, `check` | Stable within a minor |
| CLI flags | Additive within a minor |

## What is not stable

- Internal modules — `surfacelock.scanners.*`, `surfacelock.lockfile`,
  `surfacelock.policy` and friends. Import them if you like, but pin a version.
- Human-readable `text` output. Column widths and colours will change. Parse
  `--format json` instead.
- Approximate token counts. They are labelled approximate on purpose and will
  change if the estimator improves.
- Registry contents. Data changes ship as patch releases, by design.

## Finding codes

Codes are a public API because they appear in CI logs, dashboards and
suppression comments. Rules:

- A code is **never renamed**. `UNPINNED_MODEL` stays `UNPINNED_MODEL`.
- A code's meaning is **never silently repurposed**.
- A code may be **deprecated**: it stops being emitted, keeps its docs page, and
  the changelog says so.
- Adding a code is a minor change, not a patch.
- Every code has a `docs/findings/<CODE>.md` page, and CI fails if one is
  missing.

## Registry data releases

Registry-only pull requests bump a patch version. This means a patch release
can change whether `check` fails — if a retirement date moved into a window —
without any code changing.

That is intentional and it is the tool working. The lockfile protects you from
*silent snapshot movement*; it does not, and cannot, stop a provider from
retiring a model. Surfacing that is the point.

If you need total immutability for a period, pin the version:

```bash
pip install "surfacelock==0.1.3"
```

## Deprecation process

1. The changelog announces the deprecation and the replacement.
2. The old behaviour keeps working for at least one minor version.
3. The CLI warns when the deprecated path is used.
4. Removal happens at the next minor, documented in the changelog.

## Support

Only the latest 0.x minor receives fixes. Security fixes are prioritised and
backported at the maintainer's discretion; see [SECURITY.md](https://github.com/iggym/surfacelock/blob/main/SECURITY.md).

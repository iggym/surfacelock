# Governance

## Model

`surfacelock` is currently a **single-maintainer, benevolent-dictator** project.
The maintainer merges all changes and is the final arbiter of scope. This is
intentional for 0.x: the fastest way to a coherent v1.0 is a narrow, opinionated
review bar.

As the contributor base grows, this document will move to a small steering
group with published membership. Changes to governance itself are made by pull
request against this file.

## Decision making

| Decision | Process |
|---|---|
| Bug fixes, docs, tests | Maintainer merges on green CI |
| New detection rules | Issue first; maintainer approves the false-positive analysis |
| New registry entries | Pull request with a `sources` URL per entry |
| New finding codes | Requires a docs page and a `SEVERITY` entry — CI enforces both |
| New commands or flags | Requires a spec section; expect scope pushback |
| Breaking changes | Only at a 0.x minor, documented in the changelog |

## The conservative principle

The project's most important product decision is a bias toward **missing a
finding rather than emitting a false positive**. A noisy tool gets disabled, and
a disabled tool protects nothing. Proposals that trade precision for recall will
be declined unless they are gated behind an explicit annotation.

This is why:

- `fail_on_unknown_models` defaults to `false`.
- `max_prompt_tokens` defaults to `0` (off).
- Detection requires a registry hit, a context keyword, or an annotation.
- The `tricky` fixture exists and must stay at 100% precision.

## Registry data governance

`registry/models.json` is the project's most valuable and most perishable
asset. Rules:

- Every entry needs at least one `sources` URL pointing at provider
  documentation. CI rejects entries without one.
- Prices are list prices in USD per 1M tokens, as published by the provider.
- Retirement dates are only recorded when the provider has announced them.
- Data-only pull requests bump a patch release and add a changelog line.

## Release cadence

Releases are cut when a change is worth shipping, not on a calendar. Registry
data changes can ship as patch releases at any time.

## Becoming a maintainer

Sustained, high-quality contribution over several months — especially registry
data accuracy and false-positive reports — is the path. There is no formal
process yet; the maintainer will ask.

# MODEL_DENIED

> **Model on the deny list** — error

## What it means

The model matches an entry in `deny_models`.

## Why it matters

Organisations have legitimate reasons to forbid a model: an unresolved data-processing agreement, a compliance boundary, a known jailbreak surface, or a cost blowout. Encoding that in policy means it is enforced on every PR rather than remembered in a wiki.

## How to fix it

Replace the model with an approved one. If the ban no longer applies, remove the pattern from `deny_models` in `surfacelock.toml` — as a reviewed change, with a reason in the PR.

---

<sub>[← all findings](index.md)</sub>

# Seeded issues for v0.1.0

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

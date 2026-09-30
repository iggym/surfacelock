# demo-app

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

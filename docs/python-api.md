# Python API

```python
from surfacelock import scan, build_lock, check
```

These three functions are the supported surface. They are typed, shipped with
`py.typed`, and stable within a 0.x minor version. Everything else is internal.

## `scan`

```python
scan(path=".", *, config=None, registry=None) -> ScanResult
```

Walk a repository and collect findings. Writes nothing.

```python
from surfacelock import scan

result = scan(".")
for model in result.models:
    print(model.name, model.file, model.line, model.context)

print(len(result.prompts), "prompts")
print(result.files_scanned, "files in", result.duration_ms, "ms")
```

`ScanResult` carries `models`, `prompts`, `tools`, `mcp_servers`,
`files_scanned`, `files_skipped`, `duration_ms`, and an `is_empty()` helper.

## `build_lock`

```python
build_lock(path=".", *, registry=None, previous=None, resolve=None) -> Lockfile
```

Produce a lockfile. Pass `previous` to preserve existing pins — the same
semantics as `surfacelock update`. Pass `resolve={"all"}` or a set of model
names to deliberately re-pin.

```python
from surfacelock import build_lock, read_lock

previous = read_lock("surface.lock")
lock = build_lock(".", previous=previous)
print(lock.counts)
```

## `check`

```python
check(path=".", *, allow_drift=False, today=None) -> CheckResult
```

Rescan, diff against `surface.lock`, and run policy. Raises
`FileNotFoundError` when there is no lockfile — the CLI maps that to exit
code 2.

```python
from surfacelock import check

outcome = check(".", allow_drift=False)
if not outcome.ok:
    for finding in outcome.policy.errors:
        print(finding.code, finding.location, finding.message)
    raise SystemExit(outcome.exit_code)
```

`CheckResult` exposes `ok`, `drift`, `policy`, `lock`, `scan`, and an
`exit_code` property that matches the CLI.

## Error handling

```python
from surfacelock.scanners.prompts import PromptCollision
from surfacelock import scan

try:
    result = scan(".")
except PromptCollision as exc:
    print(f"two prompts share the id {exc.id!r}: {exc.first} and {exc.second}")
```

## Type checking

`surfacelock` ships `py.typed` and is `mypy --strict` clean. A consumer project
gets full inference with no stubs:

```python
from surfacelock import scan

result = scan(".")
names: list[str] = [m.name for m in result.models]
```

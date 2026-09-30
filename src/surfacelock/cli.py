"""``surfacelock`` command line interface.

The CLI is intentionally thin: it parses arguments, delegates to the library,
and formats output.  All logic lives in the modules it imports.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import date
from pathlib import Path

from . import __version__
from .explain import render_explain
from .lockfile import (
    LOCKFILE_NAME,
    Diff,
    DiffEntry,
    Lockfile,
    build_lock,
    diff_locks,
    read_lock,
    write_lock,
)
from .output import Color, emit_json, supports_color, table
from .pin import apply_pins, plan_pins, render_plan
from .policy import (
    FINDING_CODES,
    SEVERITY,
    Finding,
    PolicyResult,
    check_policy,
    load_config,
)
from .registry import Registry
from .scanners import ScanResult, scan

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_NO_LOCK = 2

_ICON = {"added": "➕", "removed": "➖", "changed": "✏️"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _registry(root: Path) -> Registry:
    return Registry.load(root)


def _scan_payload(r: ScanResult) -> dict[str, object]:
    """Serialise a ScanResult to the versioned scan.v1 JSON envelope."""
    return {
        "schema": "scan.v1",
        "surfacelock_version": __version__,
        "summary": {
            "models": len(r.models),
            "prompts": len(r.prompts),
            "tools": len(r.tools),
            "mcp_servers": len(r.mcp_servers),
            "files_scanned": r.files_scanned,
            "files_skipped": r.files_skipped,
            "duration_ms": r.duration_ms,
        },
        "models": [
            {
                "name": m.name,
                "file": m.file,
                "line": m.line,
                "context": m.context,
                "provider": m.provider,
                "annotated": m.annotated,
            }
            for m in r.models
        ],
        "prompts": [
            {
                "id": p.id,
                "path": p.path,
                "line": p.line,
                "sha256": p.sha256,
                "chars": p.chars,
                "approx_tokens": p.approx_tokens,
                "source": p.source,
            }
            for p in r.prompts
        ],
        "tools": [
            {
                "name": t.name,
                "file": t.file,
                "line": t.line,
                "sha256": t.sha256,
                "description": t.description,
                "param_keys": list(t.param_keys),
                "source": t.source,
            }
            for t in r.tools
        ],
        "mcp_servers": [
            {
                "name": s.name,
                "path": s.path,
                "transport": s.transport,
                "url": s.url,
                "command": s.command,
                "args": list(s.args),
                "env_keys": list(s.env_keys),
                "sha256": s.sha256,
            }
            for s in r.mcp_servers
        ],
    }


def _check_payload(
    drift: Diff,
    policy_result: PolicyResult,
    lock: Lockfile,
) -> dict[str, object]:
    return {
        "schema": "check.v1",
        "surfacelock_version": __version__,
        "ok": not policy_result.errors and not drift.changed,
        "counts": dict(lock.counts),
        "drift": {
            "changed": drift.changed,
            "entries": [
                {
                    "kind": e.kind,
                    "action": e.action,
                    "name": e.name,
                    "detail": e.detail,
                }
                for e in drift.entries
            ],
        },
        "findings": [f.to_json() for f in policy_result.findings],
        "suppressed": len(policy_result.suppressed),
    }


def _print_findings(findings: list[Finding], color: Color) -> None:
    if not findings:
        return
    for f in findings:
        if f.suppressed:
            icon = color("✓", "dim")
            suffix = color(f"(suppressed: {f.reason or 'no reason given'})", "dim")
        elif f.severity == "error":
            icon = color("✖", "red", "bold")
            suffix = ""
        else:
            icon = color("⚠", "yellow", "bold")
            suffix = ""
        loc = color(f.location, "cyan") if f.location else ""
        print(f"  {icon} {color(f.code, 'bold')} {loc}")
        print(f"      {f.message}")
        print(f"      {color(f.docs_url, 'blue', 'dim')}")
        if suffix:
            print(f"      {suffix}")
    print()


def _print_drift(entries: list[DiffEntry], color: Color) -> None:
    if not entries:
        return
    print(color("  AI surface drift:", "bold"))
    rows = []
    for e in entries:
        rows.append(
            [
                _ICON.get(e.action, "•"),
                e.kind,
                e.name,
                e.detail,
            ]
        )
    print(table(["", "kind", "item", "detail"], rows, color=color))
    print()


def _summary_line(result: ScanResult, color: Color) -> str:
    return (
        f"{color(str(len(result.models)), 'magenta', 'bold')} models · "
        f"{color(str(len(result.prompts)), 'blue', 'bold')} prompts · "
        f"{color(str(len(result.tools)), 'cyan', 'bold')} tools · "
        f"{color(str(len(result.mcp_servers)), 'green', 'bold')} mcp servers"
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_scan(args: argparse.Namespace) -> int:
    color = Color(supports_color())
    root = Path(args.path).resolve()
    policy, _ = load_config(root)
    result = scan(root, config=policy.scan, registry=_registry(root))

    if args.json:
        emit_json(_scan_payload(result))
        return EXIT_OK

    print()
    print(color("🔎 surfacelock scan", "bold", "magenta"))
    print(f"   {color(str(root), 'dim')}")
    print()
    print(f"   {_summary_line(result, color)}")
    print(f"   {color(f'{result.files_scanned} files in {result.duration_ms} ms', 'dim')}")
    print()

    if result.models:
        print(color("  Models", "bold", "magenta"))
        rows = [[m.name, f"{m.file}:{m.line}", m.context, m.provider or "?"] for m in result.models]
        print(table(["model", "location", "kind", "provider"], rows, color=color))
        print()
    if result.prompts:
        print(color("  Prompts", "bold", "blue"))
        rows = [
            [p.id, f"{p.path}:{p.line}", p.source, str(p.approx_tokens)] for p in result.prompts
        ]
        print(table(["id", "location", "source", "~tokens"], rows, color=color))
        print()
    if result.tools:
        print(color("  Tools", "bold", "cyan"))
        rows = [
            [t.name, f"{t.file}:{t.line}", t.source, ",".join(t.param_keys)] for t in result.tools
        ]
        print(table(["name", "location", "source", "params"], rows, color=color))
        print()
    if result.mcp_servers:
        print(color("  MCP servers", "bold", "green"))
        rows = [[s.name, s.path, s.transport, s.url or s.command] for s in result.mcp_servers]
        print(table(["name", "config", "transport", "target"], rows, color=color))
        print()

    if result.is_empty():
        print(color("   No AI surface found.", "yellow"))
        print()

    if not (root / LOCKFILE_NAME).is_file():
        print(
            color("   No surface.lock yet — run ", "dim")
            + color("surfacelock init", "bold")
            + color(" to create one.", "dim")
        )
        print()
    return EXIT_OK


def cmd_init(args: argparse.Namespace) -> int:
    color = Color(supports_color())
    root = Path(args.path).resolve()
    lock_path = root / LOCKFILE_NAME
    if lock_path.is_file() and not args.force:
        print(color(f"{LOCKFILE_NAME} already exists (use --force to overwrite).", "yellow"))
        return EXIT_FAIL

    policy, _ = load_config(root)
    registry = _registry(root)
    result = scan(root, config=policy.scan, registry=registry)
    lock = build_lock(result, registry, version=__version__)
    write_lock(lock_path, lock)

    print()
    print(color("🔒 surfacelock init", "bold", "magenta"))
    print(f"   wrote {color(str(lock_path), 'cyan')}")
    print(f"   {_summary_line(result, color)}")
    print()

    policy_result = check_policy(lock, registry, policy, root=root)
    if policy_result.findings:
        print(color("  Policy findings:", "bold"))
        print()
        _print_findings(policy_result.findings, color)
    return EXIT_FAIL if policy_result.errors else EXIT_OK


def cmd_check(args: argparse.Namespace) -> int:
    color = Color(supports_color())
    root = Path(args.path).resolve()
    lock_path = root / LOCKFILE_NAME
    if not lock_path.is_file():
        if args.format == "json":
            emit_json({"schema": "check.v1", "error": "no_lockfile", "path": str(lock_path)})
        else:
            print(color(f"No {LOCKFILE_NAME} found at {lock_path}.", "red", "bold"))
            print(color("Run `surfacelock init` first.", "dim"))
        return EXIT_NO_LOCK

    policy, _ = load_config(root)
    registry = _registry(root)
    previous = read_lock(lock_path)
    result = scan(root, config=policy.scan, registry=registry)
    fresh = build_lock(result, registry, version=__version__, previous=previous)
    drift = diff_locks(previous, fresh)
    today = date.fromisoformat(args.today) if args.today else None
    policy_result = check_policy(fresh, registry, policy, root=root, today=today)

    failed = bool(policy_result.errors) or (drift.changed and not args.allow_drift)

    if args.format == "json":
        payload = _check_payload(drift, policy_result, fresh)
        payload["ok"] = not failed
        emit_json(payload)
        return EXIT_FAIL if failed else EXIT_OK

    if args.format == "markdown":
        sys.stdout.write(
            render_explain(drift, fresh, policy_result, registry, version=__version__) + "\n"
        )
        return EXIT_FAIL if failed else EXIT_OK

    print()
    print(color("🔒 surfacelock check", "bold", "magenta"))
    print(f"   {color(str(root), 'dim')}")
    print()

    if drift.changed:
        _print_drift(drift.entries, color)
        if args.allow_drift:
            print(color("   drift allowed (--allow-drift)", "yellow"))
            print()
    else:
        print(color("   ✓ lockfile is up to date", "green"))
        print()

    if policy_result.findings:
        print(color("  Policy:", "bold"))
        print()
        _print_findings(policy_result.findings, color)

    errors = len(policy_result.errors)
    warnings = len(policy_result.warnings)
    suppressed = len(policy_result.suppressed)
    print(
        f"   {color(str(errors), 'red' if errors else 'green', 'bold')} errors · "
        f"{color(str(warnings), 'yellow' if warnings else 'green', 'bold')} warnings · "
        f"{color(str(suppressed), 'dim')} suppressed"
    )
    if failed:
        print(color("   ✖ check failed", "red", "bold"))
    else:
        print(color("   ✓ check passed", "green", "bold"))
    print()
    return EXIT_FAIL if failed else EXIT_OK


def cmd_update(args: argparse.Namespace) -> int:
    color = Color(supports_color())
    root = Path(args.path).resolve()
    lock_path = root / LOCKFILE_NAME
    policy, _ = load_config(root)
    registry = _registry(root)
    previous = read_lock(lock_path) if lock_path.is_file() else None

    resolve: set[str] = set()
    if args.resolve is not None:
        values = args.resolve if isinstance(args.resolve, list) else [args.resolve]
        resolve = {v for v in values if v} or {"all"}

    result = scan(root, config=policy.scan, registry=registry)
    fresh = build_lock(result, registry, version=__version__, previous=previous, resolve=resolve)
    drift = diff_locks(previous, fresh)
    write_lock(lock_path, fresh)

    print()
    print(color("🔒 surfacelock update", "bold", "magenta"))
    print(f"   wrote {color(str(lock_path), 'cyan')}")
    print(f"   {_summary_line(result, color)}")
    print()
    if drift.entries:
        _print_drift(drift.entries, color)
    else:
        print(color("   no changes", "dim"))
        print()
    return EXIT_OK


def cmd_explain(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    lock_path = root / LOCKFILE_NAME
    policy, _ = load_config(root)
    registry = _registry(root)

    base = Path(args.base) if args.base else lock_path
    if not base.is_file():
        print(f"No lockfile at {base}; run `surfacelock init` first.", file=sys.stderr)
        return EXIT_NO_LOCK

    previous = read_lock(base)
    result = scan(root, config=policy.scan, registry=registry)
    fresh = build_lock(result, registry, version=__version__, previous=previous)
    drift = diff_locks(previous, fresh)
    policy_result = check_policy(fresh, registry, policy, root=root)
    sys.stdout.write(
        render_explain(drift, fresh, policy_result, registry, version=__version__) + "\n"
    )
    return EXIT_OK


def cmd_registry(args: argparse.Namespace) -> int:
    color = Color(supports_color())
    root = Path(args.path).resolve()
    registry = _registry(root)

    if args.check:
        return _registry_check(color, registry)

    if args.name:
        info = registry.resolve(args.name)
        if info is None:
            print(color(f"unknown model: {args.name}", "red"))
            return EXIT_FAIL
        emit_json(info.to_json())
        return EXIT_OK

    print()
    print(color("📅 surfacelock retirement calendar", "bold", "magenta"))
    print(f"   registry updated {color(registry.updated, 'cyan')} · {len(registry)} entries")
    print()
    today = date.today()
    rows = []
    for info in registry.retirement_calendar():
        retires = info.retirement_date
        days = (retires - today).days if retires else 0
        status = (
            color("retired", "red")
            if days < 0
            else (color(f"{days}d", "yellow") if days < 90 else f"{days}d")
        )
        rows.append([info.name, info.provider, info.retirement or "", status])
    print(table(["model", "provider", "retirement", "in"], rows, color=color))
    print()
    return EXIT_OK


def _registry_check(color: Color, registry: Registry) -> int:
    """Validate the bundled registry against its schema and the source rule."""
    from importlib import resources

    errors: list[str] = []
    schema_ref = resources.files("surfacelock.registry").joinpath("schema.json")
    try:
        schema = json.loads(schema_ref.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover
        print(color(f"cannot read schema: {exc}", "red"))
        return EXIT_FAIL

    allowed_kinds = set(schema["$defs"]["entry"]["properties"]["kind"]["enum"])
    allowed_keys = set(schema["$defs"]["entry"]["properties"])
    for info in registry.entries():
        data = info.to_json()
        if info.kind not in allowed_kinds:
            errors.append(f"{info.name}: invalid kind {info.kind!r}")
        if not info.sources:
            errors.append(f"{info.name}: no sources")
        for key in data:
            if key not in allowed_keys:
                errors.append(f"{info.name}: unknown key {key!r}")

    print()
    print(color("🔍 surfacelock registry --check", "bold", "magenta"))
    print(f"   {len(registry)} entries · schema {color('registry.schema.json', 'dim')}")
    print()
    if errors:
        for err in errors:
            print(f"  {color('✖', 'red')} {err}")
        print()
        return EXIT_FAIL
    print(color("   ✓ registry is valid", "green", "bold"))
    print()
    return EXIT_OK


def cmd_pin(args: argparse.Namespace) -> int:
    color = Color(supports_color())
    root = Path(args.path).resolve()
    registry = _registry(root)
    policy, _ = load_config(root)

    plan = plan_pins(
        root,
        model=None if args.all else args.alias,
        registry=registry,
        config=policy.scan,
    )
    if plan.empty:
        print(color("   nothing to pin — no floating aliases found", "green"))
        return EXIT_OK

    diff = render_plan(root, plan)
    print()
    print(color("📌 surfacelock pin", "bold", "magenta"))
    print(f"   {len(plan.edits)} replacement(s) across {len(plan.files())} file(s)")
    print()
    print(diff)

    if args.yes:
        apply = True
    else:
        try:
            answer = input("Apply these changes? [y/N] ").strip().lower()
        except EOFError:
            answer = "n"
        apply = answer in ("y", "yes")
    if apply:
        changed = apply_pins(root, plan)
        print(color(f"   ✓ rewrote {', '.join(changed)}", "green"))
    else:
        print(color("   aborted; nothing written", "yellow"))
    return EXIT_OK


def cmd_doctor(args: argparse.Namespace) -> int:
    color = Color(supports_color())
    root = Path(args.path).resolve()
    policy, config_path = load_config(root)
    registry = _registry(root)

    print()
    print(color("🩺 surfacelock doctor", "bold", "magenta"))
    print()
    rows = [
        ["surfacelock", __version__],
        ["python", platform.python_version()],
        ["platform", f"{platform.system()} {platform.release()}"],
        ["repo root", str(root)],
        ["registry", f"{len(registry)} entries, updated {registry.updated}"],
        ["config", str(config_path) if config_path else "(defaults)"],
        ["lockfile", "present" if (root / LOCKFILE_NAME).is_file() else "missing"],
    ]
    ignores = []
    for name in (".gitignore", ".surfacelockignore"):
        if (root / name).is_file():
            ignores.append(name)
    rows.append(["ignore files", ", ".join(ignores) or "(none)"])
    rows.append(["prompt dirs", ", ".join(policy.scan.prompt_dirs) or "(auto)"])
    rows.append(
        [
            "policy",
            f"unpinned={policy.fail_on_unpinned} "
            f"retired={policy.fail_on_retired} "
            f"mcp_pinned={policy.require_mcp_pinned}",
        ]
    )
    print(table(["key", "value"], rows, color=color))
    print()

    start = time.perf_counter()
    result = scan(root, config=policy.scan, registry=registry)
    elapsed = (time.perf_counter() - start) * 1000
    print(
        f"   last scan: {result.files_scanned} files in {elapsed:.0f} ms · "
        f"{_summary_line(result, color)}"
    )
    print()
    return EXIT_OK


def cmd_default(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if (root / LOCKFILE_NAME).is_file():
        args.format = "text"
        args.allow_drift = False
        args.today = None
        return cmd_check(args)
    return cmd_scan(args)


def cmd_findings(args: argparse.Namespace) -> int:
    color = Color(supports_color())
    print()
    print(color("surfacelock finding codes", "bold", "magenta"))
    print()
    rows = [
        [code, SEVERITY[code], f"https://iggym.github.io/surfacelock/findings/{code}.md"]
        for code in FINDING_CODES
    ]
    print(table(["code", "severity", "docs"], rows, color=color))
    print()
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="surfacelock",
        description="A lockfile for the AI surface of your codebase.",
    )
    parser.add_argument("--version", action="version", version=f"surfacelock {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="show findings without writing anything")
    p_scan.add_argument("path", nargs="?", default=".")
    p_scan.add_argument("--json", action="store_true", help="emit scan.v1 JSON")
    p_scan.set_defaults(func=cmd_scan)

    p_init = sub.add_parser("init", help="write surface.lock")
    p_init.add_argument("path", nargs="?", default=".")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing lockfile")
    p_init.set_defaults(func=cmd_init)

    p_check = sub.add_parser("check", help="diff against surface.lock and run policy")
    p_check.add_argument("path", nargs="?", default=".")
    p_check.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    p_check.add_argument("--allow-drift", action="store_true")
    p_check.add_argument("--today", default=None, help="evaluate dates as of YYYY-MM-DD")
    p_check.set_defaults(func=cmd_check)

    p_update = sub.add_parser("update", help="rewrite surface.lock")
    p_update.add_argument("path", nargs="?", default=".")
    p_update.add_argument(
        "--resolve",
        nargs="*",
        default=None,
        help="re-pin MODEL (or 'all') to the current registry resolution",
    )
    p_update.set_defaults(func=cmd_update)

    p_explain = sub.add_parser("explain", help="render the Markdown PR summary")
    p_explain.add_argument("path", nargs="?", default=".")
    p_explain.add_argument("--base", default=None, help="compare against another lockfile")
    p_explain.set_defaults(func=cmd_explain)

    p_reg = sub.add_parser("registry", help="retirement calendar, lookup, or validation")
    p_reg.add_argument("name", nargs="?", default=None)
    p_reg.add_argument("--check", action="store_true")
    p_reg.add_argument("--path", default=".")
    p_reg.set_defaults(func=cmd_registry)

    p_pin = sub.add_parser("pin", help="rewrite a floating alias to its pinned snapshot")
    p_pin.add_argument("alias", nargs="?", default=None)
    p_pin.add_argument("--all", action="store_true")
    p_pin.add_argument("--yes", action="store_true")
    p_pin.add_argument("--path", default=".")
    p_pin.set_defaults(func=cmd_pin)

    p_doc = sub.add_parser("doctor", help="environment diagnostics")
    p_doc.add_argument("path", nargs="?", default=".")
    p_doc.set_defaults(func=cmd_doctor)

    p_find = sub.add_parser("findings", help="list stable finding codes")
    p_find.set_defaults(func=cmd_findings)

    return parser


SUBCOMMANDS = frozenset(
    {"scan", "init", "check", "update", "explain", "registry", "pin", "doctor", "findings"}
)


def _default_args(path: str) -> argparse.Namespace:
    return argparse.Namespace(path=path, json=False, format="text", allow_drift=False, today=None)


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)

    # `surfacelock` and `surfacelock <path>` have no subcommand: they dispatch
    # to `check` when a lockfile exists and to `scan` otherwise.
    if not args_list or (not args_list[0].startswith("-") and args_list[0] not in SUBCOMMANDS):
        path = args_list[0] if args_list else "."
        return cmd_default(_default_args(path))

    parser = build_parser()
    args = parser.parse_args(args_list)
    return int(args.func(args))


def console_main() -> None:
    """Entry point for the ``surfacelock`` script."""
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:  # pragma: no cover
        raise SystemExit(130) from None


if __name__ == "__main__":  # pragma: no cover
    console_main()

"""Explain rendering, pin rewriting, and the public Python API."""

from __future__ import annotations

from pathlib import Path

import pytest

import surfacelock
from surfacelock import build_lock, check, scan
from surfacelock.explain import render_explain
from surfacelock.lockfile import LockPrompt, diff_locks
from surfacelock.pin import apply_pins, plan_pins, render_plan
from surfacelock.policy import PolicyResult, check_policy
from surfacelock.registry import Registry


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------
def test_explain_has_required_sections(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o"\n')
    registry = Registry.load()
    previous = build_lock(tmp_path, registry=registry)
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o-2024-11-20"\n')
    fresh = build_lock(tmp_path, registry=registry, previous=previous)
    diff = diff_locks(previous, fresh)
    policy_result = check_policy(fresh, registry, surfacelock.Policy(), root=tmp_path)
    out = render_explain(diff, fresh, policy_result, registry, version="0.1.0")
    assert out.startswith("### 🔒 surfacelock — AI surface changes")
    assert "| | kind | item | detail |" in out
    assert "**Net impact:**" in out
    assert "surfacelock 0.1.0" in out


def test_explain_suggests_modelbump_on_snapshot_change(tmp_path: Path) -> None:
    """A snapshot change on the *same* model entry suggests a modelbump run."""
    lock = surfacelock.Lockfile("0.1.0", "d", "h", {"models": 1})
    old = surfacelock.Lockfile(
        "0.1.0",
        "d",
        "h",
        {"models": 1},
        models=[
            surfacelock.LockModel(
                "gpt-4o", "openai", "chat", "gpt-4o-2024-05-13", True, True, ["a.py:1"]
            )
        ],
    )
    new = surfacelock.Lockfile(
        "0.1.0",
        "d",
        "h",
        {"models": 1},
        models=[
            surfacelock.LockModel(
                "gpt-4o", "openai", "chat", "gpt-4o-2024-11-20", True, True, ["a.py:1"]
            )
        ],
    )
    out = render_explain(
        diff_locks(old, new), lock, PolicyResult(), Registry.load(), version="0.1.0"
    )
    assert "modelbump diff --from gpt-4o-2024-05-13 --to gpt-4o-2024-11-20 --suite golden/" in out


def test_explain_prompt_token_delta_and_cost(tmp_path: Path) -> None:
    old = surfacelock.Lockfile(
        "0.1.0",
        "d",
        "h",
        {"models": 1, "prompts": 1},
        models=[
            surfacelock.LockModel("gpt-4o", "openai", "chat", "x", False, True, price_in_per_1m=2.5)
        ],
        prompts=[LockPrompt("p", "a.py", 1, "s1", 100, 100, "inline")],
    )
    new = surfacelock.Lockfile(
        "0.1.0",
        "d",
        "h",
        {"models": 1, "prompts": 1},
        models=[
            surfacelock.LockModel("gpt-4o", "openai", "chat", "x", False, True, price_in_per_1m=2.5)
        ],
        prompts=[LockPrompt("p", "a.py", 1, "s2", 141, 141, "inline")],
    )
    out = render_explain(
        diff_locks(old, new), new, PolicyResult(), Registry.load(), version="0.1.0"
    )
    assert "+41 tokens/call" in out
    assert "$" in out


def test_explain_no_changes(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o"\n')
    lock = build_lock(tmp_path, registry=Registry.load())
    out = render_explain(
        diff_locks(lock, lock), lock, PolicyResult(), Registry.load(), version="0.1.0"
    )
    assert "_No changes detected in the AI surface._" in out


def test_explain_uses_only_allowed_html() -> None:
    lock = surfacelock.Lockfile(
        "0.1.0",
        "d",
        "h",
        {"models": 1},
        models=[surfacelock.LockModel("m", "openai", "chat", "a", False, True)],
    )
    out = render_explain(
        diff_locks(None, lock), lock, PolicyResult(), Registry.load(), version="0.1.0"
    )
    for tag in ("<div", "<table", "<script", "<img"):
        assert tag not in out


# ---------------------------------------------------------------------------
# pin
# ---------------------------------------------------------------------------
def test_pin_plan_finds_floating_alias(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o"\n')
    plan = plan_pins(tmp_path, model="gpt-4o")
    assert len(plan.edits) == 1
    assert plan.edits[0].before == "gpt-4o"
    assert plan.edits[0].after == "gpt-4o-2024-08-06"


def test_pin_only_touches_the_literal(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.py",
        "# gpt-4o mentioned in a comment\nMODEL = 'gpt-4o'  # trailing comment\n",
    )
    apply_pins(tmp_path, plan_pins(tmp_path, model="gpt-4o"))
    text = (tmp_path / "a.py").read_text(encoding="utf-8")
    assert "# gpt-4o mentioned in a comment" in text
    assert "MODEL = 'gpt-4o-2024-08-06'" in text
    assert "# trailing comment" in text


def test_pin_preserves_quote_style(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "MODEL = \"gpt-4o\"\nOTHER = 'gpt-4o'\n")
    apply_pins(tmp_path, plan_pins(tmp_path, model="gpt-4o"))
    text = (tmp_path / "a.py").read_text(encoding="utf-8")
    assert '"gpt-4o-2024-08-06"' in text
    assert "'gpt-4o-2024-08-06'" in text


def test_pin_is_idempotent(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o"\n')
    apply_pins(tmp_path, plan_pins(tmp_path, model="gpt-4o"))
    after_first = (tmp_path / "a.py").read_text(encoding="utf-8")
    second_plan = plan_pins(tmp_path, model="gpt-4o")
    assert second_plan.empty, "pinned literals must not be re-pinned"
    apply_pins(tmp_path, second_plan)
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == after_first


def test_pin_all_covers_every_alias(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'A = "gpt-4o"\nB = "gpt-4o-mini"\n')
    plan = plan_pins(tmp_path)
    assert {e.before for e in plan.edits} == {"gpt-4o", "gpt-4o-mini"}


def test_pin_render_plan_is_a_unified_diff(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o"\n')
    diff = render_plan(tmp_path, plan_pins(tmp_path, model="gpt-4o"))
    assert "--- a/a.py" in diff
    assert "+++ b/a.py" in diff
    assert '-MODEL = "gpt-4o"' in diff
    assert '+MODEL = "gpt-4o-2024-08-06"' in diff


def test_pin_does_not_rewrite_pinned_literal(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    assert plan_pins(tmp_path).empty


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def test_public_api_is_exported() -> None:
    assert surfacelock.__version__ == "0.1.0"
    for name in ("scan", "build_lock", "check"):
        assert callable(getattr(surfacelock, name))


def test_api_scan_returns_scan_result(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o"\n')
    result = scan(tmp_path)
    assert isinstance(result, surfacelock.ScanResult)
    assert [m.name for m in result.models] == ["gpt-4o"]


def test_api_build_lock_roundtrip(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o"\n')
    lock = build_lock(tmp_path)
    assert isinstance(lock, surfacelock.Lockfile)
    assert lock.counts["models"] == 1


def test_api_check_raises_without_lockfile(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o"\n')
    with pytest.raises(FileNotFoundError):
        check(tmp_path)


def test_api_check_exit_code(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    from surfacelock.cli import main

    main(["init", str(tmp_path)])
    outcome = check(tmp_path)
    assert outcome.ok is True
    assert outcome.exit_code == 0


def test_api_check_detects_drift(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    from surfacelock.cli import main

    main(["init", str(tmp_path)])
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o-2024-11-20"\n')
    outcome = check(tmp_path)
    assert outcome.ok is False
    assert outcome.exit_code == 1
    assert outcome.drift.changed


def test_api_check_allow_drift(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    from surfacelock.cli import main

    main(["init", str(tmp_path)])
    _write(tmp_path, "a.py", 'MODEL = "gpt-4o-2024-11-20"\n')
    assert check(tmp_path, allow_drift=True).ok is True


def test_py_typed_marker_ships() -> None:
    from importlib import resources

    assert resources.files("surfacelock").joinpath("py.typed").is_file()


def test_registry_json_schema_is_valid_json() -> None:
    import json
    from importlib import resources

    payload = json.loads(
        resources.files("surfacelock.registry").joinpath("schema.json").read_text()
    )
    assert payload["title"] == "surfacelock model registry"


def test_policy_is_reexported() -> None:
    assert surfacelock.Policy().fail_on_unpinned is True

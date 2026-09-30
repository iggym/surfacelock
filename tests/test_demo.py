"""Golden-file tests: the committed demo app must reproduce exactly.

CI diffs these artifacts. A failure here means detection, ordering or lockfile
rendering changed — which is exactly what should require a review.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from surfacelock.cli import main
from surfacelock.explain import render_explain
from surfacelock.lockfile import build_lock, diff_locks, read_lock, write_lock
from surfacelock.policy import check_policy, load_config
from surfacelock.registry import Registry
from surfacelock.scanners import scan

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo-app"


def test_demo_app_is_present() -> None:
    assert (DEMO / "surface.lock").is_file()
    assert (DEMO / "explain.md").is_file()


def test_demo_lockfile_is_reproducible(tmp_path: Path) -> None:
    """Rebuilding the lock from the committed demo must match byte for byte."""
    committed = (DEMO / "surface.lock").read_text(encoding="utf-8")
    previous = read_lock(DEMO / "surface.lock")
    policy, _ = load_config(DEMO)
    fresh = build_lock(
        scan(DEMO, config=policy.scan, registry=Registry.load(DEMO)),
        Registry.load(DEMO),
        version="0.1.0",
        previous=previous,
    )
    out = tmp_path / "surface.lock"
    write_lock(out, fresh)
    assert out.read_text(encoding="utf-8") == committed


def test_demo_lockfile_has_no_timestamp_in_body() -> None:
    text = (DEMO / "surface.lock").read_text(encoding="utf-8")
    assert "generated_at" not in text


def test_demo_check_passes() -> None:
    assert main(["check", str(DEMO)]) == 0


def test_demo_explain_matches_committed() -> None:
    registry = Registry.load(DEMO)
    lock = read_lock(DEMO / "surface.lock")
    policy, _ = load_config(DEMO)
    fresh = build_lock(
        scan(DEMO, config=policy.scan, registry=registry),
        registry,
        version="0.1.0",
        previous=lock,
    )
    result = check_policy(fresh, registry, policy, root=DEMO)
    rendered = render_explain(diff_locks(lock, fresh), fresh, result, registry, version="0.1.0")
    committed = (DEMO / "explain.md").read_text(encoding="utf-8")
    assert rendered.strip() == committed.strip()


def test_demo_scan_json_is_stable() -> None:
    """Two scans of the demo produce identical JSON."""
    from surfacelock.cli import _scan_payload

    first = json.dumps(_scan_payload(scan(DEMO)), sort_keys=True)
    second = json.dumps(_scan_payload(scan(DEMO)), sort_keys=True)
    assert first == second


def test_demo_covers_every_finding_type() -> None:
    result = scan(DEMO)
    assert result.models, "demo should exercise model detection"
    assert result.prompts, "demo should exercise prompt detection"
    assert result.tools, "demo should exercise tool detection"
    assert result.mcp_servers, "demo should exercise MCP detection"


def test_demo_prompt_sources_are_all_represented() -> None:
    sources = {p.source for p in scan(DEMO).prompts}
    assert sources == {"annotated", "inline", "file"}


def test_demo_mcp_secrets_are_not_in_the_lockfile() -> None:
    """The demo's CRM token placeholder must never reach committed output."""
    text = (DEMO / "surface.lock").read_text(encoding="utf-8")
    assert "CRM_TOKEN" not in text  # header name is hashed, not emitted
    assert "Bearer" not in text
    assert "${CRM_TOKEN}" not in text


@pytest.mark.parametrize("fmt", ["text", "json", "markdown"])
def test_demo_check_renders_in_every_format(fmt: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", str(DEMO), "--format", fmt]) == 0
    assert capsys.readouterr().out

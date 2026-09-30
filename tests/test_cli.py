"""CLI behaviour: exit codes, formats, commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from surfacelock.cli import main


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o"\n')
    return tmp_path


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "surfacelock 0.1.0" in capsys.readouterr().out


def test_scan_writes_nothing(repo: Path) -> None:
    assert main(["scan", str(repo)]) == 0
    assert not (repo / "surface.lock").exists()


def test_scan_json_schema(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["scan", str(repo), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "scan.v1"
    assert payload["summary"]["models"] == 1
    assert payload["models"][0]["name"] == "gpt-4o"


def test_scan_json_validates_against_schema(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["scan", str(repo), "--json"])
    payload = json.loads(capsys.readouterr().out)
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "docs" / "schemas" / "scan.v1.json").read_text()
    )
    _assert_schema_shape(schema, payload, schema)


def test_check_without_lockfile_exits_2(repo: Path) -> None:
    assert main(["check", str(repo)]) == 2


def test_check_without_lockfile_json_exits_2(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["check", str(repo), "--format", "json"]) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "no_lockfile"


def test_init_then_check_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["init", str(repo)]) == 1  # unpinned gpt-4o is a policy error
    assert (repo / "surface.lock").is_file()
    capsys.readouterr()
    assert main(["check", str(repo), "--allow-drift"]) == 1


def test_init_pinned_model_check_passes(tmp_path: Path) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    assert main(["init", str(tmp_path)]) == 0
    assert main(["check", str(tmp_path)]) == 0


def test_init_refuses_to_overwrite(repo: Path) -> None:
    main(["init", str(repo)])
    assert main(["init", str(repo)]) == 1
    assert main(["init", str(repo), "--force"]) == 1


def test_check_detects_drift(tmp_path: Path) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    assert main(["init", str(tmp_path)]) == 0
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o-2024-11-20"\n')
    assert main(["check", str(tmp_path)]) == 1
    assert main(["check", str(tmp_path), "--allow-drift"]) == 0


def test_check_format_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    main(["init", str(tmp_path)])
    capsys.readouterr()
    assert main(["check", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "check.v1"
    assert payload["ok"] is True


def test_check_format_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o"\n')
    main(["init", str(tmp_path)])
    capsys.readouterr()
    main(["check", str(tmp_path), "--format", "markdown"])
    out = capsys.readouterr().out
    assert out.startswith("### 🔒 surfacelock — AI surface changes")


def test_check_today_flag_changes_outcome(tmp_path: Path) -> None:
    """A model retiring in the future fails only once today moves close enough."""
    _write(tmp_path, "src/agent.py", 'MODEL = "claude-3-5-sonnet-20241022"\n')
    main(["init", str(tmp_path)])
    assert main(["check", str(tmp_path), "--today", "2026-01-01"]) == 0
    assert main(["check", str(tmp_path), "--today", "2026-10-05"]) == 1


def test_update_preserves_pin(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o"\n')
    main(["init", str(tmp_path)])
    lock = (tmp_path / "surface.lock").read_text(encoding="utf-8")
    assert "gpt-4o-2024-08-06" in lock
    capsys.readouterr()
    assert main(["update", str(tmp_path)]) == 0
    assert "gpt-4o-2024-08-06" in (tmp_path / "surface.lock").read_text(encoding="utf-8")


def test_update_resolve_all_repins(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o"\n')
    main(["init", str(tmp_path)])
    text = (tmp_path / "surface.lock").read_text(encoding="utf-8")
    (tmp_path / "surface.lock").write_text(
        text.replace("gpt-4o-2024-08-06", "gpt-4o-2024-05-13"), encoding="utf-8"
    )
    capsys.readouterr()
    assert main(["update", str(tmp_path), "--resolve", "all"]) == 0
    assert "gpt-4o-2024-08-06" in (tmp_path / "surface.lock").read_text(encoding="utf-8")


def test_explain_renders_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    main(["init", str(tmp_path)])
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o-2024-11-20"\n')
    capsys.readouterr()
    assert main(["explain", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "surfacelock — AI surface changes" in out
    assert "gpt-4o-2024-11-20" in out


def test_registry_calendar(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["registry", "--path", str(tmp_path)]) == 0
    assert "retirement calendar" in capsys.readouterr().out


def test_registry_lookup_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["registry", "gpt-4o", "--path", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["provider"] == "openai"
    assert payload["resolved"] == "gpt-4o-2024-08-06"


def test_registry_lookup_unknown(tmp_path: Path) -> None:
    assert main(["registry", "nope-not-real", "--path", str(tmp_path)]) == 1


def test_registry_check_passes(tmp_path: Path) -> None:
    assert main(["registry", "--check", "--path", str(tmp_path)]) == 0


def test_doctor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "surfacelock doctor" in out
    assert "0.1.0" in out


def test_findings_lists_all_codes(capsys: pytest.CaptureFixture[str]) -> None:
    from surfacelock.policy import FINDING_CODES

    assert main(["findings"]) == 0
    out = capsys.readouterr().out
    for code in FINDING_CODES:
        assert code in out


def test_bare_invocation_scans_when_no_lock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o"\n')
    assert main([str(tmp_path)]) == 0
    assert "surfacelock scan" in capsys.readouterr().out


def test_bare_invocation_checks_when_lock_exists(tmp_path: Path) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o-2024-08-06"\n')
    main(["init", str(tmp_path)])
    assert main([str(tmp_path)]) == 0


def test_pin_requires_confirmation_without_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "src/agent.py", 'MODEL = "gpt-4o"\n')
    monkeypatch.setattr("builtins.input", lambda *_: "n")
    assert main(["pin", "gpt-4o", "--path", str(tmp_path)]) == 0
    assert '"gpt-4o"' in (tmp_path / "src" / "agent.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Minimal JSON Schema checker (draft subset) — avoids a jsonschema dependency.
# ---------------------------------------------------------------------------
def _assert_schema_shape(schema: dict, instance: object, root: dict) -> None:
    if "$ref" in schema:
        ref = schema["$ref"].lstrip("#/").split("/")
        node: object = root
        for part in ref:
            node = node[part]  # type: ignore[index]
        _assert_schema_shape(node, instance, root)  # type: ignore[arg-type]
        return

    if "type" in schema:
        expected = schema["type"]
        types = expected if isinstance(expected, list) else [expected]
        ok = any(
            (t == "object" and isinstance(instance, dict))
            or (t == "array" and isinstance(instance, list))
            or (t == "string" and isinstance(instance, str))
            or (t == "integer" and isinstance(instance, int) and not isinstance(instance, bool))
            or (
                t == "number"
                and isinstance(instance, (int, float))
                and not isinstance(instance, bool)
            )
            or (t == "boolean" and isinstance(instance, bool))
            or (t == "null" and instance is None)
            for t in types
        )
        assert ok, f"expected {expected}, got {type(instance).__name__}"

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            assert key in instance, f"missing required key {key!r}"
        for key, subschema in schema.get("properties", {}).items():
            if key in instance:
                _assert_schema_shape(subschema, instance[key], root)
    if isinstance(instance, list) and "items" in schema:
        for item in instance:
            _assert_schema_shape(schema["items"], item, root)

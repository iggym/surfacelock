"""Scanner: walker determinism, each finding type, false-positive precision."""

from __future__ import annotations

import json
from pathlib import Path

from surfacelock.scanners import ScanConfig, scan
from surfacelock.scanners.mcp import is_mcp_config
from surfacelock.scanners.prompts import is_prompt_file


def test_python_fixture_finds_models_and_prompts(python_openai: Path) -> None:
    result = scan(python_openai)
    names = {m.name for m in result.models}
    assert "gpt-4o" in names
    assert "text-embedding-3-small" in names
    assert any(p.id == "agent.support.system" for p in result.prompts)
    assert any(t.name == "issue_refund" for t in result.tools)


def test_embedding_context_classified(python_openai: Path) -> None:
    result = scan(python_openai)
    embedding = [m for m in result.models if m.name == "text-embedding-3-small"]
    assert embedding and embedding[0].context == "embedding"


def test_ts_fixture_finds_anthropic_model(fixtures_dir: Path) -> None:
    result = scan(fixtures_dir / "ts-anthropic")
    names = {m.name for m in result.models}
    assert "claude-3-5-sonnet-latest" in names
    assert any(t.name == "get_weather" for t in result.tools)


def test_no_ai_fixture_is_empty(no_ai: Path) -> None:
    result = scan(no_ai)
    assert result.is_empty(), (
        f"expected no findings, got {len(result.models)} models, {len(result.prompts)} prompts"
    )


def test_tricky_fixture_has_perfect_precision(tricky: Path) -> None:
    """Precision on the false-positive fixture must be 100%."""
    result = scan(tricky)
    assert result.models == [], [m.name for m in result.models]
    assert result.prompts == [], [p.id for p in result.prompts]


def test_mcp_fixture_parses_servers(fixtures_dir: Path) -> None:
    result = scan(fixtures_dir / "mcp-heavy")
    names = {s.name for s in result.mcp_servers}
    assert names == {"crm", "filesystem", "git-pinned", "insecure", "legacy"}


def test_mcp_secrets_never_recorded(fixtures_dir: Path) -> None:
    """No env or header *value* may appear anywhere in scanner output."""
    result = scan(fixtures_dir / "mcp-heavy")
    blob = json.dumps(
        [
            {
                "name": s.name,
                "url": s.url,
                "command": s.command,
                "args": list(s.args),
                "env_keys": list(s.env_keys),
                "sha256": s.sha256,
            }
            for s in result.mcp_servers
        ]
    )
    assert "sk-live-DO-NOT-RECORD-THIS-VALUE" not in blob
    assert "super-secret-token-value" not in blob
    assert "Bearer" not in blob
    # Key *names* are still recorded so users know what is required.
    assert "FS_TOKEN" in blob
    assert "Authorization" not in blob  # header keys are hashed, not emitted


def test_mcp_transport_inference(fixtures_dir: Path) -> None:
    result = scan(fixtures_dir / "mcp-heavy")
    by_name = {s.name: s for s in result.mcp_servers}
    assert by_name["crm"].transport == "http"
    assert by_name["legacy"].transport == "sse"
    assert by_name["filesystem"].transport == "stdio"


def test_mcp_pinned_detection(fixtures_dir: Path) -> None:
    result = scan(fixtures_dir / "mcp-heavy")
    by_name = {s.name: s for s in result.mcp_servers}
    assert by_name["git-pinned"].pinned is True
    assert by_name["filesystem"].pinned is False
    assert by_name["crm"].insecure is False
    assert by_name["legacy"].insecure is True


def test_prompt_file_detection(fixtures_dir: Path) -> None:
    result = scan(fixtures_dir / "prompt-files")
    assert any(p.source == "file" for p in result.prompts)
    assert is_prompt_file("prompts/rag_system.prompt")
    assert is_prompt_file("src/prompts/system.md")
    assert not is_prompt_file("docs/readme.md")


def test_mcp_config_path_detection() -> None:
    assert is_mcp_config(".cursor/mcp.json")
    assert is_mcp_config("claude_desktop_config.json")
    assert is_mcp_config("config/foo-mcp.json")
    assert not is_mcp_config("src/main.py")


def test_scan_is_deterministic(python_openai: Path) -> None:
    first = scan(python_openai)
    second = scan(python_openai)
    assert [m.name for m in first.models] == [m.name for m in second.models]
    assert [p.sha256 for p in first.prompts] == [p.sha256 for p in second.prompts]


def test_scan_output_is_identical_when_tree_order_changes(tmp_path: Path) -> None:
    """Shuffling files on disk must not change the result."""
    for name in ("b.py", "a.py", "c.py"):
        (tmp_path / name).write_text('model = "gpt-4o"\n', encoding="utf-8")
    first = scan(tmp_path)
    # Rewrite in a different order with different mtimes.
    for name in ("c.py", "a.py", "b.py"):
        (tmp_path / name).write_text('model = "gpt-4o"\n', encoding="utf-8")
    second = scan(tmp_path)
    assert [m.file for m in first.models] == [m.file for m in second.models]


def test_gitignore_is_respected(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "x.py").write_text('model = "gpt-4o"\n', encoding="utf-8")
    (tmp_path / "kept.py").write_text('model = "gpt-4o"\n', encoding="utf-8")
    result = scan(tmp_path)
    assert {m.file for m in result.models} == {"kept.py"}


def test_surfacelockignore_is_respected(tmp_path: Path) -> None:
    (tmp_path / ".surfacelockignore").write_text("skip_me.py\n", encoding="utf-8")
    (tmp_path / "skip_me.py").write_text('model = "gpt-4o"\n', encoding="utf-8")
    result = scan(tmp_path)
    assert result.models == []


def test_large_files_are_skipped(tmp_path: Path) -> None:
    big = tmp_path / "big.py"
    big.write_text('model = "gpt-4o"\n' + "x = 1\n" * 400_000, encoding="utf-8")
    result = scan(tmp_path)
    assert result.models == []
    assert result.files_skipped >= 1


def test_annotation_ignore_suppresses(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text('model = "gpt-4o"  # surfacelock: ignore\n', encoding="utf-8")
    assert scan(tmp_path).models == []


def test_annotation_model_forces_detection(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        '# surfacelock: model\nDEPLOYMENT = "my-custom-deployment"\n', encoding="utf-8"
    )
    result = scan(tmp_path)
    assert [m.name for m in result.models] == ["my-custom-deployment"]
    assert result.models[0].annotated is True


def test_azure_deployment_detection(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        'client.chat.completions.create(deployment_name="gpt-4o-prod")\n', encoding="utf-8"
    )
    result = scan(tmp_path)
    assert result.models
    assert result.models[0].context == "deployment"
    assert result.models[0].provider == "azure"


def test_prompt_id_collision_raises(tmp_path: Path) -> None:
    import pytest

    from surfacelock.scanners.prompts import PromptCollision

    (tmp_path / "a.py").write_text(
        "# surfacelock: prompt id=dup\nA = " + '"' + "x" * 200 + '"\n', encoding="utf-8"
    )
    (tmp_path / "b.py").write_text(
        "# surfacelock: prompt id=dup\nB = " + '"' + "y" * 200 + '"\n', encoding="utf-8"
    )
    with pytest.raises(PromptCollision):
        scan(tmp_path)


def test_scan_config_hash_is_stable() -> None:
    assert ScanConfig().config_hash() == ScanConfig().config_hash()
    assert ScanConfig(ignore=("x",)).config_hash() != ScanConfig().config_hash()

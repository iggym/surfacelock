"""Policy: one test per finding code, suppressions, CODEOWNERS owners."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from surfacelock.lockfile import (
    Lockfile,
    LockMcp,
    LockModel,
    LockPrompt,
)
from surfacelock.policy import FINDING_CODES, Policy, check_policy, load_config
from surfacelock.registry import Registry

TODAY = date(2026, 9, 30)


def _lock(**kw: object) -> Lockfile:
    base: dict[str, object] = {
        "surfacelock_version": "0.1.0",
        "registry_updated": "2026-09-30",
        "scan_config_hash": "h",
        "counts": {},
    }
    base.update(kw)
    return Lockfile(**base)  # type: ignore[arg-type]


def _codes(lock: Lockfile, policy: Policy, tmp_path: Path) -> list[str]:
    result = check_policy(lock, Registry.load(), policy, root=tmp_path, today=TODAY)
    return [f.code for f in result.findings]


def test_every_code_has_a_docs_page() -> None:
    docs = Path(__file__).resolve().parents[1] / "docs" / "findings"
    missing = [code for code in FINDING_CODES if not (docs / f"{code}.md").is_file()]
    assert not missing, f"missing finding docs pages: {missing}"


def test_finding_codes_are_unique() -> None:
    assert len(set(FINDING_CODES)) == len(FINDING_CODES)


def test_unpinned_model(tmp_path: Path) -> None:
    lock = _lock(
        models=[LockModel("gpt-4o", "openai", "chat", "gpt-4o-2024-08-06", True, True, ["a.py:1"])]
    )
    assert "UNPINNED_MODEL" in _codes(lock, Policy(), tmp_path)


def test_unpinned_disabled(tmp_path: Path) -> None:
    lock = _lock(models=[LockModel("gpt-4o", "openai", "chat", "x", True, True, ["a.py:1"])])
    assert "UNPINNED_MODEL" not in _codes(lock, Policy(fail_on_unpinned=False), tmp_path)


def test_unknown_model_only_when_enabled(tmp_path: Path) -> None:
    lock = _lock(
        models=[
            LockModel("acme-20250101", "acme", "chat", "acme-20250101", False, False, ["a.py:1"])
        ]
    )
    assert "UNKNOWN_MODEL" not in _codes(lock, Policy(), tmp_path)
    assert "UNKNOWN_MODEL" in _codes(lock, Policy(fail_on_unknown_models=True), tmp_path)


def test_model_retired(tmp_path: Path) -> None:
    lock = _lock(
        models=[
            LockModel(
                "gpt-4-0314",
                "openai",
                "chat",
                "gpt-4-0314",
                False,
                True,
                ["a.py:1"],
                retirement="2024-06-13",
            )
        ]
    )
    assert "MODEL_RETIRED" in _codes(lock, Policy(), tmp_path)


def test_model_retiring_within_fail_window(tmp_path: Path) -> None:
    lock = _lock(
        models=[
            LockModel("m", "openai", "chat", "m", False, True, ["a.py:1"], retirement="2026-10-20")
        ]
    )
    codes = _codes(lock, Policy(), tmp_path)
    assert "MODEL_RETIRING" in codes
    assert "MODEL_DEPRECATED" not in codes


def test_model_deprecated_within_warn_window(tmp_path: Path) -> None:
    lock = _lock(
        models=[
            LockModel("m", "openai", "chat", "m", False, True, ["a.py:1"], retirement="2026-12-15")
        ]
    )
    codes = _codes(lock, Policy(), tmp_path)
    assert "MODEL_DEPRECATED" in codes
    assert "MODEL_RETIRING" not in codes


def test_retired_check_can_be_disabled(tmp_path: Path) -> None:
    lock = _lock(
        models=[
            LockModel("m", "openai", "chat", "m", False, True, ["a.py:1"], retirement="2024-01-01")
        ]
    )
    assert "MODEL_RETIRED" not in _codes(lock, Policy(fail_on_retired=False), tmp_path)


def test_model_denied(tmp_path: Path) -> None:
    lock = _lock(models=[LockModel("gpt-4o", "openai", "chat", "x", False, True, ["a.py:1"])])
    assert "MODEL_DENIED" in _codes(lock, Policy(deny_models=("gpt-*",)), tmp_path)


def test_model_not_allowed(tmp_path: Path) -> None:
    lock = _lock(models=[LockModel("gpt-4o", "openai", "chat", "x", False, True, ["a.py:1"])])
    assert "MODEL_NOT_ALLOWED" in _codes(lock, Policy(allow_models=("claude-*",)), tmp_path)


def test_model_allowed_passes(tmp_path: Path) -> None:
    lock = _lock(models=[LockModel("gpt-4o", "openai", "chat", "x", False, True, ["a.py:1"])])
    assert "MODEL_NOT_ALLOWED" not in _codes(lock, Policy(allow_models=("gpt-*",)), tmp_path)


def test_provider_not_allowed(tmp_path: Path) -> None:
    lock = _lock(models=[LockModel("gpt-4o", "openai", "chat", "x", False, True, ["a.py:1"])])
    assert "PROVIDER_NOT_ALLOWED" in _codes(lock, Policy(allow_providers=("anthropic",)), tmp_path)


def test_mcp_insecure(tmp_path: Path) -> None:
    lock = _lock(
        mcp_servers=[LockMcp("crm", ".cursor/mcp.json", "http", url="http://crm.internal/mcp")]
    )
    assert "MCP_INSECURE" in _codes(lock, Policy(), tmp_path)


def test_mcp_unpinned(tmp_path: Path) -> None:
    lock = _lock(
        mcp_servers=[
            LockMcp(
                "fs",
                ".cursor/mcp.json",
                "stdio",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem"],
            )
        ]
    )
    assert "MCP_UNPINNED" in _codes(lock, Policy(), tmp_path)


def test_mcp_pinned_passes(tmp_path: Path) -> None:
    lock = _lock(
        mcp_servers=[
            LockMcp(
                "git", ".cursor/mcp.json", "stdio", command="npx", args=["-y", "server-git@1.2.3"]
            )
        ]
    )
    assert "MCP_UNPINNED" not in _codes(lock, Policy(), tmp_path)


def test_mcp_pinned_rule_can_be_disabled(tmp_path: Path) -> None:
    lock = _lock(mcp_servers=[LockMcp("fs", "m.json", "stdio", command="uvx", args=["x"])])
    assert "MCP_UNPINNED" not in _codes(lock, Policy(require_mcp_pinned=False), tmp_path)


def test_prompt_too_large(tmp_path: Path) -> None:
    lock = _lock(prompts=[LockPrompt("p", "a.py", 1, "s", 4000, 900, "inline")])
    assert "PROMPT_TOO_LARGE" in _codes(lock, Policy(max_prompt_tokens=500), tmp_path)


def test_prompt_too_large_off_by_default(tmp_path: Path) -> None:
    lock = _lock(prompts=[LockPrompt("p", "a.py", 1, "s", 4000, 900, "inline")])
    assert "PROMPT_TOO_LARGE" not in _codes(lock, Policy(), tmp_path)


def test_prompt_no_owner(tmp_path: Path) -> None:
    lock = _lock(prompts=[LockPrompt("p", "a.py", 1, "s", 10, 3, "inline")])
    assert "PROMPT_NO_OWNER" in _codes(lock, Policy(require_prompt_owner=True), tmp_path)


def test_prompt_with_owner_passes(tmp_path: Path) -> None:
    lock = _lock(prompts=[LockPrompt("p", "a.py", 1, "s", 10, 3, "inline", owners=["@ai"])])
    assert "PROMPT_NO_OWNER" not in _codes(lock, Policy(require_prompt_owner=True), tmp_path)


def test_prompt_id_collision_code_is_documented() -> None:
    """PROMPT_ID_COLLISION is raised by the scanner; the code is still public."""
    assert "PROMPT_ID_COLLISION" in FINDING_CODES


def test_suppression_on_offending_line(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        'model = "gpt-4o"  # surfacelock: allow UNPINNED_MODEL reason="vendor SDK"\n',
        encoding="utf-8",
    )
    lock = _lock(models=[LockModel("gpt-4o", "openai", "chat", "x", True, True, ["a.py:1"])])
    result = check_policy(lock, Registry.load(), Policy(), root=tmp_path, today=TODAY)
    assert result.ok
    assert len(result.suppressed) == 1
    assert result.suppressed[0].reason == "vendor SDK"


def test_suppression_does_not_cover_other_codes(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        'model = "gpt-4o"  # surfacelock: allow MODEL_DENIED reason="ok"\n',
        encoding="utf-8",
    )
    lock = _lock(models=[LockModel("gpt-4o", "openai", "chat", "x", True, True, ["a.py:1"])])
    result = check_policy(lock, Registry.load(), Policy(), root=tmp_path, today=TODAY)
    assert not result.ok
    assert [f.code for f in result.errors] == ["UNPINNED_MODEL"]


def test_load_config_defaults(tmp_path: Path) -> None:
    policy, path = load_config(tmp_path)
    assert path is None
    assert policy.fail_on_unpinned is True
    assert policy.deprecation_warn_days == 90
    assert policy.deprecation_fail_days == 30
    assert policy.max_prompt_tokens == 0


def test_load_config_from_toml(tmp_path: Path) -> None:
    (tmp_path / "surfacelock.toml").write_text(
        '[policy]\nfail_on_unpinned = false\ndeny_models = ["gpt-*"]\n'
        "[scan]\nmin_inline_chars = 500\n",
        encoding="utf-8",
    )
    policy, path = load_config(tmp_path)
    assert path is not None
    assert policy.fail_on_unpinned is False
    assert policy.deny_models == ("gpt-*",)
    assert policy.scan.min_inline_chars == 500


def test_codeowners_owners_resolution(tmp_path: Path) -> None:
    (tmp_path / "CODEOWNERS").write_text(
        "*       @default\nprompts/ @platform-ai\n", encoding="utf-8"
    )
    (tmp_path / "surfacelock.toml").write_text(
        "[policy]\nrequire_prompt_owner = true\n", encoding="utf-8"
    )
    policy, _ = load_config(tmp_path)
    assert policy.codeowners["prompts/"] == ("@platform-ai",)

    from surfacelock.policy import owners_for

    assert owners_for("prompts/system.prompt", policy.codeowners) == ("@platform-ai",)
    assert owners_for("src/main.py", policy.codeowners) == ("@default",)


def test_policy_result_ok_semantics(tmp_path: Path) -> None:
    lock = _lock(
        models=[
            LockModel("m", "openai", "chat", "m", False, True, ["a.py:1"], retirement="2026-12-15")
        ]
    )
    result = check_policy(lock, Registry.load(), Policy(), root=tmp_path, today=TODAY)
    assert result.ok  # deprecation is a warning
    assert len(result.warnings) == 1

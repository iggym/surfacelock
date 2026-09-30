"""Registry: schema conformance, alias resolution, floating detection."""

from __future__ import annotations

import json
from importlib import resources

import pytest

from surfacelock.registry import Registry


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry.load()


def test_registry_has_at_least_120_entries(registry: Registry) -> None:
    assert len(registry) >= 120


def test_every_entry_has_a_source(registry: Registry) -> None:
    for info in registry.entries():
        assert info.sources, f"{info.name} has no source URL"
        assert all(s.startswith("http") for s in info.sources)


def test_every_entry_validates_against_schema(registry: Registry) -> None:
    schema = json.loads(resources.files("surfacelock.registry").joinpath("schema.json").read_text())
    allowed_kinds = set(schema["$defs"]["entry"]["properties"]["kind"]["enum"])
    allowed_keys = set(schema["$defs"]["entry"]["properties"])
    for info in registry.entries():
        assert info.kind in allowed_kinds
        assert set(info.to_json()) <= allowed_keys


def test_updated_date_present(registry: Registry) -> None:
    assert registry.updated == "2026-09-30"


def test_required_providers_present(registry: Registry) -> None:
    providers = {info.provider for info in registry.entries()}
    for expected in (
        "openai",
        "anthropic",
        "google",
        "mistral",
        "meta",
        "deepseek",
        "cohere",
        "xai",
        "bedrock",
        "azure",
    ):
        assert expected in providers


def test_resolve_follows_alias_chain(registry: Registry) -> None:
    info = registry.resolve("gpt-4o")
    assert info is not None
    assert info.resolved == "gpt-4o-2024-08-06"


def test_resolve_unknown_returns_none(registry: Registry) -> None:
    assert registry.resolve("definitely-not-a-model") is None


def test_resolved_snapshot_of_dated_model_is_itself(registry: Registry) -> None:
    assert registry.resolved_snapshot("gpt-4o-2024-08-06") == "gpt-4o-2024-08-06"


def test_alias_chain_terminates_on_cycle() -> None:
    from surfacelock.registry import ModelInfo, Registry, _RegistryData

    data = _RegistryData(
        updated="2026-01-01",
        models={
            "a": ModelInfo(name="a", provider="x", kind="chat", alias_of="b"),
            "b": ModelInfo(name="b", provider="x", kind="chat", alias_of="a"),
        },
    )
    reg = Registry(data)
    assert reg.resolve("a") is not None  # must not hang


@pytest.mark.parametrize(
    "name,floating",
    [
        ("gpt-4o", True),
        ("claude-3-5-sonnet-latest", True),
        ("gpt-4o-2024-08-06", False),
        ("claude-sonnet-4-20250514", False),
    ],
)
def test_is_floating_registry_knowledge(registry: Registry, name: str, floating: bool) -> None:
    result, reason = registry.is_floating(name)
    assert result is floating
    assert reason


@pytest.mark.parametrize("name", ["some-model-latest", "acme-preview", "foo:latest"])
def test_is_floating_pattern_rules(registry: Registry, name: str) -> None:
    floating, reason = registry.is_floating(name)
    assert floating
    assert "ends with" in reason or "pattern" in reason


def test_is_floating_unknown_dated_name_is_pinned(registry: Registry) -> None:
    floating, _ = registry.is_floating("acme-internal-20250101")
    assert floating is False


def test_retirement_calendar_is_sorted(registry: Registry) -> None:
    calendar = registry.retirement_calendar()
    assert calendar
    dates = [m.retirement for m in calendar]
    assert dates == sorted(dates)


def test_per_repo_override_wins(tmp_path: object) -> None:
    from pathlib import Path

    root = Path(str(tmp_path))
    (root / ".surfacelock").mkdir()
    (root / ".surfacelock" / "models.json").write_text(
        json.dumps(
            {
                "_updated": "2026-09-30",
                "models": {
                    "gpt-4o": {
                        "provider": "openai",
                        "kind": "chat",
                        "resolved": "gpt-4o-2024-11-20",
                        "sources": ["https://example.com/override"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    reg = Registry.load(root)
    assert reg.resolved_snapshot("gpt-4o") == "gpt-4o-2024-11-20"

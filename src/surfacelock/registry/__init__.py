"""Model registry: bundled knowledge about models, aliases and retirements.

The registry is data-driven.  A bundled ``models.json`` ships with the tool and a
repository may extend or override it via ``.surfacelock/models.json``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

__all__ = ["ModelInfo", "Registry", "load_registry"]

# Aliases that are *by construction* floating, independent of registry data.
_FLOATING_SUFFIXES = ("-latest", "-preview", ":latest")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@dataclass(frozen=True)
class ModelInfo:
    """A single registry entry."""

    name: str
    provider: str
    kind: str
    resolved: str | None = None
    deprecation: str | None = None
    retirement: str | None = None
    price_in: float | None = None
    price_out: float | None = None
    price_cached_in: float | None = None
    context_window: int | None = None
    sources: tuple[str, ...] = ()
    notes: str | None = None
    alias_of: str | None = None

    @property
    def deprecation_date(self) -> date | None:
        return _parse_date(self.deprecation)

    @property
    def retirement_date(self) -> date | None:
        return _parse_date(self.retirement)

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {"provider": self.provider, "kind": self.kind}
        if self.resolved is not None:
            data["resolved"] = self.resolved
        for key in ("deprecation", "retirement", "notes", "alias_of"):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        for key in ("price_in", "price_out", "price_cached_in", "context_window"):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        if self.sources:
            data["sources"] = list(self.sources)
        return data

    @classmethod
    def from_json(cls, name: str, data: dict[str, Any]) -> ModelInfo:
        return cls(
            name=name,
            provider=str(data.get("provider", "unknown")),
            kind=str(data.get("kind", "chat")),
            resolved=data.get("resolved"),
            deprecation=data.get("deprecation"),
            retirement=data.get("retirement"),
            price_in=data.get("price_in"),
            price_out=data.get("price_out"),
            price_cached_in=data.get("price_cached_in"),
            context_window=data.get("context_window"),
            sources=tuple(data.get("sources", ())),
            notes=data.get("notes"),
            alias_of=data.get("alias_of"),
        )


@dataclass
class _RegistryData:
    updated: str = ""
    alias_patterns: list[str] = field(default_factory=list)
    models: dict[str, ModelInfo] = field(default_factory=dict)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


def _bundled_data() -> dict[str, Any]:
    ref = resources.files("surfacelock.registry").joinpath("models.json")
    return json.loads(ref.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _parse_payload(payload: dict[str, Any]) -> _RegistryData:
    data = _RegistryData(
        updated=str(payload.get("_updated", "")),
        alias_patterns=list(payload.get("alias_patterns", [])),
    )
    for name, entry in payload.get("models", {}).items():
        data.models[name] = ModelInfo.from_json(name, entry)
    return data


class Registry:
    """Resolves model aliases against bundled + per-repo registry data."""

    def __init__(self, data: _RegistryData) -> None:
        self._data = data

    # -- construction -------------------------------------------------
    @classmethod
    def load(cls, root: Path | None = None) -> Registry:
        bundled = _parse_payload(_bundled_data())
        if root is not None:
            override = root / ".surfacelock" / "models.json"
            if override.is_file():
                extra = _parse_payload(_read_json(override))
                bundled.models.update(extra.models)
                if extra.updated:
                    bundled.updated = extra.updated
                bundled.alias_patterns.extend(
                    p for p in extra.alias_patterns if p not in bundled.alias_patterns
                )
        return cls(bundled)

    # -- accessors ----------------------------------------------------
    @property
    def updated(self) -> str:
        return self._data.updated

    @property
    def alias_patterns(self) -> list[str]:
        return list(self._data.alias_patterns)

    def names(self) -> list[str]:
        return sorted(self._data.models)

    def entries(self) -> Iterable[ModelInfo]:
        return (self._data.models[name] for name in self.names())

    def get(self, name: str) -> ModelInfo | None:
        """Return the raw entry for *name* (no alias following)."""
        return self._data.models.get(name)

    def __contains__(self, name: object) -> bool:
        return name in self._data.models

    def __len__(self) -> int:
        return len(self._data.models)

    def resolve(self, name: str) -> ModelInfo | None:
        """Follow alias chains and return the terminal entry.

        Returns ``None`` when the name is unknown.  A cycle is treated as
        terminal so that malformed data can never hang a scan.
        """
        seen: set[str] = set()
        current = name
        while current not in seen:
            seen.add(current)
            info = self._data.models.get(current)
            if info is None:
                return None
            if not info.alias_of:
                return info
            nxt = self._data.models.get(info.alias_of)
            if nxt is None:
                return info
            current = info.alias_of
        return self._data.models.get(name)

    def resolved_snapshot(self, name: str) -> str | None:
        info = self.resolve(name)
        if info is None:
            return None
        return info.resolved or info.name

    def is_floating(self, name: str) -> tuple[bool, str]:
        """Return ``(floating, reason)`` for *name*.

        Registry knowledge wins over pattern rules: if an entry exists and it is
        an alias, the reason is "registry alias".  Otherwise we fall back to
        naming conventions that indicate an unpinned alias.
        """
        info = self._data.models.get(name)
        if info is not None:
            if info.alias_of:
                return True, f"registry alias for {info.alias_of}"
            if info.resolved and info.resolved != info.name:
                return True, "registry maps alias to a dated snapshot"
            if info.resolved is None:
                # Known model with no dated snapshot (e.g. a stable family name).
                return False, "known model without a dated snapshot"
            return False, "registry entry is already a dated snapshot"

        lowered = name.lower()
        for suffix in _FLOATING_SUFFIXES:
            if lowered.endswith(suffix):
                return True, f"name ends with {suffix!r}"
        for pattern in self._data.alias_patterns:
            if pattern.startswith("/") and pattern.endswith("/"):
                if re.search(pattern[1:-1], name):
                    return True, f"matches alias pattern {pattern}"
            elif pattern in name:
                return True, f"contains alias marker {pattern!r}"
        # A provider name with no dated suffix at all is presumed floating.
        if re.search(r"[a-z]", name) and not re.search(r"\d{4}", name):
            return True, "no dated snapshot suffix"
        return False, "appears to be a dated snapshot"

    def retirement_calendar(self) -> list[ModelInfo]:
        """Entries with a retirement date, soonest first."""
        dated = [m for m in self.entries() if m.retirement_date is not None]
        return sorted(dated, key=lambda m: m.retirement_date or date.max)

    def search(self, needle: str) -> list[ModelInfo]:
        needle = needle.lower()
        return [m for m in self.entries() if needle in m.name.lower()]


def load_registry(root: Path | None = None) -> Registry:
    """Convenience wrapper around :meth:`Registry.load`."""
    return Registry.load(root)

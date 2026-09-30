"""``surfacelock pin`` — rewrite a floating alias literal in place (F-PIN)."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from .registry import Registry
from .scanners import ScanConfig, scan

__all__ = ["PinEdit", "PinPlan", "apply_pins", "plan_pins", "render_plan"]

_REWRITABLE_SUFFIXES = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
)


@dataclass(frozen=True)
class PinEdit:
    """One literal replacement in one file."""

    path: str
    line: int
    before: str
    after: str
    quote: str

    def render_diff(self, root: Path) -> str:
        rel = self.path
        try:
            original = (
                (root / rel).read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            )
        except OSError:  # pragma: no cover
            return ""
        updated = list(original)
        idx = self.line - 1
        if 0 <= idx < len(updated):
            updated[idx] = _replace_on_line(updated[idx], self.before, self.after)
        return "".join(
            difflib.unified_diff(original, updated, fromfile=f"a/{rel}", tofile=f"b/{rel}")
        )


@dataclass
class PinPlan:
    """A set of edits plus the files they touch."""

    edits: list[PinEdit]

    @property
    def empty(self) -> bool:
        return not self.edits

    def files(self) -> list[str]:
        return sorted({e.path for e in self.edits})


def _replace_on_line(line: str, before: str, after: str) -> str:
    """Replace *before* with *after* only inside a quoted literal on *line*."""
    pattern = re.compile(r"(?P<q>[\"'`])" + re.escape(before) + r"(?P=q)")
    return pattern.sub(lambda m: f"{m.group('q')}{after}{m.group('q')}", line, count=1)


def plan_pins(
    root: Path,
    *,
    model: str | None = None,
    registry: Registry | None = None,
    config: ScanConfig | None = None,
) -> PinPlan:
    """Work out which literals to rewrite for *model* (or every floating alias)."""
    root = root.resolve()
    registry = registry or Registry.load(root)
    result = scan(root, config=config, registry=registry)

    edits: list[PinEdit] = []
    for finding in result.models:
        if model is not None and finding.name != model:
            continue
        # Only rewrite languages whose string literals we can edit safely.
        if not finding.file.endswith(_REWRITABLE_SUFFIXES):
            continue
        snapshot = registry.resolved_snapshot(finding.name)
        floating, _reason = registry.is_floating(finding.name)
        if not floating or snapshot is None or snapshot == finding.name:
            continue
        edits.append(
            PinEdit(
                path=finding.file,
                line=finding.line,
                before=finding.name,
                after=snapshot,
                quote='"',
            )
        )
    edits.sort(key=lambda e: (e.path, e.line))
    return PinPlan(edits=edits)


def apply_pins(root: Path, plan: PinPlan) -> list[str]:
    """Apply a plan, returning the files modified."""
    touched: dict[str, list[str]] = {}
    for edit in plan.edits:
        path = root / edit.path
        if edit.path not in touched:
            touched[edit.path] = path.read_text(encoding="utf-8", errors="replace").splitlines(
                keepends=True
            )
        lines = touched[edit.path]
        idx = edit.line - 1
        if 0 <= idx < len(lines):
            lines[idx] = _replace_on_line(lines[idx], edit.before, edit.after)
    for rel, lines in touched.items():
        (root / rel).write_text("".join(lines), encoding="utf-8")
    return sorted(touched)


def render_plan(root: Path, plan: PinPlan) -> str:
    """Render the unified diff for a plan."""
    chunks = [edit.render_diff(root) for edit in plan.edits]
    return "\n".join(c for c in chunks if c)

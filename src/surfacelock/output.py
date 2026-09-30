"""Terminal output helpers: colour, tables, JSON envelopes."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from typing import Any

__all__ = ["Color", "badge", "delta", "emit_json", "supports_color", "table"]

ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}


class Color:
    """Tiny ANSI helper that degrades to plain text when colour is off."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def __call__(self, text: str, *styles: str) -> str:
        if not self.enabled or not styles:
            return text
        prefix = "".join(ANSI.get(s, "") for s in styles)
        return f"{prefix}{text}{ANSI['reset']}"


def supports_color(stream: Any | None = None) -> bool:
    """True when the stream is a tty and ``NO_COLOR`` is unset."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    stream = stream or sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


def table(headers: Sequence[str], rows: Sequence[Sequence[str]], *, color: Color) -> str:
    """Render a simple aligned table."""
    if not rows:
        return color("  (none)", "dim")
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = [
        "  " + "  ".join(color(h.ljust(widths[i]), "bold") for i, h in enumerate(headers)),
        "  " + "  ".join(color("-" * widths[i], "dim") for i in range(len(headers))),
    ]
    for row in rows:
        lines.append("  " + "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)))
    return "\n".join(lines)


def badge(count: int, label: str, color: Color) -> str:
    """Colour a count green when zero and red otherwise."""
    style = "green" if count == 0 else "red"
    return color(f"{count} {label}", style, "bold")


def delta(before: int, after: int, color: Color) -> str:
    """Format a signed delta with colour."""
    diff = after - before
    if diff == 0:
        return color("±0", "dim")
    sign = "+" if diff > 0 else ""
    style = "red" if diff > 0 else "green"
    return color(f"{sign}{diff}", style)


def emit_json(payload: dict[str, Any]) -> None:
    """Write a stable, sorted JSON envelope to stdout."""
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")

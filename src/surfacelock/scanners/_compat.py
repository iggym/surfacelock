"""Legacy shim for ``fnmatch``-style ignore patterns used by older configs."""

from __future__ import annotations

import fnmatch

__all__ = ["matches_any"]


def matches_any(name: str, patterns: list[str]) -> bool:
    """True when *name* matches any shell-style pattern in *patterns*."""
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)

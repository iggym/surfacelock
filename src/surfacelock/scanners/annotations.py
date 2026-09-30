"""Shared annotation grammar.

Annotations are comments the user writes to override the scanner:

* ``surfacelock: model``            — treat the string on this/next line as a model.
* ``surfacelock: prompt [id=x]``    — treat the string as a prompt with a stable id.
* ``surfacelock: ignore``           — do not report anything from this line.
* ``surfacelock: allow CODE reason="…"`` — suppress one policy finding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Annotation", "find_annotation", "parse_allow_codes", "parse_annotation"]

_ANNOTATION_RE = re.compile(r"surfacelock:\s*(?P<body>[^\n]*)")
_ID_RE = re.compile(r"\bid\s*=\s*(?P<id>[A-Za-z0-9_.\-/]+)")
_REASON_RE = re.compile(r"""\breason\s*=\s*(?:"(?P<d>[^"]*)"|'(?P<s>[^']*)'|(?P<b>\S+))""")
_CODE_RE = re.compile(r"\b([A-Z][A-Z0-9_]{3,})\b")


@dataclass(frozen=True)
class Annotation:
    """A parsed ``surfacelock:`` directive."""

    kind: str  # "model" | "prompt" | "ignore" | "allow"
    id: str | None = None
    reason: str | None = None
    codes: tuple[str, ...] = ()
    raw: str = ""


def parse_annotation(text: str) -> Annotation | None:
    """Parse the first ``surfacelock:`` directive in *text*, if any."""
    match = _ANNOTATION_RE.search(text)
    if match is None:
        return None
    body = match.group("body").strip()
    lowered = body.lower()
    if lowered.startswith("ignore"):
        return Annotation(kind="ignore", raw=body)
    if lowered.startswith("allow"):
        reason = _REASON_RE.search(body)
        codes = tuple(c for c in _CODE_RE.findall(body) if c != "REASON")
        return Annotation(
            kind="allow",
            reason=(reason.group("d") or reason.group("s") or reason.group("b"))
            if reason
            else None,
            codes=codes,
            raw=body,
        )
    if lowered.startswith("prompt"):
        idm = _ID_RE.search(body)
        return Annotation(kind="prompt", id=idm.group("id") if idm else None, raw=body)
    if lowered.startswith("model"):
        return Annotation(kind="model", raw=body)
    return None


def parse_allow_codes(text: str) -> tuple[str, ...]:
    """Return the finding codes named by a ``surfacelock: allow`` directive."""
    ann = parse_annotation(text)
    if ann is None or ann.kind != "allow":
        return ()
    return ann.codes


def find_annotation(lines: list[str], index: int, *, look_back: int = 1) -> Annotation | None:
    """Find an annotation on *index* or up to *look_back* lines above it.

    ``allow`` directives must sit on the offending line itself; ``model``,
    ``prompt`` and ``ignore`` may be on the line above.
    """
    if 0 <= index < len(lines):
        ann = parse_annotation(lines[index])
        if ann is not None:
            return ann
    for offset in range(1, look_back + 1):
        j = index - offset
        if j < 0:
            break
        ann = parse_annotation(lines[j])
        if ann is not None:
            return ann
    return None

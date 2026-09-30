"""String-literal extraction shared by the model, prompt and tool scanners.

Every extractor yields :class:`StringLit` records so downstream scanners can
apply the same context filters regardless of language.  Extractors are
deliberately tolerant: they must never raise on syntax they do not understand.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

__all__ = [
    "StringLit",
    "extract_strings",
    "is_comment_line",
    "is_doc",
    "language_for",
    "python_context",
]


@dataclass(frozen=True)
class StringLit:
    """A string literal found in a source file."""

    value: str
    line: int  # 1-based line of the literal's start
    end_line: int
    kind: str  # "py" | "ts" | "generic"
    quote: str = '"'


_EXT_LANGUAGE: dict[str, str] = {
    ".py": "py",
    ".pyi": "py",
    ".ts": "ts",
    ".tsx": "ts",
    ".js": "ts",
    ".jsx": "ts",
    ".mjs": "ts",
    ".cjs": "ts",
    ".mts": "ts",
    ".cts": "ts",
    ".go": "generic",
    ".rs": "generic",
    ".java": "generic",
    ".kt": "generic",
    ".kts": "generic",
    ".cs": "generic",
    ".rb": "generic",
    ".yaml": "generic",
    ".yml": "generic",
    ".json": "generic",
    ".toml": "generic",
    ".env": "generic",
    ".ini": "generic",
    ".cfg": "generic",
    ".md": "generic",
    ".txt": "generic",
    ".prompt": "generic",
    ".jinja": "generic",
    ".j2": "generic",
    ".hbs": "generic",
    ".mustache": "generic",
    ".tmpl": "generic",
}

_SCANNABLE_EXT = frozenset(_EXT_LANGUAGE)

#: Documentation extensions.  Model names and inline prompt heuristics are
#: deliberately *not* applied to these — a README mentioning `gpt-4o` is prose,
#: not a dependency.  They still count as prompt files when under a prompt dir.
DOC_EXTENSIONS = frozenset({".md", ".txt"})


def is_doc(path_name: str) -> bool:
    """True when the file is documentation rather than executable surface."""
    name = path_name.lower()
    dot = name.rfind(".")
    return dot != -1 and name[dot:] in DOC_EXTENSIONS


def language_for(path_name: str) -> str | None:
    """Return the extractor key for a filename, or ``None`` if unsupported."""
    name = path_name.lower()
    dot = name.rfind(".")
    if dot == -1:
        return None
    return _EXT_LANGUAGE.get(name[dot:])


def is_comment_line(line: str) -> bool:
    """Cheap check for lines whose payload is a comment (used to skip matches)."""
    stripped = line.lstrip()
    return stripped.startswith(("#", "//", "/*", "*", "--", '"""', "'''"))


# ---------------------------------------------------------------------------
# Python — parse once, share the tree between every consumer.
# ---------------------------------------------------------------------------
def python_context(source: str) -> ast.Module | None:
    """Parse *source* as Python, returning ``None`` when it is not valid.

    Callers parse once and reuse the tree; parsing twice per file is the single
    biggest cost in a large-repo scan.
    """
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return None


def _strings_from_ast(tree: ast.Module, source: str) -> list[StringLit]:
    """Collect string constants from a parsed module.

    Comments never appear in an AST, so this is both faster and more accurate
    than scanning raw tokens.  f-string interpolations are skipped naturally
    because only the literal ``Constant`` parts are visited.
    """
    lines = source.splitlines()
    found: list[tuple[int, int, StringLit]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        lineno = node.lineno
        line_text = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
        col = node.col_offset
        quote = line_text[col : col + 1]
        if quote not in ('"', "'"):
            quote = '"'
        found.append(
            (
                lineno,
                col,
                StringLit(
                    value=node.value,
                    line=lineno,
                    end_line=node.end_lineno or lineno,
                    kind="py",
                    quote=quote,
                ),
            )
        )
    found.sort(key=lambda item: (item[0], item[1]))
    return [lit for _lineno, _col, lit in found]


def _extract_python(source: str, tree: ast.Module | None = None) -> list[StringLit]:
    if tree is None:
        tree = python_context(source)
    if tree is None:
        return _extract_generic(source)
    return _strings_from_ast(tree, source)


# ---------------------------------------------------------------------------
# TypeScript / JavaScript — tolerant scanner for quoted + template literals.
# ---------------------------------------------------------------------------
_TS_STRING_RE = re.compile(
    r"""
    (?P<back>`(?:[^`\\]|\\.)*`)          # template literal
  | (?P<dq>"(?:[^"\\\n]|\\.)*")          # double quoted
  | (?P<sq>'(?:[^'\\\n]|\\.)*')          # single quoted
    """,
    re.VERBOSE,
)


def _strip_ts_comments(source: str) -> str:
    """Blank out ``//`` and ``/* */`` comments, preserving line structure."""
    out: list[str] = []
    i = 0
    n = len(source)
    in_line = False
    in_block = False
    quote: str | None = None
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if in_line:
            if ch == "\n":
                in_line = False
                out.append(ch)
            else:
                out.append(" ")
            i += 1
            continue
        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                out.append("  ")
                i += 2
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
            continue
        if quote:
            out.append(ch)
            if ch == "\\" and nxt:
                out.append(nxt)
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line = True
            out.append("  ")
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block = True
            out.append("  ")
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _extract_ts(source: str) -> list[StringLit]:
    cleaned = _strip_ts_comments(source)
    out: list[StringLit] = []
    for match in _TS_STRING_RE.finditer(cleaned):
        raw = match.group(0)
        quote = raw[0]
        value = raw[1:-1]
        value = re.sub(r"\\(.)", r"\1", value)
        line = cleaned.count("\n", 0, match.start()) + 1
        end_line = line + value.count("\n")
        out.append(StringLit(value=value, line=line, end_line=end_line, kind="ts", quote=quote))
    return out


# ---------------------------------------------------------------------------
# Generic — quoted strings in YAML/JSON/TOML/Go/Rust/Java/… plus .env values.
# ---------------------------------------------------------------------------
_GENERIC_STRING_RE = re.compile(r"""(?P<q>["'])(?P<v>(?:[^"'\\\n]|\\.)*?)(?P=q)""")
_ENV_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<v>.+?)\s*$")


def _extract_generic(source: str) -> list[StringLit]:
    out: list[StringLit] = []
    seen: set[tuple[int, str]] = set()
    for line_no, line in enumerate(source.splitlines(), start=1):
        stripped = line.lstrip()
        for match in _GENERIC_STRING_RE.finditer(line):
            value = re.sub(r"\\(.)", r"\1", match.group("v"))
            key = (line_no, value)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                StringLit(value=value, line=line_no, end_line=line_no, kind="generic", quote='"')
            )
        if "=" in stripped and not stripped.startswith(("#", "//")):
            env = _ENV_RE.match(line)
            if env:
                value = env.group("v").strip().strip("\"'")
                key = (line_no, value)
                if value and key not in seen:
                    seen.add(key)
                    out.append(
                        StringLit(
                            value=value,
                            line=line_no,
                            end_line=line_no,
                            kind="generic",
                            quote="",
                        )
                    )
    return out


def extract_strings(source: str, language: str, tree: ast.Module | None = None) -> list[StringLit]:
    """Extract string literals from *source* using the extractor for *language*.

    Pass *tree* to reuse an already-parsed Python AST.
    """
    try:
        if language == "py":
            return _extract_python(source, tree)
        if language == "ts":
            return _extract_ts(source)
        return _extract_generic(source)
    except Exception:  # pragma: no cover - defensive: never crash a scan
        return []

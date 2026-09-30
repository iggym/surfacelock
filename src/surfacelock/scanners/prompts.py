"""Prompt detection (F-SCAN-2).

Three sources, in priority order:

``annotated``
    An explicit ``surfacelock: prompt [id=…]`` comment on the line itself or the
    line above a string assignment.
``file``
    A file that lives under a prompt directory or carries a prompt extension.
``inline``
    A heuristic: a string assigned to a prompt-ish name that is long enough, or
    any very long multi-line string.
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from .annotations import find_annotation
from .textutil import StringLit, extract_strings, is_doc, language_for, python_context

__all__ = ["PromptCollision", "PromptFinding", "find_prompts", "is_prompt_file"]

PROMPT_DIRS = frozenset({"prompt", "prompts", "system_prompts", "instructions"})
PROMPT_EXTENSIONS = frozenset({".prompt", ".jinja", ".j2", ".hbs", ".mustache", ".tmpl"})
PROMPT_TEXT_EXTENSIONS = frozenset({".md", ".txt"})
PROMPT_NAME_RE = re.compile(r"(prompt|system|instruction|persona|template)", re.IGNORECASE)

MIN_INLINE_CHARS = 160
LONG_STRING_CHARS = 400


@dataclass(frozen=True)
class PromptFinding:
    """A prompt discovered in the repository."""

    id: str
    path: str
    line: int
    sha256: str
    chars: int
    approx_tokens: int
    source: str  # annotated | file | inline
    owners: tuple[str, ...] = ()


class PromptCollision(Exception):
    """Raised when two different prompts claim the same id."""

    def __init__(self, prompt_id: str, first: str, second: str) -> None:
        super().__init__(
            f"prompt id {prompt_id!r} is used by both {first} and {second}; "
            f"give one of them an explicit id via `surfacelock: prompt id=...`"
        )
        self.prompt_id = prompt_id
        self.first = first
        self.second = second


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_prompt_file(rel_path: str) -> bool:
    """True when *rel_path* should be read wholesale as a prompt."""
    p = PurePosixPath(rel_path)
    if p.suffix.lower() in PROMPT_EXTENSIONS:
        return True
    # Markdown/text only counts inside a prompt directory.
    return any(part.lower() in PROMPT_DIRS for part in p.parts[:-1])


def _module_id(rel_path: str) -> str:
    p = PurePosixPath(rel_path)
    stem = str(p.with_suffix("")).replace("/", ".")
    return stem


# ---------------------------------------------------------------------------
# Assignment-name tracking
# ---------------------------------------------------------------------------
def _iter_statement_nodes(tree: ast.Module) -> list[ast.stmt]:
    """Statements at module level plus one nesting level inside blocks.

    Cheaper than ``ast.walk`` (which descends into every expression) and
    sufficient for finding string assignments, which are what prompts look like.
    """
    out: list[ast.stmt] = []
    stack: list[ast.stmt] = list(tree.body)
    blocks = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.If,
        ast.Try,
        ast.With,
        ast.AsyncWith,
        ast.For,
        ast.AsyncFor,
        ast.While,
    )
    while stack:
        node = stack.pop()
        out.append(node)
        if isinstance(node, blocks):
            stack.extend(node.body)
            stack.extend(getattr(node, "orelse", []))
            stack.extend(getattr(node, "finalbody", []))
            for handler in getattr(node, "handlers", []):
                stack.extend(handler.body)
    return out


def _python_assignments(source: str, tree: ast.Module | None = None) -> dict[int, str]:
    """Map string-literal line numbers to the name they are assigned to."""
    mapping: dict[int, str] = {}
    if "=" not in source:  # no assignment can exist
        return mapping
    if tree is None:
        tree = python_context(source)
    if tree is None:
        return mapping
    for node in _iter_statement_nodes(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not names:
                continue
            name = names[0]
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    mapping[sub.lineno] = name
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        mapping[sub.lineno] = node.target.id
    return mapping


_TS_ASSIGN_RE = re.compile(
    r"\b(?:const|let|var|export\s+const)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*"
    r"(?P<quote>[`\"'])",
)


def _ts_assignments(source: str) -> dict[int, str]:
    """Best-effort map of template/quoted literal start line -> variable name."""
    mapping: dict[int, str] = {}
    for match in _TS_ASSIGN_RE.finditer(source):
        line = source.count("\n", 0, match.start()) + 1
        mapping.setdefault(line, match.group("name"))
    return mapping


_GENERIC_ASSIGN_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z_][\w.]*)\s*[=:]\s*(?P<quote>[`\"'])",
)


def _generic_assignments(source: str) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for line_no, line in enumerate(source.splitlines(), start=1):
        m = _GENERIC_ASSIGN_RE.match(line)
        if m:
            mapping[line_no] = m.group("name").split(".")[-1]
    return mapping


def _assignments(source: str, language: str, tree: ast.Module | None = None) -> dict[int, str]:
    if language == "py":
        return _python_assignments(source, tree)
    if language == "ts":
        merged = _ts_assignments(source)
        for line, name in _generic_assignments(source).items():
            merged.setdefault(line, name)
        return merged
    return _generic_assignments(source)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def find_prompts(
    source: str,
    *,
    rel_path: str,
    approx_tokens_fn: object,
    min_inline_chars: int = MIN_INLINE_CHARS,
    prompt_dirs: tuple[str, ...] = (),
    tree: ast.Module | None = None,
    lits: list[StringLit] | None = None,
) -> list[PromptFinding]:
    """Return prompt findings for one file's contents.

    Pass *tree* to reuse an already-parsed Python AST, and *lits* to reuse
    string literals the caller already extracted — both avoid re-parsing.
    """
    lines = source.splitlines()
    findings: list[PromptFinding] = []
    seen_ids: dict[str, PromptFinding] = {}

    def emit(finding: PromptFinding) -> None:
        prior = seen_ids.get(finding.id)
        if prior is not None:
            # Two literals on the same line (e.g. a quoted string plus an
            # ``KEY=value`` form) describe one prompt, not a collision.
            if prior.path == finding.path and prior.line == finding.line:
                return
            if prior.sha256 != finding.sha256:
                raise PromptCollision(
                    finding.id,
                    f"{prior.path}:{prior.line}",
                    f"{finding.path}:{finding.line}",
                )
            return
        seen_ids[finding.id] = finding
        findings.append(finding)

    # (b) whole-file prompt sources.
    file_is_prompt = is_prompt_file(rel_path)
    if not file_is_prompt and prompt_dirs:
        parts = PurePosixPath(rel_path).parts[:-1]
        file_is_prompt = any(d.lower() in {p.lower() for p in parts} for d in prompt_dirs)
    if file_is_prompt and source.strip():
        emit(
            PromptFinding(
                id=_module_id(rel_path),
                path=rel_path,
                line=1,
                sha256=_sha256(source),
                chars=len(source),
                approx_tokens=int(approx_tokens_fn(source)),  # type: ignore[operator]
                source="file",
            )
        )

    language = language_for(rel_path)
    if language is None:
        return findings

    lits = extract_strings(source, language, tree) if lits is None else lits
    assigns = _assignments(source, language, tree)

    # Documentation is scanned only as a whole-file prompt source above.
    if is_doc(rel_path):
        return findings

    for lit in lits:
        if lit.line - 1 >= len(lines):
            continue
        ann = find_annotation(lines, lit.line - 1)
        if ann is not None and ann.kind == "ignore":
            continue
        value = lit.value

        annotated = ann is not None and ann.kind == "prompt"
        name = assigns.get(lit.line)

        if annotated:
            prompt_id = ann.id if ann and ann.id else f"{_module_id(rel_path)}.{name or 'prompt'}"
            emit(
                PromptFinding(
                    id=prompt_id,
                    path=rel_path,
                    line=lit.line,
                    sha256=_sha256(value),
                    chars=len(value),
                    approx_tokens=int(approx_tokens_fn(value)),  # type: ignore[operator]
                    source="annotated",
                )
            )
            continue

        if file_is_prompt:
            # Avoid double-reporting the same content already captured as a file.
            continue

        # (c) inline heuristics.
        is_named = name is not None and PROMPT_NAME_RE.search(name) is not None
        if (is_named and len(value) >= min_inline_chars) or (
            len(value) >= LONG_STRING_CHARS and "\n" in value
        ):
            prompt_id = (
                f"{_module_id(rel_path)}.{name}" if name else f"{_module_id(rel_path)}:{lit.line}"
            )
            emit(
                PromptFinding(
                    id=prompt_id,
                    path=rel_path,
                    line=lit.line,
                    sha256=_sha256(value),
                    chars=len(value),
                    approx_tokens=int(approx_tokens_fn(value)),  # type: ignore[operator]
                    source="inline",
                )
            )

    return findings

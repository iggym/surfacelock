"""Scan orchestrator: walk a repo, run every detector, return a ScanResult."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pathspec

from ..registry import Registry
from ..tokens import approx_tokens
from .mcp import McpFinding, find_mcp_servers, is_mcp_config
from .models import ModelFinding, find_models
from .prompts import PromptCollision, PromptFinding, find_prompts
from .textutil import extract_strings, is_doc, language_for, python_context
from .tools import ToolFinding, find_tools

__all__ = ["DEFAULT_IGNORES", "ScanConfig", "ScanResult", "scan"]

MAX_FILE_BYTES = 2 * 1024 * 1024

DEFAULT_IGNORES: tuple[str, ...] = (
    ".git/",
    ".hg/",
    ".svn/",
    "node_modules/",
    "__pycache__/",
    ".venv/",
    "venv/",
    ".env.d/",
    "dist/",
    "build/",
    "target/",
    ".tox/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".surfacelock/cache/",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    "*.dll",
    "*.exe",
    "*.bin",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.whl",
    "*.lock",
    "surface.lock",
    # surfacelock's own registry data is tool input, not project AI surface.
    "**/surfacelock/registry/models.json",
    "**/surfacelock/registry/schema.json",
)


@dataclass
class ScanConfig:
    """User-controlled scan behaviour (``[scan]`` in ``surfacelock.toml``)."""

    ignore: tuple[str, ...] = ()
    prompt_dirs: tuple[str, ...] = ()
    min_inline_chars: int = 160

    def config_hash(self) -> str:
        payload = {
            "ignore": sorted(self.ignore),
            "prompt_dirs": sorted(self.prompt_dirs),
            "min_inline_chars": self.min_inline_chars,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


@dataclass
class ScanResult:
    """Everything the scanner found, plus enough metadata to lock it."""

    root: Path
    models: list[ModelFinding] = field(default_factory=list)
    prompts: list[PromptFinding] = field(default_factory=list)
    tools: list[ToolFinding] = field(default_factory=list)
    mcp_servers: list[McpFinding] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    duration_ms: int = 0
    config_hash: str = ""

    def is_empty(self) -> bool:
        return not (self.models or self.prompts or self.tools or self.mcp_servers)


def _load_ignore_spec(root: Path, extra: Iterable[str]) -> pathspec.PathSpec[Any]:
    patterns: list[str] = list(DEFAULT_IGNORES)
    for name in (".gitignore", ".surfacelockignore"):
        path = root / name
        if path.is_file():
            with contextlib.suppress(OSError):  # pragma: no cover - unreadable file
                patterns.extend(path.read_text(encoding="utf-8", errors="replace").splitlines())
    patterns.extend(extra)
    return pathspec.PathSpec[Any].from_lines("gitignore", patterns)


def _looks_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def _walk(root: Path, spec: pathspec.PathSpec[Any]) -> list[tuple[str, Path]]:
    """Return ``(relpath, abspath)`` pairs in deterministic order."""
    out: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = "" if rel_dir == "." else rel_dir.replace(os.sep, "/")
        dirnames.sort()
        filenames.sort()
        # Prune ignored directories so we never descend into node_modules.
        dirnames[:] = [
            d for d in dirnames if not spec.match_file(f"{rel_dir}/{d}/" if rel_dir else f"{d}/")
        ]
        for filename in filenames:
            rel = f"{rel_dir}/{filename}" if rel_dir else filename
            if spec.match_file(rel):
                continue
            out.append((rel, Path(dirpath) / filename))
    return out


def _read_text(path: Path) -> str | None:
    try:
        # One open() rather than stat()+read_bytes(): this is the hot path.
        with path.open("rb") as fh:
            data = fh.read(MAX_FILE_BYTES + 1)
    except OSError:  # pragma: no cover - unreadable file
        return None
    if len(data) > MAX_FILE_BYTES:
        return None
    if _looks_binary(data):
        return None
    return data.decode("utf-8", errors="replace")


def _scan_one(
    rel: str,
    path: Path,
    registry: Registry,
    config: ScanConfig,
) -> tuple[list[ModelFinding], list[PromptFinding], list[ToolFinding], list[McpFinding], bool]:
    """Scan a single file; returns findings plus a "was read" flag."""
    is_mcp = is_mcp_config(rel)
    language = language_for(rel)
    if language is None and not is_mcp:
        return [], [], [], [], False

    source = _read_text(path)
    if source is None:
        return [], [], [], [], False

    lines = source.splitlines()
    # Parse Python once and share the tree with every consumer below.  A file
    # with no quote character cannot contain a string constant, so skip it.
    has_strings = '"' in source or "'" in source
    tree = python_context(source) if (language == "py" and has_strings) else None
    if language == "py" and not has_strings:
        return [], [], [], [], True

    # Extract string literals once; the prompt and model scanners both consume
    # them, and re-extracting would re-walk the AST for every file.
    lits = extract_strings(source, language, tree) if language is not None else []

    prompts = find_prompts(
        source,
        rel_path=rel,
        approx_tokens_fn=approx_tokens,
        min_inline_chars=config.min_inline_chars,
        prompt_dirs=config.prompt_dirs,
        tree=tree,
        lits=lits,
    )
    tools = find_tools(source, rel_path=rel, tree=tree)
    mcp = find_mcp_servers(source, rel_path=rel) if is_mcp else []

    models: list[ModelFinding] = []
    if language is not None and not is_doc(rel):
        for lit in lits:
            models.extend(find_models(lit, lines=lines, rel_path=rel, registry=registry))

    return models, prompts, tools, mcp, True


def scan(
    root: Path | str = ".", *, config: ScanConfig | None = None, registry: Registry | None = None
) -> ScanResult:
    """Scan *root* and return a :class:`ScanResult`.

    Deterministic: the same tree always produces byte-identical output, and file
    order on disk does not affect the result.
    """
    import time

    started = time.perf_counter()
    root_path = Path(root).resolve()
    config = config or ScanConfig()
    registry = registry or Registry.load(root_path)

    spec = _load_ignore_spec(root_path, config.ignore)
    files = _walk(root_path, spec)

    result = ScanResult(root=root_path, config_hash=config.config_hash())
    skipped = 0
    collected: list[
        tuple[str, list[ModelFinding], list[PromptFinding], list[ToolFinding], list[McpFinding]]
    ] = []

    def work(
        item: tuple[str, Path],
    ) -> tuple[
        str, list[ModelFinding], list[PromptFinding], list[ToolFinding], list[McpFinding], bool
    ]:
        rel, path = item
        try:
            models, prompts, tools, mcp, read = _scan_one(rel, path, registry, config)
        except PromptCollision:
            raise
        return rel, models, prompts, tools, mcp, read

    max_workers = min(8, (os.cpu_count() or 1) + 4)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for rel, models, prompts, tools, mcp, read in pool.map(work, files):
            if not read:
                skipped += 1
                continue
            result.files_scanned += 1
            collected.append((rel, models, prompts, tools, mcp))

    collected.sort(key=lambda row: row[0])

    def sort_key(item: object) -> tuple[str, int, str]:
        return (
            getattr(item, "file", getattr(item, "path", "")),
            getattr(item, "line", 0),
            getattr(item, "name", getattr(item, "id", "")),
        )

    for _rel, models, prompts, tools, mcp in collected:
        result.models.extend(models)
        result.prompts.extend(prompts)
        result.tools.extend(tools)
        result.mcp_servers.extend(mcp)

    result.models.sort(key=sort_key)
    result.prompts.sort(key=sort_key)
    result.tools.sort(key=sort_key)
    result.mcp_servers.sort(key=sort_key)

    # Prompt ids must be unique repo-wide; the per-file check cannot see this.
    seen: dict[str, PromptFinding] = {}
    for prompt in result.prompts:
        prior = seen.get(prompt.id)
        if prior is not None and prior.sha256 != prompt.sha256:
            raise PromptCollision(
                prompt.id,
                f"{prior.path}:{prior.line}",
                f"{prompt.path}:{prompt.line}",
            )
        seen.setdefault(prompt.id, prompt)

    result.files_skipped = skipped
    result.duration_ms = int((time.perf_counter() - started) * 1000)
    return result

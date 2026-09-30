"""Tool / function schema detection (F-SCAN-3).

Covers the schema shapes people actually ship:

* OpenAI ``{"type": "function", "function": {…}}``
* Anthropic / MCP ``{name, description, input_schema|inputSchema|parameters}``
* Python decorators: ``@tool``, ``@mcp.tool()``, ``@function_tool``, ``@agent.tool``
* Pydantic models passed to ``tools=[…]`` (best effort by class name)
* LangChain ``StructuredTool.from_function``
* TS/JS: Vercel AI SDK ``tool({…})`` and MCP SDK ``server.tool("name", …)``
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass

from .annotations import find_annotation

__all__ = ["ToolFinding", "find_tools"]

_SOURCE_BY_EXT = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".py": "python-dict",
    ".ts": "ts-sdk",
    ".tsx": "ts-sdk",
    ".js": "ts-sdk",
    ".jsx": "ts-sdk",
    ".mjs": "ts-sdk",
    ".cjs": "ts-sdk",
}

_SCHEMA_KEYS = ("input_schema", "inputSchema", "parameters", "args_schema")
_DESCRIPTION_KEYS = ("description", "desc", "docstring")


@dataclass(frozen=True)
class ToolFinding:
    """A tool / function schema discovered in the repository."""

    name: str
    file: str
    line: int
    sha256: str
    description: str
    param_keys: tuple[str, ...]
    source: str


def _canonical_sha(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _param_keys(schema: object) -> tuple[str, ...]:
    if not isinstance(schema, dict):
        return ()
    props = schema.get("properties")
    if isinstance(props, dict):
        return tuple(sorted(props))
    # Anthropic style: {"type": "object", "properties": {...}} or a bare list.
    if isinstance(schema.get("input_schema"), dict):
        return _param_keys(schema["input_schema"])
    if isinstance(schema, dict) and all(isinstance(v, dict) for v in schema.values()):
        return tuple(sorted(schema))
    return ()


def _tool_from_mapping(
    obj: dict[str, object], file: str, line: int, source: str
) -> ToolFinding | None:
    """Recognise a tool schema in a decoded JSON/YAML/Python mapping."""
    name = obj.get("name")
    if not isinstance(name, str) or not name:
        # OpenAI nests the real schema under "function".
        fn = obj.get("function")
        if isinstance(fn, dict):
            return _tool_from_mapping(fn, file, line, source)
        return None

    has_schema = any(k in obj for k in _SCHEMA_KEYS)
    if not has_schema and obj.get("type") != "function":
        return None

    description = ""
    for key in _DESCRIPTION_KEYS:
        value = obj.get(key)
        if isinstance(value, str):
            description = value
            break

    schema_obj: object = {}
    for key in _SCHEMA_KEYS:
        if key in obj:
            schema_obj = obj[key]
            break

    canonical = {
        "name": name,
        "description": description,
        "parameters": schema_obj if isinstance(schema_obj, dict) else {},
    }
    return ToolFinding(
        name=name,
        file=file,
        line=line,
        sha256=_canonical_sha(canonical),
        description=description,
        param_keys=_param_keys(schema_obj),
        source=source,
    )


def _walk_json(node: object, file: str, source: str, out: list[ToolFinding], line: int = 1) -> None:
    if isinstance(node, dict):
        found = _tool_from_mapping(node, file, line, source)
        if found is not None:
            # The whole mapping is the tool.  Its "parameters"/"function"
            # sub-objects would otherwise be re-matched as tools themselves.
            out.append(found)
            return
        for value in node.values():
            _walk_json(value, file, source, out, line)
    elif isinstance(node, list):
        for value in node:
            _walk_json(value, file, source, out, line)


# ---------------------------------------------------------------------------
# Python: decorators + dict literals + StructuredTool
# ---------------------------------------------------------------------------
_TOOL_DECORATORS = ("tool", "function_tool", "mcp.tool", "agent.tool", "server.tool")
_STRUCTURED_TOOL_RE = re.compile(r"StructuredTool\.from_function")
_PYDANTIC_TOOLS_RE = re.compile(r"tools\s*=\s*\[(?P<body>[^\]]*)\]")


def _decorator_name(dec: ast.expr) -> str:
    if isinstance(dec, ast.Name):
        return dec.id
    if isinstance(dec, ast.Attribute):
        base = _decorator_name(dec.value)
        return f"{base}.{dec.attr}" if base else dec.attr
    if isinstance(dec, ast.Call):
        return _decorator_name(dec.func)
    return ""


def _python_tools(source: str, file: str, tree: ast.Module | None = None) -> list[ToolFinding]:
    out: list[ToolFinding] = []
    # Every Python tool form needs a dict literal (`{`), a decorator (`@`) or a
    # `tools=[...]` list.  Without any of those the AST walk cannot find one.
    if "{" not in source and "@" not in source and "tools" not in source:
        return out
    if tree is None:
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError, RecursionError):
            return out

    dict_findings: list[tuple[int, int, ToolFinding]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names = [_decorator_name(d) for d in node.decorator_list]
            if not any(n in _TOOL_DECORATORS for n in names):
                continue
            docstring = ast.get_docstring(node) or ""
            args = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
            canonical = {"name": node.name, "description": docstring, "parameters": sorted(args)}
            out.append(
                ToolFinding(
                    name=node.name,
                    file=file,
                    line=node.lineno,
                    sha256=_canonical_sha(canonical),
                    description=docstring,
                    param_keys=tuple(sorted(args)),
                    source="decorator",
                )
            )
        elif isinstance(node, ast.Dict):
            try:
                obj = ast.literal_eval(node)
            except (ValueError, SyntaxError, TypeError, RecursionError):
                continue
            if not isinstance(obj, dict):
                continue
            found = _tool_from_mapping(obj, file, node.lineno, "python-dict")
            if found is not None:
                dict_findings.append((node.lineno, node.end_lineno or node.lineno, found))

    # A nested dict inside a matched tool schema is part of that tool, not a
    # second tool.  Drop any match whose span sits inside another match's span.
    for start, end, finding in dict_findings:
        if any(
            other_start <= start and end <= other_end and (other_start, other_end) != (start, end)
            for other_start, other_end, _ in dict_findings
        ):
            continue
        out.append(finding)

    # Pydantic / LangChain best-effort: names referenced in tools=[...].
    # A cheap prefilter keeps the regex off files that cannot contain the form.
    if "tools" in source and "[" in source:
        for match in _PYDANTIC_TOOLS_RE.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            for raw in match.group("body").split(","):
                ref = raw.strip()
                if not ref or not re.match(r"^[A-Za-z_][\w.]*$", ref):
                    continue
                out.append(
                    ToolFinding(
                        name=ref,
                        file=file,
                        line=line,
                        sha256=_canonical_sha({"ref": ref}),
                        description="",
                        param_keys=(),
                        source="pydantic",
                    )
                )
    if "StructuredTool" in source:
        structured = _STRUCTURED_TOOL_RE.search(source)
        if structured is not None:
            line = source.count("\n", 0, structured.start()) + 1
            out.append(
                ToolFinding(
                    name="StructuredTool.from_function",
                    file=file,
                    line=line,
                    sha256=_canonical_sha({"kind": "langchain-structured-tool"}),
                    description="",
                    param_keys=(),
                    source="python-dict",
                )
            )
    return out


# ---------------------------------------------------------------------------
# TS/JS: tool({...}) and server.tool("name", ...)
# ---------------------------------------------------------------------------
_TS_TOOL_CALL_RE = re.compile(r"\btool\s*\(\s*\{")
_TS_MCP_TOOL_RE = re.compile(r"\.tool\s*\(\s*(?P<q>[\"'])(?P<name>[^\"']+)(?P=q)")
_TS_NAME_RE = re.compile(r"\bname\s*:\s*(?P<q>[\"'])(?P<name>[^\"']+)(?P=q)")


def _ts_tools(source: str, file: str) -> list[ToolFinding]:
    out: list[ToolFinding] = []
    for match in _TS_MCP_TOOL_RE.finditer(source):
        name = match.group("name")
        line = source.count("\n", 0, match.start()) + 1
        out.append(
            ToolFinding(
                name=name,
                file=file,
                line=line,
                sha256=_canonical_sha({"name": name, "sdk": "mcp"}),
                description="",
                param_keys=(),
                source="ts-sdk",
            )
        )
    for match in _TS_TOOL_CALL_RE.finditer(source):
        window = source[match.start() : match.start() + 600]
        name_m = _TS_NAME_RE.search(window)
        if name_m is None:
            continue
        name = name_m.group("name")
        line = source.count("\n", 0, match.start()) + 1
        param_keys = tuple(sorted(re.findall(r"^\s*(\w+)\s*:", window, re.MULTILINE)))
        out.append(
            ToolFinding(
                name=name,
                file=file,
                line=line,
                sha256=_canonical_sha({"name": name, "sdk": "vercel-ai"}),
                description="",
                param_keys=param_keys,
                source="ts-sdk",
            )
        )
    return out


def find_tools(source: str, *, rel_path: str, tree: ast.Module | None = None) -> list[ToolFinding]:
    """Return tool findings for one file's contents.

    Pass *tree* to reuse an already-parsed Python AST.
    """
    suffix = "." + rel_path.rsplit(".", 1)[-1].lower() if "." in rel_path else ""
    source_kind = _SOURCE_BY_EXT.get(suffix)
    if source_kind is None:
        return []

    lines = source.splitlines()
    out: list[ToolFinding] = []

    if source_kind == "json":
        try:
            data = json.loads(source)
        except (json.JSONDecodeError, ValueError):
            return []
        _walk_json(data, rel_path, "json", out)
    elif source_kind == "yaml":
        try:
            import yaml

            data = yaml.safe_load(source)
        except Exception:
            return []
        _walk_json(data, rel_path, "yaml", out)
    elif source_kind == "python-dict":
        out = _python_tools(source, rel_path, tree)
    elif source_kind == "ts-sdk":
        out = _ts_tools(source, rel_path)

    filtered: list[ToolFinding] = []
    for finding in out:
        line_index = finding.line - 1
        ann = find_annotation(lines, line_index) if 0 <= line_index < len(lines) else None
        if ann is not None and ann.kind == "ignore":
            continue
        filtered.append(finding)
    return filtered

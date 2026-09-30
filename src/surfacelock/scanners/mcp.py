"""MCP server configuration detection (F-SCAN-4).

Parses the config files agents actually read and records the server shape.
Environment *values* are never recorded — only key names — so a scan can be
safely pasted into an issue.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

__all__ = ["MCP_CONFIG_PATHS", "McpFinding", "find_mcp_servers"]

# Exact config paths worth checking, relative to the repo root.
MCP_CONFIG_PATHS: tuple[str, ...] = (
    ".cursor/mcp.json",
    ".vscode/mcp.json",
    ".claude/mcp.json",
    ".mcp.json",
    "mcp.json",
    "claude_desktop_config.json",
    ".gemini/settings.json",
    ".codex/config.toml",
    ".continue/config.yaml",
)

_MCP_GLOB_RE = re.compile(r".*mcp.*\.(?:json|yaml|yml|toml)$", re.IGNORECASE)
_SERVER_MAPS = ("mcpServers", "servers", "mcp_servers")

_UNPINNED_RUNNERS = ("npx", "uvx", "bunx", "pipx")

# A version is present only when a digit follows the separator.  This
# distinguishes `server-git@1.2.3` (pinned) from `@scope/server-git`
# (unpinned — the `@` is the npm scope, not a version) and from `pkg@latest`.
_VERSIONED_ARG_RE = re.compile(r"@\d|==\d")


def is_pinned_runner(command: str, args: tuple[str, ...]) -> bool:
    """True when a package runner is given an explicit version.

    Only meaningful for ``npx``/``uvx``/``bunx``/``pipx``; every other command
    is treated as already pinned.
    """
    if not command:
        return True
    base = command.replace("\\", "/").rsplit("/", 1)[-1]
    if base not in _UNPINNED_RUNNERS:
        return True
    for arg in args:
        if arg.startswith("-"):
            continue
        return bool(_VERSIONED_ARG_RE.search(arg))
    return False


@dataclass(frozen=True)
class McpFinding:
    """An MCP server entry discovered in a config file."""

    name: str
    path: str
    transport: str
    url: str = ""
    command: str = ""
    args: tuple[str, ...] = ()
    env_keys: tuple[str, ...] = ()
    header_keys: tuple[str, ...] = ()
    sha256: str = ""
    pinned: bool = True
    insecure: bool = False


def is_mcp_config(rel_path: str) -> bool:
    """True when *rel_path* is a known or glob-matched MCP config."""
    posix = rel_path.replace("\\", "/")
    if posix in MCP_CONFIG_PATHS:
        return True
    return bool(_MCP_GLOB_RE.match(PurePosixPath(posix).name))


def _canonical_sha(entry: dict[str, Any]) -> str:
    """Hash the entry with secret *values* removed."""
    redacted: dict[str, Any] = {}
    for key, value in entry.items():
        if (key in ("env", "environment") and isinstance(value, dict)) or (
            key == "headers" and isinstance(value, dict)
        ):
            redacted[key] = dict.fromkeys(sorted(value), "<redacted>")
        else:
            redacted[key] = value
    canonical = json.dumps(redacted, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _infer_transport(entry: dict[str, Any]) -> str:
    explicit = entry.get("transport") or entry.get("type")
    if isinstance(explicit, str) and explicit:
        normalised = explicit.lower().replace("_", "-")
        if normalised in ("stdio", "http", "sse", "streamable-http", "streamablehttp"):
            return "streamable-http" if normalised == "streamablehttp" else normalised
    url = entry.get("url") or entry.get("serverUrl")
    if isinstance(url, str) and url:
        if url.startswith("sse:"):
            return "sse"
        return "http"
    if entry.get("command"):
        return "stdio"
    return "unknown"


def _is_pinned(command: str, args: tuple[str, ...]) -> bool:
    """Version-pinned when a runner is given an explicit ``pkg@version``."""
    return is_pinned_runner(command, args)


def _server_entry(name: str, entry: Any, path: str) -> McpFinding | None:
    if not isinstance(entry, dict):
        return None
    transport = _infer_transport(entry)
    url = str(entry.get("url") or entry.get("serverUrl") or "")
    command = str(entry.get("command") or "")
    raw_args = entry.get("args") or []
    args = tuple(str(a) for a in raw_args) if isinstance(raw_args, list) else ()
    env = entry.get("env") or entry.get("environment") or {}
    env_keys = tuple(sorted(env)) if isinstance(env, dict) else ()
    headers = entry.get("headers") or {}
    header_keys = tuple(sorted(headers)) if isinstance(headers, dict) else ()

    insecure = url.startswith("http://")
    pinned = _is_pinned(command, args)

    return McpFinding(
        name=name,
        path=path,
        transport=transport,
        url=url,
        command=command,
        args=args,
        env_keys=env_keys,
        header_keys=header_keys,
        sha256=_canonical_sha(entry),
        pinned=pinned,
        insecure=insecure,
    )


def _servers_from_mapping(data: Any, path: str) -> list[McpFinding]:
    if not isinstance(data, dict):
        return []
    servers: Any = None
    for key in _SERVER_MAPS:
        if key in data and isinstance(data[key], dict):
            servers = data[key]
            break
    if servers is None:
        # Some configs nest under a "mcp" object.
        nested = data.get("mcp")
        if isinstance(nested, dict):
            return _servers_from_mapping(nested, path)
        return []
    out: list[McpFinding] = []
    for name, entry in sorted(servers.items()):
        finding = _server_entry(str(name), entry, path)
        if finding is not None:
            out.append(finding)
    return out


def _parse_json(source: str) -> Any:
    try:
        return json.loads(source)
    except (json.JSONDecodeError, ValueError):
        # Tolerate JSONC (comments/trailing commas) used by .vscode and .cursor.
        stripped = re.sub(r"(?m)^\s*//.*$", "", source)
        stripped = re.sub(r",\s*([}\]])", r"\1", stripped)
        try:
            return json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            return None


def find_mcp_servers(source: str, *, rel_path: str) -> list[McpFinding]:
    """Return MCP server findings for one config file's contents."""
    posix = rel_path.replace("\\", "/")
    if not is_mcp_config(posix):
        return []
    name = PurePosixPath(posix).name.lower()

    data: Any = None
    if name.endswith(".json"):
        data = _parse_json(source)
    elif name.endswith((".yaml", ".yml")):
        try:
            import yaml

            data = yaml.safe_load(source)
        except Exception:
            data = None
    elif name.endswith(".toml"):
        import tomllib

        try:
            data = tomllib.loads(source)
        except Exception:
            data = None

    if data is None:
        return []
    return _servers_from_mapping(data, posix)

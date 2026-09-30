"""Policy engine (F-POL-*): turn lock + scan into actionable findings."""

from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .lockfile import Lockfile
from .registry import Registry
from .scanners import ScanConfig
from .scanners.annotations import parse_allow_codes

__all__ = [
    "DOCS_BASE",
    "FINDING_CODES",
    "Finding",
    "Policy",
    "PolicyResult",
    "check_policy",
    "load_config",
]

DOCS_BASE = "https://iggym.github.io/surfacelock/findings/"

#: Every stable finding code emitted by v0.1.
FINDING_CODES: tuple[str, ...] = (
    "UNPINNED_MODEL",
    "UNKNOWN_MODEL",
    "MODEL_DEPRECATED",
    "MODEL_RETIRING",
    "MODEL_RETIRED",
    "MODEL_DENIED",
    "MODEL_NOT_ALLOWED",
    "PROVIDER_NOT_ALLOWED",
    "MCP_INSECURE",
    "MCP_UNPINNED",
    "PROMPT_TOO_LARGE",
    "PROMPT_NO_OWNER",
    "PROMPT_ID_COLLISION",
)

SEVERITY: dict[str, str] = {
    "UNPINNED_MODEL": "error",
    "UNKNOWN_MODEL": "warning",
    "MODEL_DEPRECATED": "warning",
    "MODEL_RETIRING": "error",
    "MODEL_RETIRED": "error",
    "MODEL_DENIED": "error",
    "MODEL_NOT_ALLOWED": "error",
    "PROVIDER_NOT_ALLOWED": "error",
    "MCP_INSECURE": "error",
    "MCP_UNPINNED": "warning",
    "PROMPT_TOO_LARGE": "error",
    "PROMPT_NO_OWNER": "warning",
    "PROMPT_ID_COLLISION": "error",
}

#: Codes that do not fail the run even at "error" severity.
NON_FAILING: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Finding:
    """A policy violation with a stable code and a documentation link."""

    code: str
    message: str
    path: str = ""
    line: int = 0
    severity: str = "error"
    suppressed: bool = False
    reason: str | None = None

    @property
    def docs_url(self) -> str:
        return f"{DOCS_BASE}{self.code}.md"

    @property
    def location(self) -> str:
        if self.path and self.line:
            return f"{self.path}:{self.line}"
        return self.path

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "severity": self.severity,
            "suppressed": self.suppressed,
            "reason": self.reason,
            "docs_url": self.docs_url,
        }


@dataclass
class Policy:
    """``[policy]`` configuration with spec defaults."""

    fail_on_unpinned: bool = True
    fail_on_unknown_models: bool = False
    deprecation_warn_days: int = 90
    deprecation_fail_days: int = 30
    fail_on_retired: bool = True
    allow_models: tuple[str, ...] = ()
    deny_models: tuple[str, ...] = ()
    allow_providers: tuple[str, ...] = ()
    require_mcp_pinned: bool = True
    max_prompt_tokens: int = 0
    require_prompt_owner: bool = False
    scan: ScanConfig = field(default_factory=ScanConfig)
    codeowners: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Policy:
        policy_data = data.get("policy", {}) if isinstance(data, dict) else {}
        scan_data = data.get("scan", {}) if isinstance(data, dict) else {}
        return cls(
            fail_on_unpinned=bool(policy_data.get("fail_on_unpinned", True)),
            fail_on_unknown_models=bool(policy_data.get("fail_on_unknown_models", False)),
            deprecation_warn_days=int(policy_data.get("deprecation_warn_days", 90)),
            deprecation_fail_days=int(policy_data.get("deprecation_fail_days", 30)),
            fail_on_retired=bool(policy_data.get("fail_on_retired", True)),
            allow_models=tuple(policy_data.get("allow_models", ())),
            deny_models=tuple(policy_data.get("deny_models", ())),
            allow_providers=tuple(policy_data.get("allow_providers", ())),
            require_mcp_pinned=bool(policy_data.get("require_mcp_pinned", True)),
            max_prompt_tokens=int(policy_data.get("max_prompt_tokens", 0)),
            require_prompt_owner=bool(policy_data.get("require_prompt_owner", False)),
            scan=ScanConfig(
                ignore=tuple(scan_data.get("ignore", ())),
                prompt_dirs=tuple(scan_data.get("prompt_dirs", ())),
                min_inline_chars=int(scan_data.get("min_inline_chars", 160)),
            ),
        )


def load_config(root: Path) -> tuple[Policy, Path | None]:
    """Load ``surfacelock.toml`` from *root*, returning the policy and its path."""
    path = root / "surfacelock.toml"
    if not path.is_file():
        return Policy(), None
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    policy = Policy.from_mapping(data)
    policy.codeowners = _load_codeowners(root)
    return policy, path


def _load_codeowners(root: Path) -> dict[str, tuple[str, ...]]:
    for candidate in ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"):
        path = root / candidate
        if not path.is_file():
            continue
        rules: dict[str, tuple[str, ...]] = {}
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            rules[parts[0]] = tuple(parts[1:])
        return rules
    return {}


def owners_for(path: str, rules: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Last matching CODEOWNERS rule wins, per git convention.

    A pattern ending in ``/`` is a directory prefix, ``*`` matches any path,
    and everything else is matched with shell globbing.
    """
    matched: tuple[str, ...] = ()
    for pattern, owners in rules.items():
        pat = pattern.lstrip("/")
        hit = False
        if pat in ("*", "**"):
            hit = True
        elif pat.endswith("/"):
            hit = path.startswith(pat)
        elif fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, f"*/{pat}"):
            hit = True
        if hit:
            matched = owners
    return matched


def _glob_match_any(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


@dataclass
class PolicyResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error" and not f.suppressed]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning" and not f.suppressed]

    @property
    def suppressed(self) -> list[Finding]:
        return [f for f in self.findings if f.suppressed]

    @property
    def ok(self) -> bool:
        return not self.errors


def _read_lines(root: Path, rel: str) -> list[str]:
    path = root / rel
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:  # pragma: no cover
        return []


def _apply_suppressions(root: Path, findings: list[Finding]) -> list[Finding]:
    """Mark findings suppressed when the offending line carries ``allow``."""
    cache: dict[str, list[str]] = {}
    out: list[Finding] = []
    for finding in findings:
        if not finding.path or not finding.line:
            out.append(finding)
            continue
        if finding.path not in cache:
            cache[finding.path] = _read_lines(root, finding.path)
        lines = cache[finding.path]
        idx = finding.line - 1
        if 0 <= idx < len(lines):
            codes = parse_allow_codes(lines[idx])
            if finding.code in codes:
                from .scanners.annotations import parse_annotation

                ann = parse_annotation(lines[idx])
                out.append(
                    Finding(
                        code=finding.code,
                        message=finding.message,
                        path=finding.path,
                        line=finding.line,
                        severity=finding.severity,
                        suppressed=True,
                        reason=ann.reason if ann else None,
                    )
                )
                continue
        out.append(finding)
    return out


def check_policy(
    lock: Lockfile,
    registry: Registry,
    policy: Policy,
    *,
    root: Path,
    today: date | None = None,
) -> PolicyResult:
    """Evaluate every policy rule against a lockfile."""
    today = today or date.today()
    findings: list[Finding] = []

    for model in lock.models:
        locations = model.locations or [""]
        for location in locations:
            path, _, line_s = location.partition(":")
            line = int(line_s) if line_s.isdigit() else 0

            if model.floating and policy.fail_on_unpinned:
                findings.append(
                    Finding(
                        "UNPINNED_MODEL",
                        f"`{model.name}` is a floating alias; pin it to "
                        f"`{model.resolved}` or run `surfacelock pin {model.name}`.",
                        path,
                        line,
                    )
                )
            if not model.known and policy.fail_on_unknown_models:
                findings.append(
                    Finding(
                        "UNKNOWN_MODEL",
                        f"`{model.name}` is not in the registry; add it to "
                        f".surfacelock/models.json or annotate it.",
                        path,
                        line,
                    )
                )
            if _glob_match_any(model.name, policy.deny_models):
                findings.append(
                    Finding(
                        "MODEL_DENIED",
                        f"`{model.name}` is on the deny list.",
                        path,
                        line,
                    )
                )
            if policy.allow_models and not _glob_match_any(model.name, policy.allow_models):
                findings.append(
                    Finding(
                        "MODEL_NOT_ALLOWED",
                        f"`{model.name}` is not on the allow list.",
                        path,
                        line,
                    )
                )
            if policy.allow_providers and model.provider not in policy.allow_providers:
                findings.append(
                    Finding(
                        "PROVIDER_NOT_ALLOWED",
                        f"provider `{model.provider}` is not on the allow list.",
                        path,
                        line,
                    )
                )

            retirement = _parse(model.retirement)
            if retirement is not None:
                days = (retirement - today).days
                if days < 0 and policy.fail_on_retired:
                    findings.append(
                        Finding(
                            "MODEL_RETIRED",
                            f"`{model.name}` was retired on {model.retirement}.",
                            path,
                            line,
                        )
                    )
                elif 0 <= days <= policy.deprecation_fail_days:
                    findings.append(
                        Finding(
                            "MODEL_RETIRING",
                            f"`{model.name}` retires on {model.retirement} ({days} days away).",
                            path,
                            line,
                        )
                    )
                elif 0 <= days <= policy.deprecation_warn_days:
                    findings.append(
                        Finding(
                            "MODEL_DEPRECATED",
                            f"`{model.name}` retires on {model.retirement} ({days} days away).",
                            path,
                            line,
                            severity="warning",
                        )
                    )

    for server in lock.mcp_servers:
        if server.url.startswith("http://"):
            findings.append(
                Finding(
                    "MCP_INSECURE",
                    f"MCP server `{server.name}` uses plaintext http:// — use https://.",
                    server.path,
                    0,
                )
            )
        if policy.require_mcp_pinned and not _mcp_pinned(server):
            findings.append(
                Finding(
                    "MCP_UNPINNED",
                    f"MCP server `{server.name}` runs `{server.command}` without a "
                    f"version pin; pin the package or use a container digest.",
                    server.path,
                    0,
                )
            )

    for prompt in lock.prompts:
        if policy.max_prompt_tokens and prompt.approx_tokens > policy.max_prompt_tokens:
            findings.append(
                Finding(
                    "PROMPT_TOO_LARGE",
                    f"prompt `{prompt.id}` is ~{prompt.approx_tokens} tokens "
                    f"(limit {policy.max_prompt_tokens}).",
                    prompt.path,
                    prompt.line,
                )
            )
        if policy.require_prompt_owner and not prompt.owners:
            findings.append(
                Finding(
                    "PROMPT_NO_OWNER",
                    f"prompt `{prompt.id}` has no CODEOWNERS match.",
                    prompt.path,
                    prompt.line,
                )
            )

    findings = _apply_suppressions(root, findings)
    findings.sort(key=lambda f: (f.path, f.line, f.code))
    return PolicyResult(findings=findings)


def _mcp_pinned(server: Any) -> bool:
    from .scanners.mcp import is_pinned_runner

    return is_pinned_runner(server.command or "", tuple(server.args or ()))


def _parse(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def deprecation_window(policy: Policy) -> tuple[date, date]:
    """Return ``(warn_start, fail_start)`` relative to today for reporting."""
    today = date.today()
    return (
        today + timedelta(days=policy.deprecation_warn_days),
        today + timedelta(days=policy.deprecation_fail_days),
    )

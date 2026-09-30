"""surfacelock — a lockfile for the AI surface of your codebase.

Public API (stable within 0.x minor versions)::

    from surfacelock import scan, build_lock, check

The three functions below are the supported entry points.  Everything else is
internal and may change between minor releases.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .lockfile import (
    Diff,
    DiffEntry,
    Lockfile,
    LockMcp,
    LockModel,
    LockPrompt,
    LockTool,
    diff_locks,
    read_lock,
)
from .lockfile import (
    build_lock as _build_lock,
)
from .policy import Finding, Policy, PolicyResult, check_policy, load_config
from .registry import ModelInfo, Registry
from .scanners import ScanConfig, ScanResult
from .scanners import scan as _scan
from .scanners.textutil import python_context

__version__ = "0.1.0"

__all__ = [
    "CheckResult",
    "Diff",
    "DiffEntry",
    "Finding",
    "LockMcp",
    "LockModel",
    "LockPrompt",
    "LockTool",
    "Lockfile",
    "ModelInfo",
    "Policy",
    "PolicyResult",
    "Registry",
    "ScanConfig",
    "ScanResult",
    "__version__",
    "build_lock",
    "check",
    "python_context",
    "scan",
]


def scan(
    path: str | Path = ".", *, config: ScanConfig | None = None, registry: Registry | None = None
) -> ScanResult:
    """Scan a repository and return its AI surface findings.

    Parameters
    ----------
    path:
        Repository root.  ``.gitignore``, ``.surfacelockignore`` and the
        default ignore list are respected.
    config:
        Optional :class:`ScanConfig` overriding ignore rules and thresholds.
    registry:
        Optional pre-loaded :class:`Registry`; one is loaded from *path* when
        omitted.
    """
    return _scan(path, config=config, registry=registry)


def build_lock(
    path: str | Path = ".",
    *,
    registry: Registry | None = None,
    config: ScanConfig | None = None,
    previous: Lockfile | None = None,
    resolve: set[str] | None = None,
) -> Lockfile:
    """Scan *path* and build a :class:`Lockfile`.

    Existing pins from *previous* are preserved unless their model name appears
    in *resolve* (or *resolve* contains ``"all"``).
    """
    root = Path(path).resolve()
    registry = registry or Registry.load(root)
    result = _scan(root, config=config, registry=registry)
    return _build_lock(result, registry, version=__version__, previous=previous, resolve=resolve)


@dataclass
class CheckResult:
    """The outcome of :func:`check`."""

    ok: bool
    drift: Diff
    policy: PolicyResult
    lock: Lockfile
    scan: ScanResult | None = None

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1


def check(
    path: str | Path = ".",
    *,
    allow_drift: bool = False,
    today: str | None = None,
) -> CheckResult:
    """Rescan *path*, diff against ``surface.lock`` and run policy.

    Raises :class:`FileNotFoundError` when no lockfile exists — the CLI maps
    that to exit code 2.
    """
    from datetime import date as _date

    root = Path(path).resolve()
    lock_path = root / "surface.lock"
    if not lock_path.is_file():
        raise FileNotFoundError(lock_path)

    registry = Registry.load(root)
    policy, _ = load_config(root)
    previous = read_lock(lock_path)
    fresh = _build_lock(
        _scan(root, config=policy.scan, registry=registry),
        registry,
        version=__version__,
        previous=previous,
    )
    drift = diff_locks(previous, fresh)
    parsed_today = _date.fromisoformat(today) if today else None
    policy_result = check_policy(fresh, registry, policy, root=root, today=parsed_today)
    ok = policy_result.ok and (allow_drift or not drift.changed)
    return CheckResult(ok=ok, drift=drift, policy=policy_result, lock=fresh)

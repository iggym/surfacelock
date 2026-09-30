"""Markdown PR summary rendering (F-EXPLAIN / §7.4)."""

from __future__ import annotations

from dataclasses import dataclass

from .lockfile import Diff, Lockfile
from .policy import PolicyResult
from .registry import Registry

__all__ = ["CostEstimate", "render_explain"]

_ACTION_ICON = {"added": "➕", "removed": "➖", "changed": "✏️"}
_KIND_LABEL = {
    "model": "model",
    "prompt": "prompt",
    "tool": "tool",
    "mcp_server": "mcp",
}


@dataclass
class CostEstimate:
    """A deliberately rough per-call cost delta."""

    token_delta: int
    usd_delta: float
    reference_model: str | None

    def render(self) -> str:
        if self.token_delta == 0 and abs(self.usd_delta) < 1e-9:
            return "no net change"
        sign = "+" if self.usd_delta >= 0 else "-"
        tokens = f"{self.token_delta:+d} tokens/call"
        usd = f"{sign}${abs(self.usd_delta):.6f}/call"
        ref = f" at {self.reference_model} input pricing" if self.reference_model else ""
        return f"{tokens} · {usd}{ref}"


def _estimate_cost(diff: Diff, registry: Registry, lock: Lockfile) -> CostEstimate:
    """Estimate per-call token and USD delta.

    Prompt changes contribute a token delta; that delta is priced at the most
    expensive input price present in the lock so the number is an upper bound
    rather than a flattering average.
    """
    token_delta = 0
    for entry in diff.by_kind("prompt"):
        if entry.action == "added":
            token_delta += _tokens_from_detail(entry.detail)
        elif entry.action == "removed":
            token_delta -= _tokens_from_detail(entry.detail)
        elif entry.action == "changed":
            token_delta += _delta_from_detail(entry.detail)

    reference = None
    reference_price = 0.0
    for model in lock.models:
        if model.price_in_per_1m and model.price_in_per_1m > reference_price:
            reference_price = model.price_in_per_1m
            reference = model.name

    usd_delta = token_delta / 1_000_000 * reference_price if reference_price else 0.0
    return CostEstimate(token_delta=token_delta, usd_delta=usd_delta, reference_model=reference)


def _tokens_from_detail(detail: str) -> int:
    for part in detail.split():
        if part.isdigit():
            return int(part)
    return 0


def _delta_from_detail(detail: str) -> int:
    if "(" in detail and detail.endswith(")"):
        inner = detail[detail.rfind("(") + 1 : -1]
        try:
            return int(inner)
        except ValueError:
            return 0
    return 0


def render_explain(
    diff: Diff,
    lock: Lockfile,
    policy_result: PolicyResult,
    registry: Registry,
    *,
    version: str,
) -> str:
    """Render the ``explain`` Markdown summary."""
    estimate = _estimate_cost(diff, registry, lock)
    lines: list[str] = ["### 🔒 surfacelock — AI surface changes", ""]

    if not diff.entries:
        lines.append("_No changes detected in the AI surface._")
        lines.append("")
    else:
        lines.append("| | kind | item | detail |")
        lines.append("|---|---|---|---|")
        for entry in diff.entries:
            icon = _ACTION_ICON.get(entry.action, "•")
            kind = _KIND_LABEL.get(entry.kind, entry.kind)
            detail = entry.detail.replace("|", "\\|")
            item = f"`{entry.name}`".replace("|", "\\|")
            lines.append(f"| {icon} | {kind} | {item} | {detail} |")
        lines.append("")
        lines.append(f"**Net impact:** {estimate.render()}")
        lines.append("")

    snapshot_changes = [
        e for e in diff.by_kind("model") if e.action == "changed" and "→" in e.detail
    ]
    if snapshot_changes:
        lines.append("<details><summary>Suggested regression check</summary>")
        lines.append("")
        for entry in snapshot_changes:
            before, _, after = entry.detail.partition("→")
            lines.append("```bash")
            lines.append(
                f"modelbump diff --from {before.strip()} --to {after.strip()} --suite golden/"
            )
            lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    errors = policy_result.errors
    warnings = policy_result.warnings
    if errors or warnings:
        lines.append("#### Policy")
        lines.append("")
        for finding in errors:
            lines.append(f"- ❌ **{finding.code}** — {finding.message}")
        for finding in warnings:
            lines.append(f"- ⚠️ **{finding.code}** — {finding.message}")
        lines.append("")

    counts = lock.counts
    suppressed = len(policy_result.suppressed)
    lines.append("<sub>")
    lines.append(
        f"{counts.get('models', 0)} models · {counts.get('prompts', 0)} prompts · "
        f"{counts.get('tools', 0)} tools · {counts.get('mcp_servers', 0)} mcp servers · "
        f"{len(errors)} errors · {len(warnings)} warnings · {suppressed} suppressed · "
        f"surfacelock {version}"
    )
    lines.append("</sub>")
    return "\n".join(lines)

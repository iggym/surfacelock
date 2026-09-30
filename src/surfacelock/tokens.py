"""Deterministic approximate token estimation.

The estimator is intentionally simple and dependency-free so that results are
reproducible across machines and CI runs.  ``tiktoken`` is used when it is
installed *and* the caller explicitly opts in, but the default path never
touches the network.
"""

from __future__ import annotations

import re

__all__ = ["TOKENIZER_LABEL", "approx_tokens"]

# Label surfaced in the lockfile and JSON output so nobody mistakes the number
# for an exact provider tokenizer count.
TOKENIZER_LABEL = "approx-v1"

_WORD_RE = re.compile(r"\w+|[^\w\s]")
_CJK_RE = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")


def approx_tokens(text: str, *, use_tiktoken: bool = False) -> int:
    """Return a deterministic estimate of the token count for *text*.

    The heuristic blends two cheap signals: word/punctuation chunks and raw
    characters.  It tracks ``tiktoken`` closely enough for budget deltas while
    staying pure-Python and offline.
    """
    if not text:
        return 0

    if use_tiktoken:  # pragma: no cover - optional dependency path
        try:
            import tiktoken  # type: ignore[import-not-found]

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            pass

    cjk = len(_CJK_RE.findall(text))
    latin = len(text) - cjk
    chunks = len(_WORD_RE.findall(text))
    # ~4 characters per token for latin text, ~1.5 for CJK, blended with the
    # chunk count which captures punctuation-heavy code.
    estimate = max(cjk / 1.5 + latin / 4.0, chunks * 0.75)
    return max(1, round(estimate))

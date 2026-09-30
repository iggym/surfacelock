"""Model identifier detection (F-SCAN-1).

Detection is the conjunction of:

1. a regex family that matches a provider naming scheme, **and**
2. the string is known to the registry **or** the surrounding line carries a
   model-context keyword **or** the string is explicitly annotated.

Conservative by design: a bare ``"1.5.0"`` never matches, and a model name that
only appears inside a comment is never reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .annotations import find_annotation
from .textutil import StringLit, is_comment_line

__all__ = ["MODEL_REGEXES", "ModelFinding", "find_models"]

# Regex families per provider naming scheme.  Each pattern must be anchored to
# the whole string so that version numbers and URLs cannot sneak through.
MODEL_REGEXES: tuple[re.Pattern[str], ...] = (
    # OpenAI chat / reasoning / audio / image families.
    re.compile(r"^(gpt-(?:3\.5|4|4o|4\.1|4\.5|5)[a-z0-9.\-]*|o[1-9](?:-mini|-pro|-preview)?)$"),
    re.compile(r"^chatgpt-[a-z0-9.\-]+$"),
    re.compile(r"^text-(?:embedding|davinci|curie|babbage|ada)[a-z0-9.\-]*$"),
    re.compile(r"^(?:dall-e-\d+|gpt-image-\d+|whisper-\d+|tts-\d+(?:-hd)?)$"),
    # Anthropic.  Newer names interpose a family word before the version
    # (`claude-sonnet-4-20250514`), so a bare leading digit is not enough.
    re.compile(r"^claude-(?:[a-z]+-)?(?:\d[\w.\-]*)$"),
    # Google.
    re.compile(r"^gemini-[\w.\-]+$"),
    re.compile(r"^(?:imagen|veo)-[\w.\-]+$"),
    # Mistral.
    re.compile(
        r"^(?:mistral|open-mistral|open-mixtral|mixtral|codestral|pixtral|magistral)[\w.\-]*$"
    ),
    re.compile(r"^ministral-[\w.\-]+$"),
    # Cohere.
    re.compile(r"^(?:command|embed|rerank)[\w.\-]*$"),
    # xAI.
    re.compile(r"^grok-[\w.\-]+$"),
    # DeepSeek.
    re.compile(r"^deepseek-[\w.\-]+$"),
    # HuggingFace-style org/model ids.
    re.compile(r"^[\w.\-]+/(?:Llama|Meta-Llama|mistral|Mixtral|Qwen|gemma)[\w.\-]*$"),
    # Bedrock ids.
    re.compile(r"^[\w.\-]+\.(?:claude|llama\d?|mistral|mixtral|titan|command|jamba)[\w.\-:]*$"),
    re.compile(r"^(?:amazon|ai21|stability|cohere|anthropic|meta|mistral)\.[\w.\-:]+$"),
    # Azure deployment paths.
    re.compile(r"^azure/[\w.\-]+$"),
)

# A line carrying one of these words is treated as model context, which lets us
# accept provider names the regex families deliberately exclude (e.g. a new
# model released after this tool version).
CONTEXT_KEYWORDS = re.compile(
    r"\b("
    r"model|model_name|model_id|modelName|modelId|deployment|deployment_name|azure_deployment|"
    r"engine|llm|completion|chat_model|embedding_model|embed_model|"
    r"LLM_MODEL|OPENAI_MODEL|ANTHROPIC_MODEL|GEMINI_MODEL|MODEL"
    r")\b",
    re.IGNORECASE,
)

# Strings that look like model names but are definitely not.
_NEGATIVE = re.compile(
    r"^(?:"
    r"[\d.]+|"  # bare version numbers
    r"v?\d+(?:\.\d+)*|"  # v1.2.3
    r"https?://\S+|"
    r"[\w.\-]+\.(?:py|js|ts|json|toml|yaml|yml|md|txt)|"
    r"[\w.\-]+@[\w.\-]+|"
    r"[A-Z_][A-Z0-9_]*$"
    r")$"
)

_AZURE_DEPLOY_RE = re.compile(
    r"\b(?:deployment_name|azure_deployment|deployment_id|AZURE_OPENAI_DEPLOYMENT)\b\s*[=:]\s*"
    r"[\"']?(?P<name>[\w.\-]+)"
)


@dataclass(frozen=True)
class ModelFinding:
    """A model identifier discovered in a source file."""

    name: str
    file: str
    line: int
    context: str  # model | embedding | deployment
    provider: str | None = None
    annotated: bool = False


def _matches_family(value: str) -> bool:
    return any(rx.match(value) for rx in MODEL_REGEXES)


# A bare lowercase English word (``command``, ``embed``, ``rerank``) can be a
# registry key and a dictionary key at the same time.  Such strings only count
# when the surrounding line explicitly says it is a model.
_GENERIC_WORD_RE = re.compile(r"^[a-z]+$")


def _needs_explicit_context(value: str) -> bool:
    return bool(_GENERIC_WORD_RE.match(value))


def _classify_kind(value: str) -> str:
    lowered = value.lower()
    if any(k in lowered for k in ("embed", "bge-", "e5-", "text-embedding", "embedding")):
        return "embedding"
    if any(k in lowered for k in ("rerank", "reranker", "guard")):
        return "rerank"
    if any(k in lowered for k in ("dall-e", "gpt-image", "imagen", "stable-diffusion", "veo")):
        return "image"
    if any(k in lowered for k in ("whisper", "tts-", "audio", "realtime")):
        return "audio"
    return "chat"


def find_models(
    lit: StringLit,
    *,
    lines: list[str],
    rel_path: str,
    registry: object | None = None,
) -> list[ModelFinding]:
    """Return model findings for a single string literal.

    ``registry`` is an object exposing ``__contains__`` and ``get`` (a
    :class:`~surfacelock.registry.Registry`); it may be ``None`` in which case
    only regex + keyword detection applies.
    """
    value = lit.value.strip()
    if not value or len(value) > 200:
        return []
    if _NEGATIVE.match(value):
        return []

    line_text = lines[lit.line - 1] if 0 < lit.line <= len(lines) else ""
    if is_comment_line(line_text):
        return []

    ann = find_annotation(lines, lit.line - 1)
    annotated = ann is not None and ann.kind == "model"
    if ann is not None and ann.kind == "ignore":
        return []

    known = registry is not None and value in registry  # type: ignore[operator]
    has_context = bool(CONTEXT_KEYWORDS.search(line_text))
    in_family = _matches_family(value)

    # Azure deployment names are detected from the keyword, not the regex family.
    azure_match = _AZURE_DEPLOY_RE.search(line_text)
    if azure_match and azure_match.group("name") == value:
        return [
            ModelFinding(
                name=value,
                file=rel_path,
                line=lit.line,
                context="deployment",
                provider="azure",
                annotated=annotated,
            )
        ]

    if not (in_family or annotated or known):
        return []
    if _needs_explicit_context(value) and not (annotated or has_context):
        return []

    provider = None
    if registry is not None:
        info = registry.get(value)  # type: ignore[attr-defined]
        if info is not None:
            provider = info.provider

    return [
        ModelFinding(
            name=value,
            file=rel_path,
            line=lit.line,
            context=_classify_kind(value),
            provider=provider,
            annotated=annotated,
        )
    ]

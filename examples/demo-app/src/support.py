"""A support agent with a realistic AI surface."""

from anthropic import Anthropic

client = Anthropic()

# surfacelock: prompt id=support.system
SYSTEM = """You are a support agent for an online store.

Rules:
  1. Always verify the order id before discussing an order.
  2. Never promise a refund you cannot issue; use the issue_refund tool.
  3. If the customer is upset, acknowledge the problem before troubleshooting.
  4. Escalate to a human when the customer asks twice for one.
"""

CHAT_MODEL = "claude-sonnet-4-20250514"
EMBED_MODEL = "text-embedding-3-small"

FALLBACK_TEMPLATE = (
    "The customer said: {message}. Summarise the complaint in one sentence, "
    "then list the two most likely causes and the next diagnostic step to take. "
    "Keep the whole reply under 80 words and never invent an order id."
)


def ask(message: str) -> str:
    response = client.messages.create(
        model=CHAT_MODEL,
        system=SYSTEM,
        messages=[{"role": "user", "content": FALLBACK_TEMPLATE.format(message=message)}],
    )
    return response.content[0].text

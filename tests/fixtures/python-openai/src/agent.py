"""Support agent backed by OpenAI."""

from openai import OpenAI

client = OpenAI()

# surfacelock: prompt id=agent.support.system
SUPPORT_SYSTEM = """You are a helpful support agent for Acme Corp.
Always be concise, cite the order number, and never promise a refund the
policy engine would reject. Escalate anything involving a chargeback."""

MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"


def answer(question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SUPPORT_SYSTEM},
            {"role": "user", "content": question},
        ],
    )
    return response.choices[0].message.content or ""


ISSUE_REFUND_TOOL = {
    "type": "function",
    "function": {
        "name": "issue_refund",
        "description": "Issue a refund to the customer",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
            },
            "required": ["order_id", "amount"],
        },
    },
}

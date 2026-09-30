"""Tool schemas the support agent can call."""

from dataclasses import dataclass

from anthropic import beta_tool

REFUND_SCHEMA = {
    "type": "function",
    "function": {
        "name": "issue_refund",
        "description": "Issue a refund to the customer",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order to refund"},
                "amount": {"type": "number", "description": "Amount in USD"},
                "reason": {"type": "string", "enum": ["damaged", "late", "wrong_item"]},
            },
            "required": ["order_id", "amount"],
        },
    },
}


@dataclass
class LookupOrder:
    """Look up an order by its identifier."""

    order_id: str


@beta_tool
def lookup_order(order_id: str) -> dict:
    """Look up an order by its identifier."""
    return {"order_id": order_id, "status": "shipped"}

"""Mixed monorepo: Python service + TypeScript worker sharing one AI surface."""

import os

from anthropic import Anthropic

client = Anthropic()

# surfacelock: prompt id=worker.planner.system
PLANNER_SYSTEM = (
    "You are a planning assistant. Break the request into ordered steps, "
    "name the tool you would call at each step, and stop when the plan is "
    "complete. Never invent a tool that is not in the provided list."
)

MODEL = "claude-opus-4-latest"
FALLBACK = "gpt-4o-mini"
AZURE_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-prod")

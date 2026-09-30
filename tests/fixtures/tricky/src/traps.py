"""False-positive traps. Precision on this fixture must be 100%.

Everything below is deliberately *not* AI surface.
"""

import os

# A comment mentioning gpt-4o and claude-3-5-sonnet-latest should be ignored.
VERSION = "1.5.0"
SEMVER = "v2.3.4-beta.1"
URL = "https://api.example.com/v1/models"
DOCS = "https://platform.openai.com/docs/models/gpt-4o"
PACKAGE = "langchain==0.1.0"
EMAIL = "support@openai.com"
ENV_NAME = "OPENAI_API_KEY"
FILENAME = "agent.py"
PATH = "src/agent.py"

# A markdown-ish string that mentions models but is prose, and short.
NOTE = "See the docs for gpt-4o pricing."

# Long but not prompt-ish, and not assigned to a prompt name.
CHANGELOG = (
    "This release updates the HTTP client, fixes a race in the scheduler, and "
    "bumps the minimum Python version. No AI models were touched in this release."
)

os.environ.get("ANTHROPIC_API_KEY")

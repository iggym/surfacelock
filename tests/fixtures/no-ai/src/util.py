"""A repository with no AI surface at all — the lockfile must come out empty."""

import json
from pathlib import Path


def load_config(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


VERSION = "1.5.0"
HOMEPAGE = "https://example.com/docs/getting-started"
LICENSE_NAME = "Apache-2.0"
USER_AGENT = "myapp/1.5.0"


def greeting(name: str) -> str:
    return f"hello, {name}"

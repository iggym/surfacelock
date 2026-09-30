"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture()
def python_openai(fixtures_dir: Path) -> Path:
    return fixtures_dir / "python-openai"


@pytest.fixture()
def tricky(fixtures_dir: Path) -> Path:
    return fixtures_dir / "tricky"


@pytest.fixture()
def no_ai(fixtures_dir: Path) -> Path:
    return fixtures_dir / "no-ai"

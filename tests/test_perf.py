"""Performance: the scanner must stay under 5 s on a 10k-file tree."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from surfacelock.scanners import scan

FILE_COUNT = 10_000
BUDGET_SECONDS = 5.0


@pytest.mark.slow
def test_scan_10k_files_under_5_seconds(tmp_path: Path) -> None:
    body = (
        "import os\n"
        'MODEL = "gpt-4o"\n'
        'SYSTEM_PROMPT = "' + ("You are a careful assistant. " * 12) + '"\n'
        "def handler(request):\n"
        '    return {"ok": True, "path": "/v1/chat"}\n'
    )
    for i in range(FILE_COUNT):
        sub = tmp_path / f"pkg{i // 100}"
        sub.mkdir(exist_ok=True)
        (sub / f"mod_{i}.py").write_text(body, encoding="utf-8")

    start = time.perf_counter()
    result = scan(tmp_path)
    elapsed = time.perf_counter() - start

    assert result.files_scanned >= FILE_COUNT
    assert elapsed < BUDGET_SECONDS, f"scan took {elapsed:.2f}s (budget {BUDGET_SECONDS}s)"


@pytest.mark.slow
def test_scan_is_linear_and_repeatable(tmp_path: Path) -> None:
    body = 'MODEL = "gpt-4o"\n'
    for i in range(500):
        (tmp_path / f"f{i}.py").write_text(body, encoding="utf-8")
    first = scan(tmp_path)
    second = scan(tmp_path)
    assert [m.file for m in first.models] == [m.file for m in second.models]


def test_skip_oversized_file_is_fast(tmp_path: Path) -> None:
    """A file above the 2 MB limit is skipped without being parsed."""
    big = tmp_path / "huge.py"
    big.write_text("x = 1\n" * 500_000, encoding="utf-8")
    assert big.stat().st_size > 2 * 1024 * 1024
    start = time.perf_counter()
    result = scan(tmp_path)
    assert time.perf_counter() - start < 1.0
    assert result.files_skipped == 1

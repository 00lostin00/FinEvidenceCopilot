from pathlib import Path

import pytest

from finevidence.service import Copilot

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def copilot(tmp_path):
    return Copilot(ROOT, trace_path=tmp_path / "trace.jsonl")

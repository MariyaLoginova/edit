from __future__ import annotations

import json
from pathlib import Path
import pytest

from models import ScriptDraft, SourceMap

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fashion_source() -> SourceMap:
    data = json.loads((FIXTURES / "fashion_theory_segment.json").read_text(encoding="utf-8"))
    return SourceMap.model_validate(data)


@pytest.fixture
def biography_source() -> SourceMap:
    data = json.loads((FIXTURES / "biography_segment.json").read_text(encoding="utf-8"))
    return SourceMap.model_validate(data)


@pytest.fixture
def script_weak() -> ScriptDraft:
    data = json.loads((FIXTURES / "script_weak.json").read_text(encoding="utf-8"))
    return ScriptDraft.model_validate(data)


@pytest.fixture
def script_strong() -> ScriptDraft:
    data = json.loads((FIXTURES / "script_strong.json").read_text(encoding="utf-8"))
    return ScriptDraft.model_validate(data)


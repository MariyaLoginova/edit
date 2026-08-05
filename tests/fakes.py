from __future__ import annotations

import json
from typing import Any


class FakeLLM:
    """Детерминированный LLM для юнит-тестов: отдаёт заранее заданный JSON-текст."""

    def __init__(self, payload: Any):
        self.payload = payload
        self.calls: list[list[dict[str, str]]] = []

    def invoke(self, messages: list[dict[str, str]]):
        self.calls.append(messages)
        if callable(self.payload):
            text = self.payload(messages)
        elif isinstance(self.payload, str):
            text = self.payload
        else:
            text = json.dumps(self.payload, ensure_ascii=False)

        class _Resp:
            def __init__(self, content: str):
                self.content = content

        return _Resp(text)

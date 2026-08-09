from __future__ import annotations

import json
from typing import Any

from edit.search import SearchHit


class FakeLLM:
    """Детерминированный LLM для юнит-тестов: отдаёт заранее заданный JSON-текст."""

    def __init__(self, payload: Any = None, *, queue: list[Any] | None = None):
        self.payload = payload
        self._queue = list(queue) if queue is not None else None
        self.calls: list[list[dict[str, str]]] = []

    def invoke(self, messages: list[dict[str, str]]):
        self.calls.append(messages)
        if self._queue is not None:
            if not self._queue:
                raise AssertionError("FakeLLM queue исчеркана")
            current = self._queue.pop(0)
            text = current if isinstance(current, str) else json.dumps(current, ensure_ascii=False)
        elif callable(self.payload):
            text = self.payload(messages)
        elif isinstance(self.payload, str):
            text = self.payload
        else:
            text = json.dumps(self.payload, ensure_ascii=False)

        class _Resp:
            def __init__(self, content: str):
                self.content = content

        return _Resp(text)


class FakeSearcher:
    def __init__(
        self,
        web: list[SearchHit] | None = None,
        images: list[SearchHit] | None = None,
    ):
        self.web = web or []
        self.images = images or []
        self.web_queries: list[str] = []
        self.image_queries: list[str] = []

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        self.web_queries.append(query)
        return self.web[:max_results]

    def search_images(self, query: str, *, max_results: int = 8) -> list[SearchHit]:
        self.image_queries.append(query)
        return self.images[:max_results]

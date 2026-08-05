"""Веб/картиночный поиск — подключаемые клиенты (Brave при наличии ключа)."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "in",
    "on",
    "to",
    "for",
    "with",
    "как",
    "что",
    "это",
    "для",
    "при",
    "без",
}


@dataclass
class SearchHit:
    url: str
    title: str = ""
    snippet: str = ""


class WebSearcher(Protocol):
    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]: ...


class ImageSearcher(Protocol):
    def search_images(self, query: str, *, max_results: int = 8) -> list[SearchHit]: ...


def tokenize_query(query: str) -> set[str]:
    parts = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", query.lower())
    return {p for p in parts if p not in _STOP}


def soft_metadata_match(query: str, title: str, description: str) -> bool:
    """Критерий C2: описание/метаданные ≈ запрос (пересечение токенов)."""
    q = tokenize_query(query)
    if not q:
        return False
    hay = tokenize_query(f"{title} {description}")
    return bool(q & hay)


class NullSearcher:
    """Пустой поиск — для офлайна / когда нет API-ключа."""

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        logger.warning("NullSearcher: web search skipped for %r", query)
        return []

    def search_images(self, query: str, *, max_results: int = 8) -> list[SearchHit]:
        logger.warning("NullSearcher: image search skipped for %r", query)
        return []


class BraveSearcher:
    """Brave Search API (web + images). Требует BRAVE_API_KEY."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("BRAVE_API_KEY", "")

    def _get(self, url: str) -> dict:
        import json

        req = Request(
            url,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
                "User-Agent": "edit-pipeline/0.2",
            },
        )
        with urlopen(req, timeout=20) as resp:  # noqa: S310 — контролируемый API Brave
            return json.loads(resp.read().decode("utf-8"))

    def search(self, query: str, *, max_results: int = 5) -> list[SearchHit]:
        if not self.api_key:
            return NullSearcher().search(query, max_results=max_results)
        url = (
            "https://api.search.brave.com/res/v1/web/search"
            f"?q={quote_plus(query)}&count={max_results}"
        )
        data = self._get(url)
        hits: list[SearchHit] = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            hits.append(
                SearchHit(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("description", ""),
                )
            )
        return hits

    def search_images(self, query: str, *, max_results: int = 8) -> list[SearchHit]:
        if not self.api_key:
            return NullSearcher().search_images(query, max_results=max_results)
        url = (
            "https://api.search.brave.com/res/v1/images/search"
            f"?q={quote_plus(query)}&count={max_results}"
        )
        data = self._get(url)
        hits: list[SearchHit] = []
        for item in data.get("results", [])[:max_results]:
            props = item.get("properties") or {}
            hits.append(
                SearchHit(
                    url=props.get("url") or item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("description") or props.get("alt", "") or "",
                )
            )
        return hits


def default_searcher() -> BraveSearcher:
    return BraveSearcher()

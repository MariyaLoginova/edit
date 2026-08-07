"""B1 EDIT-B1: гейты и пакетный скоринг виральности тем."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from edit.audience import load_audience
from edit.config import ROOT
from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_personal_story_model
from models import AxisScore, ScoredTopic, TopicCandidate

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "b1_topic_scoring.txt"
_UNIVERSAL = re.compile(r"(?i)\b(любой|все|всегда|каждый)\b")
_AXES = (
    "showable",
    "surprise",
    "recognizable",
    "social_currency",
    "arguable",
    "supersystem",
)


def _config() -> dict:
    data = yaml.safe_load((ROOT / "config" / "thresholds.yaml").read_text(encoding="utf-8")) or {}
    return data.get("topic_scoring") or {}


def _axis(value: int, why: str) -> AxisScore:
    return AxisScore(value=value, why=why)


def gate_topic(
    topic: TopicCandidate, *, produced_topic_ids: set[str] | None = None
) -> list[str]:
    """Дешёвые, объяснимые отсевы до LLM-вызова."""
    failures: list[str] = []
    if not topic.source_conclusion_quote.strip():
        failures.append("нет дословного вывода автора в источнике")
    minimum = 6 if topic.format == "excursion" else 3
    if len(topic.visual_examples) < minimum:
        failures.append(
            f"нечего показать: {len(topic.visual_examples)}<{minimum} визуальных экземпляров"
        )
    if _UNIVERSAL.search(topic.one_line):
        failures.append("универсальная формулировка: любой/все/всегда/каждый")
    if topic.topic_id in (produced_topic_ids or set()):
        failures.append("дубль уже выпущенной темы")
    return failures


def _drop(topic: TopicCandidate, failures: list[str]) -> ScoredTopic:
    axis = _axis(1, "Не оценивалось: тема не прошла гейт.")
    return ScoredTopic(
        topic_id=topic.topic_id,
        gates_passed=False,
        gate_failures=failures,
        showable=axis,
        surprise=axis,
        recognizable=axis,
        social_currency=axis,
        arguable=axis,
        supersystem=axis,
        total=0.0,
        verdict="drop",
        one_line=topic.one_line,
    )


def _total(item: ScoredTopic, weights: dict[str, float]) -> float:
    numerator = sum(
        getattr(item, axis).value * float(weights.get(axis, 1.0)) for axis in _AXES
    )
    denominator = sum(abs(float(weights.get(axis, 1.0))) for axis in _AXES) or 1.0
    return round(numerator / denominator, 3)


def score_topics(
    topics: list[TopicCandidate],
    *,
    produced_topic_ids: set[str] | None = None,
    llm: ChatModel | None = None,
) -> list[ScoredTopic]:
    """Один LLM-вызов на всю пачку прошедших гейты тем."""
    dropped: list[ScoredTopic] = []
    accepted: list[TopicCandidate] = []
    for topic in topics:
        failures = gate_topic(topic, produced_topic_ids=produced_topic_ids)
        if failures:
            dropped.append(_drop(topic, failures))
        else:
            accepted.append(topic)
    if not accepted:
        return dropped

    cfg = _config()
    model = llm or get_personal_story_model(temperature=0.0)
    raw = parse_json_payload(
        content_text(
            model.invoke(
                [
                    {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
                    {
                        "role": "user",
                        "content": str(
                            {
                                "audience": load_audience(),
                                "topics": [topic.model_dump(mode="json") for topic in accepted],
                                "metrics_map": {
                                    "showable": "middle retention",
                                    "surprise": "3-second retention",
                                    "recognizable": "early retention / reach",
                                    "social_currency": "shares and saves",
                                    "arguable": "comments",
                                    "supersystem": "reach outside core",
                                },
                            }
                        ),
                    },
                ]
            )
        )
    )
    if isinstance(raw, dict):
        raw = raw.get("topics") or raw.get("scored_topics") or []
    if not isinstance(raw, list):
        raise ValueError("B1 topics: ожидался JSON-массив")
    by_id = {topic.topic_id: topic for topic in accepted}
    weights = {str(k): float(v) for k, v in (cfg.get("weights") or {}).items()}
    min_axis = int(cfg.get("min_axis_for_production", 2))
    produce_threshold = float(cfg.get("produce_threshold", 3.4))
    scored: list[ScoredTopic] = []
    for item in raw:
        if not isinstance(item, dict) or item.get("topic_id") not in by_id:
            continue
        topic = by_id.pop(item["topic_id"])
        candidate = ScoredTopic(
            topic_id=topic.topic_id,
            gates_passed=True,
            gate_failures=[],
            **{axis: item.get(axis) for axis in _AXES},
            total=0.0,
            verdict="bank",
            one_line=topic.one_line,
        )
        total = _total(candidate, weights)
        low_axis = any(getattr(candidate, axis).value < min_axis for axis in _AXES)
        verdict = "produce" if total >= produce_threshold and not low_axis else "bank"
        scored.append(candidate.model_copy(update={"total": total, "verdict": verdict}))
    # Нет ответа на тему — не производить молча.
    for topic in by_id.values():
        dropped.append(_drop(topic, ["скорер не вернул оценку темы"]))
    return sorted([*scored, *dropped], key=lambda x: (-x.total, x.topic_id))


def append_topic_bank(path: Path, topics: list[ScoredTopic]) -> None:
    """Не терять bank/drop темы: простой человекочитаемый журнал."""
    rejected = [item for item in topics if item.verdict != "produce"]
    if not rejected:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Банк тем B1\n"
    additions = []
    for item in rejected:
        marker = f"## {item.topic_id}"
        if marker in existing:
            continue
        reason = "; ".join(item.gate_failures) or "ось ниже порога / низкая сумма"
        additions.append(f"\n{marker}\n\n{item.one_line}\n\n**B1:** {item.verdict} · {reason}\n")
    if additions:
        path.write_text(existing.rstrip() + "\n" + "".join(additions), encoding="utf-8")

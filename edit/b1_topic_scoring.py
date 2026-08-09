"""B1 EDIT-B1: гейты и пакетный скоринг виральности тем."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from edit.audience import load_audience
from edit.config import ROOT
from edit.llm import ChatModel, content_text, parse_json_payload
from edit.model_routing import get_personal_story_model
from models import AxisScore, ClaimCard, ScoredTopic, TopicCandidate

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


def claim_to_topic_candidate(
    claim: ClaimCard,
    *,
    format: str = "narrative",
) -> TopicCandidate:
    """A2 ClaimCard → TopicCandidate для первого прохода по книге."""
    visuals: list[str] = []
    for item in (
        claim.visual_hint,
        claim.object_anchor,
        claim.contrast_pair.state_a,
        claim.contrast_pair.state_b,
    ):
        text = (item or "").strip()
        if text and text not in visuals:
            visuals.append(text)
    return TopicCandidate(
        topic_id=claim.claim_id,
        one_line=claim.claim,
        naive_expectation=claim.counter_expectation,
        source_conclusion_quote=claim.citation.quote,
        visual_examples=visuals[:12],
        format=format if format in {"excursion", "narrative", "argument"} else "narrative",
        source_locator=claim.citation.locator,
    )


def claims_to_topic_candidates(
    claims: list[ClaimCard],
    *,
    format: str = "narrative",
) -> list[TopicCandidate]:
    return [claim_to_topic_candidate(claim, format=format) for claim in claims]


def gate_topic(
    topic: TopicCandidate, *, produced_topic_ids: set[str] | None = None
) -> list[str]:
    """Дешёвые отсевы до LLM. Авторская цитата и визуалы не гейтят."""
    failures: list[str] = []
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


def _score_accepted_batch(
    accepted: list[TopicCandidate],
    *,
    llm: ChatModel,
    cfg: dict,
) -> list[ScoredTopic]:
    raw = parse_json_payload(
        content_text(
            llm.invoke(
                [
                    {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8").strip()},
                    {
                        "role": "user",
                        "content": str(
                            {
                                "audience": load_audience(),
                                "topics": [topic.model_dump(mode="json") for topic in accepted],
                                "metrics_map": {
                                    "social_currency": "shares / saves / forward to colleague",
                                    "surprise": "unusual fact vs naive expectation",
                                    "recognizable": "early retention / reach",
                                    "arguable": "comments",
                                    "supersystem": "reach outside core",
                                    "showable": "optional visual richness (secondary)",
                                },
                                "priority": [
                                    "social_currency",
                                    "surprise",
                                    "recognizable",
                                    "arguable",
                                    "supersystem",
                                    "showable",
                                ],
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
    soft_axes = {str(x) for x in (cfg.get("soft_axes") or ["showable"])}
    produce_threshold = float(cfg.get("produce_threshold", 3.4))
    scored: list[ScoredTopic] = []
    dropped: list[ScoredTopic] = []
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
        hard_axes = [axis for axis in _AXES if axis not in soft_axes]
        low_axis = any(getattr(candidate, axis).value < min_axis for axis in hard_axes)
        verdict = "produce" if total >= produce_threshold and not low_axis else "bank"
        scored.append(candidate.model_copy(update={"total": total, "verdict": verdict}))
    for topic in by_id.values():
        dropped.append(_drop(topic, ["скорер не вернул оценку темы"]))
    return [*scored, *dropped]


def score_topics(
    topics: list[TopicCandidate],
    *,
    produced_topic_ids: set[str] | None = None,
    llm: ChatModel | None = None,
    batch_size: int | None = None,
) -> list[ScoredTopic]:
    """Пакетный скоринг: LLM-вызовы чанками (книга → много тем)."""
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
    size = int(batch_size or cfg.get("batch_size") or 20)
    size = max(1, size)
    scored: list[ScoredTopic] = []
    for i in range(0, len(accepted), size):
        chunk = accepted[i : i + size]
        scored.extend(_score_accepted_batch(chunk, llm=model, cfg=cfg))
    return sorted([*scored, *dropped], key=lambda x: (-x.total, x.topic_id))


def score_mined_claims(
    claims: list[ClaimCard],
    *,
    format: str = "narrative",
    produced_topic_ids: set[str] | None = None,
    llm: ChatModel | None = None,
) -> list[ScoredTopic]:
    """Первый проход: A2-карточки сразу получают оценку привлекательности."""
    return score_topics(
        claims_to_topic_candidates(claims, format=format),
        produced_topic_ids=produced_topic_ids,
        llm=llm,
    )


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

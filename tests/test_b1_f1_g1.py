from __future__ import annotations

from pathlib import Path

import yaml

from edit.b1_scoring import score_claims
from edit.config import clear_thresholds_cache, scoring_weights
from edit.f1_shotlist import build_shotlist
from edit.g1_post_analyst import analyze_rollouts, apply_weight_update
from edit.search import SearchHit
from models import (
    Citation,
    ClaimCard,
    Dossier,
    RolloutMetrics,
    ScriptDraft,
    ScriptLine,
)
from tests.claim_factory import make_claim, make_frozen_dossier
from tests.fakes import FakeSearcher


def _card(**overrides) -> ClaimCard:
    return make_claim(**overrides)


def _dossier(card: ClaimCard | None = None) -> Dossier:
    return make_frozen_dossier(card or _card())


def _script(claim_id: str = "lbd-maintenance-not-luxury") -> ScriptDraft:
    return ScriptDraft(
        script_id="s1",
        claim_id=claim_id,
        duration_sec=20,
        lines=[
            ScriptLine(t_start=0, t_end=5, text="Не роскошь, а отсутствие горничной.", claim_id=claim_id),
            ScriptLine(t_start=5, t_end=12, text="Платье почти не требовало ухода.", claim_id=claim_id),
            ScriptLine(t_start=12, t_end=20, text="Формула: статус маскирует сервис.", claim_id=claim_id),
        ],
    )


def test_b1_scores_and_ranks():
    weak = _card(
        claim_id="weak",
        claim="Форма была новой",
        counter_expectation="ок",
        visual_hint="форма",
        confidence=0.2,
        citation=Citation(locator="x", quote="short"),
    )
    strong = _card()
    ranked = score_claims([weak, strong])
    assert ranked[0].rank == 1
    assert ranked[0].claim.claim_id == "lbd-maintenance-not-luxury"
    assert set(ranked[0].scores) == {
        "surprise",
        "specificity",
        "causal_clarity",
        "evidence",
        "shareability",
    }
    assert ranked[0].total >= ranked[1].total


def test_f1_builds_packet_per_line():
    searcher = FakeSearcher(
        images=[
            SearchHit(
                url="https://img/ex1.jpg",
                title="Chanel little black dress Vogue 1926",
                snippet="archive plate",
            ),
            SearchHit(url="https://img/ex2.jpg", title="cat", snippet="pet"),
        ]
    )
    shot_list = build_shotlist(_script(), _dossier(), searcher=searcher)
    assert len(shot_list.shots) == 3
    assert all(len(s.images) >= 1 for s in shot_list.shots)
    assert shot_list.shots[0].images[0].soft_match is True
    assert "вручную" in shot_list.note.lower() or "монтаж" in shot_list.note.lower()


def test_g1_raises_surprise_on_early_dropoff():
    clear_thresholds_cache()
    before = scoring_weights()
    metrics = [
        RolloutMetrics(
            script_id=f"s{i}",
            claim_id="c",
            avg_watch_pct=0.5,
            dropoff_3s=0.5,
            shares=10,
            saves=10,
            e2_dropoff_score=20,
        )
        for i in range(3)
    ]
    update = analyze_rollouts(metrics)
    assert update.hypothesis is True
    assert update.scoring_weights.surprise > before.surprise
    assert "surprise" in update.notes.lower() or "отвал" in update.notes.lower()


def test_g1_suggests_stricter_e2_threshold():
    metrics = [
        RolloutMetrics(
            script_id="s1",
            claim_id="c",
            avg_watch_pct=0.3,
            dropoff_3s=0.2,
            shares=1,
            saves=1,
            e2_dropoff_score=10,  # E2 сказал «ок», факт — плохо
        )
    ]
    update = analyze_rollouts(metrics)
    assert update.dropoff_score_threshold is not None
    assert update.dropoff_score_threshold < 40


def test_g1_persist_to_temp_yaml(tmp_path: Path):
    clear_thresholds_cache()
    src = Path("config/thresholds.yaml").read_text(encoding="utf-8")
    target = tmp_path / "thresholds.yaml"
    target.write_text(src, encoding="utf-8")
    # point loader via apply with path
    metrics = [
        RolloutMetrics(
            script_id="s1",
            claim_id="c",
            avg_watch_pct=0.2,
            dropoff_3s=0.5,
            shares=60,
            saves=40,
        )
    ]
    update = analyze_rollouts(metrics)
    data = apply_weight_update(update, path=target, persist=True)
    written = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert written["scoring"]["weights"]["shareability"] == data["scoring"]["weights"]["shareability"]
    clear_thresholds_cache()

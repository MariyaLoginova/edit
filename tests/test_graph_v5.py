from __future__ import annotations

from edit.graph import build_f1_only_graph, build_learning_graph
from edit.search import SearchHit
from models import (
    Citation,
    ClaimCard,
    ClaimKind,
    Dossier,
    RolloutMetrics,
    Scope,
    ScriptDraft,
    ScriptLine,
    SoftFactcheckResult,
)
from tests.fakes import FakeSearcher


def test_f1_only_graph():
    claim = ClaimCard(
        claim_id="lbd-maintenance-not-luxury",
        kind=ClaimKind.causal,
        claim="Маленькое чёрное взлетело из-за ухода",
        counter_expectation="Думают про роскошь",
        visual_hint="Chanel LBD Vogue 1926",
        citation=Citation(locator="гл.2", quote="required almost no maintenance"),
        scope=Scope(period="1920s", author_or_work="Chanel"),
        source_segment_id="ch2",
        confidence=0.9,
    )
    dossier = Dossier(
        claim_id=claim.claim_id,
        claim=claim,
        soft_factcheck=SoftFactcheckResult(ok=True, rationale="ok"),
    ).freeze()
    script = ScriptDraft(
        script_id="s1",
        claim_id=claim.claim_id,
        duration_sec=10,
        lines=[
            ScriptLine(t_start=0, t_end=5, text="Не роскошь.", claim_id=claim.claim_id),
            ScriptLine(t_start=5, t_end=10, text="Уход.", claim_id=claim.claim_id),
        ],
    )
    searcher = FakeSearcher(
        images=[
            SearchHit(
                url="https://img/a.jpg",
                title="Chanel LBD Vogue 1926",
                snippet="dress",
            )
        ]
    )
    out = build_f1_only_graph(searcher=searcher).invoke(
        {"script": script, "dossier": dossier}
    )
    assert len(out["shot_list"].shots) == 2


def test_learning_graph_updates_weights():
    out = build_learning_graph(persist=False).invoke(
        {
            "rollout_metrics": [
                RolloutMetrics(
                    script_id="s1",
                    claim_id="c",
                    avg_watch_pct=0.3,
                    dropoff_3s=0.5,
                    shares=80,
                    saves=40,
                )
            ]
        }
    )
    assert out["weight_update"].n_rollouts_seen == 1
    assert out["weight_update"].hypothesis is True
    assert out["weight_update"].scoring_weights.shareability >= 1.0

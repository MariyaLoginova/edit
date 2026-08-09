from __future__ import annotations

from edit.graph import build_f1_only_graph, build_learning_graph
from models import RolloutMetrics, ScriptDraft, ScriptLine
from tests.claim_factory import abundant_searcher, make_frozen_dossier
from tests.fakes import FakeSearcher


def test_f1_only_graph():
    dossier = make_frozen_dossier()
    claim = dossier.claim
    script = ScriptDraft(
        script_id="s1",
        claim_id=claim.claim_id,
        duration_sec=10,
        lines=[
            ScriptLine(t_start=0, t_end=5, text="Не роскошь.", claim_id=claim.claim_id),
            ScriptLine(t_start=5, t_end=10, text="Уход.", claim_id=claim.claim_id),
        ],
    )
    searcher = abundant_searcher()
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

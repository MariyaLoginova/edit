from __future__ import annotations

from edit.c1_research_enricher import enrich_material
from models import Dossier, SoftFactcheckResult, WebConfirmation
from tests.brief_factory import make_argument_brief
from tests.claim_factory import make_claim
from tests.fakes import FakeLLM


def _dossier(**overrides) -> Dossier:
    claim = make_claim(claim_id="black-underwear-shift")
    data = dict(
        claim_id=claim.claim_id,
        claim=claim,
        material_notes=(
            "В 1960-е чёрное бельё обогнало белое. Реклама спрашивала: "
            "«Скажи мне, какого цвета белье...»"
        ),
        web_confirmations=[],
        soft_factcheck=SoftFactcheckResult(ok=True, rationale="ok"),
    )
    data.update(overrides)
    return Dossier(**data)


def test_enrich_keeps_https_facts_from_search(monkeypatch):
    monkeypatch.setattr(
        "edit.c1_research_enricher._research_settings",
        lambda: (True, 360.0),
    )
    llm = FakeLLM(
        {
            "claim_id": "black-underwear-shift",
            "facts": [
                {
                    "fact": "В Европе чёрный нейлон в белье массово вошёл в 1960-е.",
                    "source_url": "https://example.com/lingerie-1960s",
                    "source_title": "Archive",
                    "why_it_matters": "Внешнее подтверждение сдвига.",
                },
                {
                    "fact": "Выдуманный local не должен пройти в web-режиме.",
                    "source_url": "local://primary",
                    "source_title": "Nope",
                    "why_it_matters": "Это пересказ.",
                },
            ],
            "gaps": ["black lingerie advertising 1960 Europe"],
            "summary": "Нашла внешний материал про нейлон 1960-х.",
        }
    )
    brief = make_argument_brief(claim_id="black-underwear-shift")
    dossier, pack = enrich_material(_dossier(), brief, llm=llm)

    assert len(llm.calls) == 1
    assert llm.kwargs_list[0].get("tools")
    assert [f.source_url for f in pack.facts] == ["https://example.com/lingerie-1960s"]
    assert "ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРЯЕМЫЕ ФАКТЫ (web)" in dossier.material_notes


def test_enrich_repairs_when_no_https_facts(monkeypatch):
    monkeypatch.setattr(
        "edit.c1_research_enricher._research_settings",
        lambda: (True, 360.0),
    )
    llm = FakeLLM(
        queue=[
            {
                "claim_id": "black-underwear-shift",
                "facts": [],
                "gaps": ["lingerie ads 1960"],
                "summary": "Нужен поиск.",
            },
            {
                "claim_id": "black-underwear-shift",
                "facts": [
                    {
                        "fact": "Каталоги 1960-х показывают рост чёрного ассортимента.",
                        "source_url": "https://example.com/catalogs",
                        "source_title": "Catalogs",
                        "why_it_matters": "Визуальный proof.",
                    }
                ],
                "gaps": ["lingerie ads 1960"],
                "summary": "Нашла каталоги.",
            },
        ]
    )
    brief = make_argument_brief(claim_id="black-underwear-shift")
    _, pack = enrich_material(_dossier(), brief, llm=llm)
    assert len(llm.calls) == 2
    assert len(pack.facts) == 1


def test_enrich_keeps_more_than_eight_https_facts(monkeypatch):
    monkeypatch.setattr(
        "edit.c1_research_enricher._research_settings",
        lambda: (True, 360.0),
    )
    facts = [
        {
            "fact": f"Внешний факт {i} про цвет белья.",
            "source_url": f"https://example.com/f{i}",
            "source_title": "Web",
            "why_it_matters": "Усиливает историю сдвига.",
        }
        for i in range(1, 12)
    ]
    llm = FakeLLM(
        {
            "claim_id": "black-underwear-shift",
            "facts": facts,
            "gaps": [],
            "summary": "Много внешних деталей.",
        }
    )
    brief = make_argument_brief(claim_id="black-underwear-shift")
    _, pack = enrich_material(_dossier(), brief, llm=llm)
    assert len(pack.facts) == 11


def test_enrich_compresses_gap_dicts_to_short_queries(monkeypatch):
    monkeypatch.setattr(
        "edit.c1_research_enricher._research_settings",
        lambda: (True, 360.0),
    )
    llm = FakeLLM(
        {
            "claim_id": "black-underwear-shift",
            "facts": [
                {
                    "fact": "Хотя бы один https факт.",
                    "source_url": "https://example.com/x",
                    "source_title": "X",
                    "why_it_matters": "ok",
                }
            ],
            "gaps": [
                {
                    "topic": "патенты красителей",
                    "why_needed": "длинное эссе...",
                    "query": "synthetic black dye nylon patent 1960",
                }
            ],
            "summary": "ok",
        }
    )
    brief = make_argument_brief(claim_id="black-underwear-shift")
    _, pack = enrich_material(_dossier(), brief, llm=llm)
    assert pack.gaps == ["synthetic black dye nylon patent 1960"]

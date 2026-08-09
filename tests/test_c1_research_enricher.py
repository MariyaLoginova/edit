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


def test_enrich_keeps_primary_facts_without_web():
    llm = FakeLLM(
        {
            "claim_id": "black-underwear-shift",
            "facts": [
                {
                    "fact": "В 1960-е чёрное бельё обогнало белое.",
                    "source_url": "local://primary",
                    "source_title": "Пастуро",
                    "why_it_matters": "Сдвиг нормы — ядро ролика.",
                }
            ],
            "gaps": ["black lingerie advertising 1960s Europe"],
            "summary": "Из текста вытащила смену нормы; внешний поиск — уточнить рекламу.",
        }
    )
    brief = make_argument_brief(claim_id="black-underwear-shift")
    dossier, pack = enrich_material(_dossier(), brief, llm=llm)

    assert len(llm.calls) == 1
    assert len(pack.facts) == 1
    assert pack.facts[0].source_url == "local://primary"
    assert "ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРЯЕМЫЕ ФАКТЫ" in dossier.material_notes
    assert pack.gaps == ["black lingerie advertising 1960s Europe"]


def test_enrich_keeps_web_facts_and_drops_unknown_urls():
    llm = FakeLLM(
        {
            "claim_id": "black-underwear-shift",
            "facts": [
                {
                    "fact": "Внешний нюанс про красители.",
                    "source_url": "https://example.com/dye",
                    "source_title": "Archive",
                    "why_it_matters": "Практическая причина стойкости.",
                },
                {
                    "fact": "Выдуманный URL не должен пройти.",
                    "source_url": "https://evil.example/nope",
                    "source_title": "Nope",
                    "why_it_matters": "Нельзя.",
                },
            ],
            "gaps": [],
            "summary": "Добавила внешний факт по allowlist.",
        }
    )
    dossier = _dossier(
        web_confirmations=[
            WebConfirmation(
                url="https://example.com/dye",
                title="Archive",
                snippet="dye",
                query="black dye",
                supports_claim=True,
            )
        ]
    )
    brief = make_argument_brief(claim_id="black-underwear-shift")
    _, pack = enrich_material(dossier, brief, llm=llm)
    assert [f.source_url for f in pack.facts] == ["https://example.com/dye"]


def test_enrich_compresses_gap_dicts_to_short_queries():
    llm = FakeLLM(
        {
            "claim_id": "black-underwear-shift",
            "facts": [],
            "gaps": [
                {
                    "topic": "патенты красителей",
                    "why_needed": "длинное эссе про отсутствие данных...",
                    "query": "synthetic black dye nylon patent 1960",
                }
            ],
            "summary": "Нужен точечный поиск.",
        }
    )
    brief = make_argument_brief(claim_id="black-underwear-shift")
    _, pack = enrich_material(_dossier(), brief, llm=llm)
    assert pack.gaps == ["synthetic black dye nylon patent 1960"]

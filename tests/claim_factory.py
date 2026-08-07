"""Фабрика узких ClaimCard (FIX-1) для тестов."""

from __future__ import annotations

from models import ClaimCard, ClaimKind, Citation, ContrastPair, Scope


def make_claim(**overrides) -> ClaimCard:
    data = {
        "claim_id": "lbd-maintenance-not-luxury",
        "kind": ClaimKind.causal,
        "claim": (
            "Little black dress взлетел как готовое решение для женщины без горничной, "
            "а не как символ вневременной роскоши."
        ),
        "counter_expectation": "Считают, что LBD — про вневременную элегантность и статус",
        "visual_hint": "Chanel little black dress, реклама Vogue 1926",
        "object_anchor": "little black dress Chanel",
        "contrast_pair": ContrastPair(
            state_a="пастельное платье салона, требующее ухода",
            state_b="чёрное прямое платье для городской коммютерши",
            shift="статус сменяется сервисом и воспроизводимостью",
        ),
        "mechanism_term": "сервис-вместо-статуса",
        "mechanism_explain": (
            "Прямой крой и чёрный цвет маскируют износ и упрощают фабричный пошив — "
            "платье работает как инфраструктура дня."
        ),
        "citation": Citation(
            locator="гл. 2, с. 61–63",
            quote="required almost no maintenance and looked correct from morning errands to evening",
        ),
        "scope": Scope(period="1920s", region="Paris", author_or_work="Chanel"),
        "source_segment_id": "ch2-s1",
        "confidence": 0.85,
    }
    data.update(overrides)
    if isinstance(data.get("citation"), dict):
        data["citation"] = Citation(**data["citation"])
    if isinstance(data.get("scope"), dict):
        data["scope"] = Scope(**data["scope"])
    if isinstance(data.get("contrast_pair"), dict):
        data["contrast_pair"] = ContrastPair(**data["contrast_pair"])
    return ClaimCard(**data)


def make_images_for(claim: ClaimCard, n: int = 3):
    from models import ImageBuckets, ImageCandidate

    pair = claim.contrast_pair

    def pack(state: str, query: str):
        return [
            ImageCandidate(
                url=f"https://img.example/{state}{i}.jpg",
                title=query,
                description=query,
                query=query,
                soft_match=True,
                for_state=state,  # type: ignore[arg-type]
            )
            for i in range(n)
        ]

    return ImageBuckets(
        for_state_a=pack("a", pair.state_a),
        for_state_b=pack("b", pair.state_b),
        search_status="ok",
    )


def make_frozen_dossier(claim: ClaimCard | None = None, **overrides):
    from models import Dossier, SoftFactcheckResult, WebConfirmation

    claim = claim or make_claim()
    data = {
        "claim_id": claim.claim_id,
        "claim": claim,
        "material_notes": "material notes for tests",
        "web_confirmations": [
            WebConfirmation(
                url="https://example.com/x",
                title="support",
                snippet=claim.citation.quote[:80],
                query=claim.claim,
                supports_claim=True,
            )
        ],
        "image_candidates": make_images_for(claim),
        "soft_factcheck": SoftFactcheckResult(ok=True, rationale="ok"),
    }
    data.update(overrides)
    return Dossier(**data).freeze()


def abundant_searcher():
    """FakeSearcher с картинками под любой запрос (для C2 A/B)."""
    from edit.search import SearchHit
    from tests.fakes import FakeSearcher

    imgs = [
        SearchHit(url=f"https://img.example/{i}.jpg", title="little black dress кот", snippet="визуал объект")
        for i in range(8)
    ]
    web = [
        SearchHit(
            url="https://example.com/a",
            title="support",
            snippet="required almost no maintenance",
        )
    ]
    return FakeSearcher(web=web, images=imgs)


def make_countability_claim() -> ClaimCard:
    return make_claim(
        claim_id="cats-countability-flip",
        claim=(
            "Один кот на улице умиляет, а пятьдесят тех же котов включают тревогу — "
            "счётность переворачивает милоту."
        ),
        counter_expectation="Чем больше милых котов, тем сильнее умиление.",
        visual_hint="один кот vs толпа котов на улице",
        object_anchor="коты на улице",
        contrast_pair=ContrastPair(
            state_a="один кот остановился и смотрит",
            state_b="пятьдесят котов стоят и смотрят",
            shift="милота сменяется ощущением хищной массы",
        ),
        mechanism_term="счётность",
        mechanism_explain=(
            "При росте количества тот же педоморфный силуэт перестаёт читаться как "
            "детёныш и начинает читаться как стая."
        ),
        citation=Citation(
            locator="seg-7",
            quote="Пятьдесят — ты останавливаешься и не знаешь, как идти дальше",
        ),
        scope=Scope(),
        source_segment_id="goralik-mimimi-0006",
        confidence=0.9,
    )

import pytest
from pydantic import ValidationError

from models import ClaimCard, ClaimKind, Citation, Scope


def _valid_kwargs(**overrides):
    data = {
        "claim_id": "bauhaus-sans-serif-cost",
        "kind": ClaimKind.causal,
        "claim": "Гротеск выбрали, потому что набор стоил дешевле антиквы",
        "counter_expectation": "Считают, что гротеск выбрали ради «современности»",
        "visual_hint": "Прайс-лист наборной кассы Bauhaus, 1925",
        "citation": Citation(
            locator="гл. 3, с. 44",
            quote="sans-serif type was cheaper to set than roman",
        ),
        "scope": Scope(period="1920s", region="Germany", author_or_work="Bauhaus"),
        "source_segment_id": "ch3-p44",
        "confidence": 0.8,
    }
    data.update(overrides)
    return data


def test_valid_claim_card():
    card = ClaimCard(**_valid_kwargs())
    assert card.claim_id == "bauhaus-sans-serif-cost"
    assert card.kind is ClaimKind.causal


def test_compound_claim_rejected():
    with pytest.raises(ValidationError):
        ClaimCard(**_valid_kwargs(claim="Первая причина и вторая причина сразу"))


def test_missing_counter_expectation_rejected():
    data = _valid_kwargs()
    del data["counter_expectation"]
    with pytest.raises(ValidationError):
        ClaimCard(**data)


def test_descriptive_kind_not_in_enum():
    with pytest.raises(ValidationError):
        ClaimCard(**_valid_kwargs(kind="descriptive"))

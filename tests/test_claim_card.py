import pytest
from pydantic import ValidationError

from models import ClaimCard, ClaimKind
from tests.claim_factory import make_claim


def test_valid_claim_card():
    card = make_claim()
    assert card.claim_id == "lbd-maintenance-not-luxury"
    assert card.kind is ClaimKind.causal
    assert card.contrast_pair.state_a != card.contrast_pair.state_b
    assert card.mechanism_term


def test_compound_claim_rejected():
    with pytest.raises(ValidationError):
        make_claim(claim="Первая причина; вторая причина сразу")
    card = make_claim(claim="Чёрный маскировал пятна и износ лучше пастели little black")
    assert "и" in card.claim


def test_universal_law_rejected():
    with pytest.raises(ValidationError, match="универсальный закон"):
        make_claim(
            claim="Любой милый объект воспринимается как неизбежно хрупкий",
            object_anchor="милый объект",
            visual_hint="милый объект",
        )


def test_missing_contrast_rejected():
    data = make_claim().model_dump()
    del data["contrast_pair"]
    with pytest.raises(ValidationError):
        ClaimCard(**data)


def test_missing_counter_expectation_rejected():
    data = make_claim().model_dump()
    del data["counter_expectation"]
    with pytest.raises(ValidationError):
        ClaimCard(**data)


def test_descriptive_kind_not_in_enum():
    with pytest.raises(ValidationError):
        make_claim(kind="descriptive")

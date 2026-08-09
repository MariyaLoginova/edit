"""EDIT-A2 · ClaimCard — узкий причинный тезис с A/B и механизмом (FIX-1)."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class ClaimKind(str, Enum):
    causal = "causal"  # почему визуал такой (ЦЕЛЕВОЙ тип)
    corrective = "corrective"  # распространённое заблуждение опровергается
    origin = "origin"  # откуда взялась форма/приём


class Citation(BaseModel):
    locator: str = Field(..., description="Глава/раздел/страница внутри источника")
    quote: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Дословная цитата из источника, подтверждающая claim. НЕ пересказ.",
    )


class Scope(BaseModel):
    period: str | None = Field(None, description="Год/эпоха, к которым относится тезис")
    region: str | None = Field(None, description="Гео/культурный контекст")
    author_or_work: str | None = Field(
        None, description="Автор, студия, бренд, конкретное произведение"
    )


class ContrastPair(BaseModel):
    """A/B — два состояния ОДНОГО объекта. Каркас средней части ролика."""

    state_a: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Первое состояние/ракурс (напр. 'один кот на улице')",
    )
    state_b: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Второе состояние того же объекта (напр. 'пятьдесят котов')",
    )
    shift: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Что меняется в восприятии между A и B",
    )

    @model_validator(mode="after")
    def _states_differ(self) -> ContrastPair:
        if self.state_a.strip().lower() == self.state_b.strip().lower():
            raise ValueError("contrast_pair: state_a и state_b должны различаться")
        return self


UNIVERSAL_MARKERS = (
    "любой",
    "любая",
    "любое",
    "все ",
    "всякий",
    "всякая",
    "каждый",
    "каждая",
    "вся ",
    "всё ",
    "всегда",
)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", text.lower())}


class ClaimCard(BaseModel):
    claim_id: str = Field(..., description="Стабильный slug, напр. bauhaus-sans-serif-cost")
    kind: ClaimKind

    claim: str = Field(
        ...,
        min_length=1,
        max_length=240,
        description="Одна проверяемая мысль или неожиданный факт. Не универсальный закон.",
    )
    counter_expectation: str = Field(
        ...,
        min_length=1,
        max_length=240,
        description=(
            "Привычная версия истории, которую ломает claim. "
            "Контраст даёт крючок."
        ),
    )
    visual_hint: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Конкретная деталь, персонаж, предмет или ситуация из источника.",
    )
    object_anchor: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description=(
            "Конкретный якорь истории из источника. Это может быть вещь, персонаж, "
            "эпизод или факт — не абстрактная тема."
        ),
    )
    contrast_pair: ContrastPair = Field(
        ...,
        description="Обязательный поворот: до/после, старая/новая версия или два контекста.",
    )
    mechanism_term: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="Короткое имя переноса мысли, которое зритель унесёт.",
    )
    mechanism_explain: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Как работает поворот: через факты, контекст и последствия.",
    )

    citation: Citation
    scope: Scope

    source_segment_id: str = Field(
        ..., description="ID сегмента из source_map, откуда извлечён тезис"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Уверенность майнера, что тезис реально присутствует в сегменте",
    )

    @field_validator("claim")
    @classmethod
    def _single_claim(cls, v: str) -> str:
        lowered = v.lower()
        for sep in ["; ", " а также ", " также ", " и при этом ", " и одновременно "]:
            if sep in lowered:
                raise ValueError(
                    f"claim выглядит составным (найдено '{sep.strip()}'). "
                    "Разбей на отдельные карточки."
                )
        return v

    @field_validator("claim")
    @classmethod
    def _no_universal_law(cls, v: str) -> str:
        low = v.lower()
        for m in UNIVERSAL_MARKERS:
            if m in low:
                raise ValueError(
                    f"claim сформулирован как универсальный закон ('{m.strip()}'). "
                    "Нужен тезис про конкретный объект, а не про класс вещей."
                )
        return v

    @model_validator(mode="after")
    def _anchor_grounded_in_claim(self) -> ClaimCard:
        """Тезис привязан к конкретной детали истории, а не парит над источником."""

        def overlaps(a: str, b: str) -> bool:
            ta, tb = _tokens(a), _tokens(b)
            for x in ta:
                if len(x) < 4:
                    continue
                for y in tb:
                    if len(y) < 4:
                        continue
                    if x == y or x.startswith(y[:4]) or y.startswith(x[:4]):
                        return True
            return False

        if not (
            overlaps(self.object_anchor, self.claim)
            or overlaps(self.visual_hint, self.claim)
        ):
            raise ValueError(
                "object_anchor не отражён в claim — мысль должна быть "
                "привязана к конкретному факту или истории, а не парить над ней"
            )
        return self

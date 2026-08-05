"""EDIT-E2 · RetentionReport — диагностика отвала по секундам."""

from enum import Enum

from pydantic import BaseModel, Field


class DropReason(str, Enum):
    slow_open = "slow_open"  # первые 3 сек без крючка / раскачка
    no_forward = "no_forward"  # нет причины смотреть дальше, «плато»
    front_loaded_payoff = "front_loaded_payoff"  # интрига раскрыта слишком рано
    second_thesis = "second_thesis"  # появился второй тезис — расфокус
    abstract = "abstract"  # ушли в абстракцию без объекта на экране
    filler = "filler"  # вводные слова, «в этом видео мы», связки-пустышки
    unpaid_setup = "unpaid_setup"  # обещание/вопрос без последующего ответа
    flat_ending = "flat_ending"  # кода не сворачивается в цитируемую фразу


class BeatRisk(BaseModel):
    t_start: float = Field(..., ge=0, description="Секунда начала фрагмента")
    t_end: float = Field(..., ge=0, description="Секунда конца фрагмента")
    quote: str = Field(..., min_length=1, description="Кусок сценария, к которому относится риск")
    reason: DropReason
    forward_question: str | None = Field(
        None,
        description=(
            "Какой вопрос держит зрителя на этом фрагменте. None = отвал: держать нечем."
        ),
    )
    severity: int = Field(..., ge=1, le=5, description="1 — придирка, 5 — гарантированный отвал")
    fix_hint: str = Field(
        ...,
        min_length=1,
        description="Что сделать. НЕ переписанный текст — направление для E4/E6.",
    )


class RetentionReport(BaseModel):
    script_id: str
    duration_sec: float

    first3_has_hook: bool = Field(..., description="Есть ли крючок в первые 3 секунды")
    open_strength: int = Field(..., ge=1, le=5, description="Сила открытия")

    risks: list[BeatRisk]

    dropoff_score: int = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Интегральная оценка риска отвала. Выше = хуже. "
            "Порог блокировки задаётся в конфиге."
        ),
    )
    passes: bool = Field(
        ..., description="dropoff_score ниже порога И нет risks с severity>=4"
    )
    summary: str = Field(..., max_length=400, description="Где именно теряем зрителя, 2-3 фразы")

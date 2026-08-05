"""EDIT-E7 · IdeaProbe — маркированный идейный разгон (мнение, не факт)."""

from enum import Enum

from pydantic import BaseModel, Field


class ProbeRegister(str, Enum):
    optic = "optic"  # «что если смотреть так» — рамка
    what_if = "what_if"  # альтернативная история/сценарий
    parallel = "parallel"  # перенос паттерна на сегодняшнее явление


class GenerationBrief(BaseModel):
    """ЗАГЛУШКА НА БУДУЩЕЕ. Пока не используется в продакшене — текстовый разгон.

    Заполняется, но продакшен-слой её игнорирует до отдельного решения по
    генеративному визуалу.
    """

    source_image_hint: str | None = Field(
        None, description="Какой исходник кормить (напр. фото Bild-Lilli)"
    )
    prompt: str | None = Field(None, description="Промпт под генератор (Nano Banana и т.п.)")
    desired_image: str | None = Field(
        None, description="Что должно получиться — образ гипотезы"
    )


class IdeaProbe(BaseModel):
    anchor_claim_id: str = Field(
        ..., description="ОБЯЗАТЕЛЬНО: факт из досье, от которого стартует разгон"
    )
    register: ProbeRegister

    probe_text: str = Field(
        ...,
        min_length=1,
        max_length=400,
        description=(
            "Текст разгона. Сформулирован как вопрос-оптика/гипотеза, "
            "НЕ как утверждение факта."
        ),
    )
    voiced_marker: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description=(
            "Фраза-переключатель регистра в озвучке: 'а если посмотреть так…' и т.п. "
            "Обязательна — именно она отделяет мнение от факта на слух."
        ),
    )

    generation_brief: GenerationBrief | None = Field(
        None,
        description=(
            "Заглушка на будущее. Пока None или заполняется 'в стол' — продакшен игнорирует."
        ),
    )

    proposed: bool = Field(
        True, description="Узел ВСЕГДА предлагает разгон (константа формата)"
    )

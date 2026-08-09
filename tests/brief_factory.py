"""Фабрики StoryBrief для тестов (EDIT-FORM)."""

from __future__ import annotations

from models import (
    Conclusion,
    EndingType,
    Exhibit,
    ProofItem,
    ReelFormat,
    StoryBrief,
)


def make_argument_brief(**overrides) -> StoryBrief:
    source_quotes = ("твидовый костюм", "длинные перчатки", "разноцветных динозавриков")
    base = dict(
        claim_id="x",
        format=ReelFormat.argument,
        main_thought="Костюм показывает разрешённый образ работы.",
        angle="уменьшить до минимума — вся история в перчатках",
        why_viewer="Служебно: про разрешённый силуэт на работе.",
        visual_evidence="твидовый костюм, длинные перчатки и разноцветных динозавриков",
        recommended_method="a_vot_nifiga",
        alternative_methods=[],
        opening="Кадр ломает ожидание.",
        audience_reason="Служебно.",
        share_reason="Есть конкретный образ.",
        proof_plan=[
            ProofItem(point=f"деталь {i}", source_quote=quote)
            for i, quote in enumerate(source_quotes, start=1)
        ],
        exhibits=[],
        conclusion=Conclusion(
            source_quote="твидовый костюм",
            plain="Костюм продаёт не работу, а допустимость.",
        ),
        idea_pitch="Я бы поставила эти костюмы в один ряд.",
        selected_structure="none",
        ending_type=EndingType.formula,
    )
    base.update(overrides)
    return StoryBrief(**base)


def make_excursion_brief(**overrides) -> StoryBrief:
    exhibits = [
        Exhibit(
            name=name,
            what_to_see=see,
            source_quote=quote,
        )
        for name, see, quote in (
            ("Busy Girl", "твидовый костюм и длинные перчатки", "твидовый костюм"),
            ("Army Barbie", "военная форма и знаки различия", "длинные перчатки"),
            ("Палеонтолог", "разноцветные динозаврики вместо пыли", "разноцветных динозавриков"),
            ("Стюардесса", "форма и аккуратная юбка", "твидовый костюм"),
            ("Медсестра", "белый халат без крови", "длинные перчатки"),
            ("Бизнес-леди", "строгий силуэт без кабинета", "разноцветных динозавриков"),
        )
    ]
    base = dict(
        claim_id="x",
        format=ReelFormat.excursion,
        main_thought="Карьерные костюмы Барби — ряд допустимых ролей.",
        angle="уменьшить до минимума — смотрим только костюм",
        why_viewer="Служебно: про чтение визуальных кодов.",
        recommended_method="odna_detal",
        alternative_methods=[],
        opening="Давай просто разложим этих Барби в ряд.",
        exhibits=exhibits,
        proof_plan=[],
        conclusion=Conclusion(
            source_quote="барометром происходящего",
            plain="Роли, которые ей разрешали, показывали, к чему общество уже готово.",
        ),
        idea_pitch="",
        selected_structure="none",
        ending_type=EndingType.reactive,
    )
    base.update(overrides)
    return StoryBrief(**base)

from __future__ import annotations

from edit.d2_monologue import write_monologue
from models import EndingType
from tests.brief_factory import make_argument_brief
from tests.claim_factory import make_frozen_dossier
from tests.fakes import FakeLLM


def test_d2_user_payload_includes_full_structure_example_for_argument():
    dossier = make_frozen_dossier()
    brief = make_argument_brief(
        selected_structure="myth_bust",
        ending_type=EndingType.reactive,
    )
    seen: dict = {}

    def router(messages):
        seen["user"] = messages[1]["content"]
        return ("текст " * 450) + "Спиздели или вдохновились?"

    write_monologue(dossier, brief, hook_text="Кадр ломает ожидание.", llm=FakeLLM(router))
    assert "myth_bust" in seen["user"]
    assert "full_example" in seen["user"]
    assert "Ретроградный Меркурий" in seen["user"]
    # Служебные поля не должны утечь в D2.
    assert "why_viewer" not in seen["user"]
    assert "audience_reason" not in seen["user"]
    assert "share_reason" not in seen["user"]
    assert "idea_pitch" not in seen["user"]
    assert "Кому это интересно" not in seen["user"]


def test_d2_retries_on_service_speech_leak():
    dossier = make_frozen_dossier()
    brief = make_argument_brief()
    calls = 0

    def router(messages):
        nonlocal calls
        calls += 1
        if calls == 1:
            return (
                "Кадр ломает ожидание. "
                + ("деталь " * 450)
                + "Кому это интересно? Всем, кто рисует. Что думаешь?"
            )
        return ("текст " * 450) + "Какая больше нравится?"

    monologue = write_monologue(
        dossier, brief, hook_text="Кадр ломает ожидание.", llm=FakeLLM(router)
    )
    assert "кому это интересно" not in monologue.text.lower()
    assert calls == 2

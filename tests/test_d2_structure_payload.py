from __future__ import annotations

from edit.d2_monologue import write_monologue
from models import EndingType, ProofItem, StoryBrief
from tests.claim_factory import make_frozen_dossier
from tests.fakes import FakeLLM


def test_d2_user_payload_includes_full_structure_example():
    dossier = make_frozen_dossier()
    brief = StoryBrief(
        claim_id="x",
        main_thought="Костюм показывает разрешённый образ работы.",
        visual_evidence="твидовый костюм, длинные перчатки и разноцветных динозавриков",
        recommended_method="a_vot_nifiga",
        alternative_methods=[],
        selected_structure="myth_bust",
        opening="Кадр ломает ожидание.",
        audience_reason="Есть показуемый конфликт.",
        share_reason="Есть конкретный образ.",
        proof_plan=[
            ProofItem(point=f"деталь {i}", source_quote=q)
            for i, q in enumerate(
                ("твидовый костюм", "длинные перчатки", "разноцветных динозавриков"),
                start=1,
            )
        ],
        idea_pitch="Я бы поставила эти костюмы в один ряд.",
        ending_type=EndingType.reactive,
    )
    seen: dict = {}

    def router(messages):
        seen["user"] = messages[1]["content"]
        return ("текст " * 220) + "Спиздели или вдохновились?"

    write_monologue(dossier, brief, hook_text="Кадр ломает ожидание.", llm=FakeLLM(router))
    assert "myth_bust" in seen["user"]
    assert "full_example" in seen["user"]
    assert "Ретроградный Меркурий" in seen["user"]

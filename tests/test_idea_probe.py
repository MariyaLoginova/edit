from models import IdeaProbe, ProbeRegister


def test_idea_probe_requires_anchor():
    probe = IdeaProbe(
        anchor_claim_id="bild-lilli-barbie-prototype",
        register=ProbeRegister.optic,
        probe_text=(
            "Что если читать переиздание старого (сигареты, помада, бельё) "
            "как приём захвата внимания через узнавание?"
        ),
        voiced_marker="а если посмотреть так…",
    )
    assert probe.proposed is True
    assert probe.generation_brief is None
    assert probe.anchor_claim_id.startswith("bild-lilli")

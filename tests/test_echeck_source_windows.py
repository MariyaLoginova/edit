from __future__ import annotations

from edit.e_check import _compose_source_for_check


def test_compose_source_keeps_midchapter_proof_anchors():
    head = "начало главы " * 200
    mid = "Busy Girl Barbie вышла в твидовом костюме."
    tail = " конец " * 200 + "разноцветных динозавриков из земли"
    notes = head + mid + tail
    out = _compose_source_for_check(
        notes,
        ["Busy Girl Barbie вышла в твидовом костюме.", "разноцветных динозавриков"],
        limit=2500,
    )
    assert "Busy Girl Barbie" in out
    assert "разноцветных динозавриков" in out

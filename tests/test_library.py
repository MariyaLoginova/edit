from __future__ import annotations

from edit.library import (
    NONE_ID,
    idea_trigger_menu,
    load_hook_formulas,
    load_idea_triggers,
    load_open_second_triggers,
    normalize_library_id,
)
from edit.e_editor import load_story_methods


def test_idea_triggers_curated_and_menu_has_none():
    items = load_idea_triggers()
    assert len(items) >= 15
    assert all(item.get("id") and item.get("angle") for item in items)
    menu = idea_trigger_menu()
    assert menu[-1]["id"] == NONE_ID


def test_hook_and_open_menus_loaded():
    assert len(load_hook_formulas()) >= 10
    assert len(load_open_second_triggers()) >= 6


def test_story_methods_enriched_with_beats():
    methods = load_story_methods()
    ids = {m["id"] for m in methods}
    assert {"bylo_stalo", "novyy_ya", "vizhu_tsel", "moya_dvizhuka"} <= ids
    assert all(m.get("beats") for m in methods)


def test_normalize_library_id():
    assert normalize_library_id("none", known_ids={"a"}) == NONE_ID
    assert normalize_library_id("a", known_ids={"a"}) == "a"
    assert normalize_library_id("unknown", known_ids={"a"}) == NONE_ID

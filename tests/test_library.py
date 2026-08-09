from __future__ import annotations

from edit.library import (
    NONE_ID,
    compose_system_prompt,
    idea_trigger_menu,
    load_hook_formulas,
    load_idea_triggers,
    load_knowledge_menu,
    load_open_second_triggers,
    normalize_library_id,
)
from edit.e_editor import load_story_methods
from edit.e_editor import PROMPT_PATH as E_EDITOR_PROMPT
from edit.e_hook import PROMPT_PATH as E_HOOK_PROMPT
from edit.d2_monologue import PROMPT_PATH as D2_PROMPT


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


def test_knowledge_menus_are_short_static_files():
    editor = load_knowledge_menu("e_editor_menu")
    hook = load_knowledge_menu("e_hook_menu")
    d2 = load_knowledge_menu("d2_methods_menu")
    assert "увеличить до предела" in editor
    assert "СТОП-ЛИСТ" in hook
    assert "Было / Стало" in d2
    # Бюджет качества: короткие меню, не лекции.
    assert len(editor) < 900
    assert len(hook) < 900
    assert len(d2) < 900


def test_compose_system_prompt_appends_knowledge_menu():
    text = compose_system_prompt(E_EDITOR_PROMPT, "e_editor_menu")
    assert "научпоп про историю визуала" in text
    assert "УГЛЫ ФАНТОГРАММЫ" in text
    assert "ЗНАНИЯ" in compose_system_prompt(E_HOOK_PROMPT, "e_hook_menu")
    d2 = compose_system_prompt(D2_PROMPT, "d2_methods_menu")
    assert "МЕТОДИКИ" in d2
    assert "СНАЧАЛА РЕАКЦИЯ, ПОТОМ ФАКТ" in d2
    assert "а как тебе эта" in d2


def test_stop_lists_loaded_from_config():
    from edit.library import banned_speech_phrases, load_stop_lists

    lists = load_stop_lists()
    assert "кому это интересно" in lists["service_speech"]
    assert "досмотри" in lists["service_speech"]
    banned = banned_speech_phrases()
    assert "а вот нифига" in banned
    assert "всем, кто" in banned

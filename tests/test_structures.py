from __future__ import annotations

from edit.structures import (
    NONE_ID,
    get_structure,
    load_structures,
    normalize_structure_id,
    structure_menu,
)


def test_structure_library_has_eleven_plus_none_menu():
    items = load_structures()
    assert len(items) == 11
    assert all(item.get("id") and item.get("full_example") for item in items)
    menu = structure_menu()
    assert menu[-1]["id"] == NONE_ID
    assert len(menu) == 12


def test_normalize_structure_id_accepts_none_aliases():
    assert normalize_structure_id(None) == NONE_ID
    assert normalize_structure_id("none") == NONE_ID
    assert normalize_structure_id("Нет") == NONE_ID
    assert normalize_structure_id("myth_bust") == "myth_bust"
    assert normalize_structure_id({"id": "historical"}) == "historical"


def test_get_structure_returns_full_example():
    item = get_structure("historical")
    assert item is not None
    assert "идеальный пресс" in item["full_example"]
    assert get_structure("none") is None

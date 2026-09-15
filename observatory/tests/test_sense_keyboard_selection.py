from pathlib import Path


def test_sense_rows_are_keyboard_selectable():
    source = (Path(__file__).parents[1] / "render" / "senses.js").read_text()
    assert 'row.setAttribute("role", "button")' in source
    assert "row.tabIndex = 0" in source
    assert 'event.key === "Enter"' in source
    assert 'event.key === " "' in source

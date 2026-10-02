import symbiont.core as core


def test_every_name_in_all_is_importable() -> None:
    missing = [name for name in core.__all__ if not hasattr(core, name)]
    assert missing == []

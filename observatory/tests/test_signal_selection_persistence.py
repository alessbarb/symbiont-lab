from pathlib import Path


def test_snapshot_projection_keeps_selected_signal_when_profile_is_temporarily_absent():
    source = (Path(__file__).parents[1] / "projection" / "snapshot.js").read_text()

    # Selection is intentionally independent from the current profile list so
    # reconnects/replays can render an explicit unavailable state.
    assert "selectedSignalId = null" not in source

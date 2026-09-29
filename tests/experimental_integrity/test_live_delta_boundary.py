from pathlib import Path


def test_live_delta_protocol_stays_outside_organism_runtime() -> None:
    root = Path(__file__).resolve().parents[2]
    core = root / "src" / "symbiont"
    mentions = []
    for path in core.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "observer-live-delta-v1" in text or "ObservationDeltaEncoder" in text:
            mentions.append(path.relative_to(root).as_posix())

    assert mentions == []


def test_web_consumers_decode_before_dispatch() -> None:
    root = Path(__file__).resolve().parents[2]
    mind = (
        root / "src" / "symbiont_lab" / "workbench" / "web" / "views" / "mind" / "streams.js"
    ).read_text(encoding="utf-8")
    body = (
        root / "src" / "symbiont_lab" / "workbench" / "web" / "views" / "body" / "viewer.js"
    ).read_text(encoding="utf-8")

    for source in (mind, body):
        assert "LiveObservationDecoder" in source
        assert ".liveDecoder.decode(" in source


def test_domain_specific_high_frequency_streams_are_not_generic_delta_channels() -> None:
    root = Path(__file__).resolve().parents[2]
    protocol = (root / "src" / "symbiont_lab" / "observation" / "delta.py").read_text(
        encoding="utf-8"
    )

    assert '"body_pose"' not in protocol.split("COMPRESSIBLE_TYPES", 1)[1].split(")", 1)[0]
    assert '"world_scene"' not in protocol.split("COMPRESSIBLE_TYPES", 1)[1].split(")", 1)[0]

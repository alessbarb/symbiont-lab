import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from symbiont_lab.world.dashboard_server import make_server
from symbiont_lab.world.dashboard_state import WorldDashboardState


@pytest.fixture
def running_server():
    state = WorldDashboardState(world_seed=101, founders=3, width=6, height=6, tick_delay_s=0.05)
    server = make_server(port=0, state=state)
    state.start()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    try:
        yield server
    finally:
        state.stop()
        server.shutdown()
        server.server_close()


def _get(server, path: str):
    port = server.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as response:
        return response.status, response.read()


def test_index_page_served(running_server):
    status, body = _get(running_server, "/")
    assert status == 200
    assert b"Symbiont World" in body
    assert b"Scientific Observatory" in body
    assert b"[ Reality ]" in body
    assert b"[ Phenotype ]" in body
    assert b"[ Perception ]" in body
    assert b"[ Self ]" in body
    assert b"timelineCanvas" in body
    assert b"overlayControls" in body
    assert b"/api/events?after=" in body


def test_api_state_returns_progressing_tick(running_server):
    _, first = _get(running_server, "/api/state")
    time.sleep(0.3)
    _, second = _get(running_server, "/api/state")
    tick_first = json.loads(first)["tick"]
    tick_second = json.loads(second)["tick"]
    assert tick_second > tick_first


def test_api_state_shape(running_server):
    _, body = _get(running_server, "/api/state")
    data = json.loads(body)
    expected_keys = {
        "running", "error", "tick", "alive_count", "text",
        "world_id", "width", "height", "organisms", "fields", "cells",
        "history", "events",
    }
    assert set(data) == expected_keys
    assert data["running"] is True
    assert data["alive_count"] == 3
    assert "World" in data["text"]
    assert "ticks" in data["history"]
    assert isinstance(data["events"], list)


def test_api_state_includes_graphical_snapshot_for_svg_rendering(running_server):
    _, body = _get(running_server, "/api/state")
    data = json.loads(body)
    assert data["width"] == 6
    assert data["height"] == 6
    assert len(data["organisms"]) == 3
    org = data["organisms"][0]
    assert {"id", "q", "r", "region", "alive", "vital_state", "integrity", "metabolic_reserve"}.issubset(set(org))
    cell_key = f"{org['q']},{org['r']}"
    assert cell_key in data["cells"]
    assert "resources" in data["cells"][cell_key]
    assert "hazards" in data["cells"][cell_key]
    assert isinstance(data["fields"], dict)



def test_unknown_path_returns_404(running_server):
    port = running_server.server_address[1]
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/nonsense")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("expected 404")


def test_server_has_no_post_handler():
    """No control surface: the handler class must not define do_POST or
    any other mutating verb (docs/design/symbiont-world-v2.md §8)."""
    from symbiont_lab.world.dashboard_api import make_handler

    handler_cls = make_handler(WorldDashboardState(founders=1, width=4, height=4))
    for verb in ("do_POST", "do_PUT", "do_DELETE", "do_PATCH"):
        assert not hasattr(handler_cls, verb)


def test_world_dashboard_state_stops_when_all_organisms_die():
    state = WorldDashboardState(founders=1, width=4, height=4, tick_delay_s=0.0)
    organism_id = state.population.organism_ids[0]
    from symbiont.core.physiology import VitalState

    physiology = state.population._rigs[organism_id].runtime._physiology
    physiology._state = VitalState.DEAD
    physiology._death_tick = 0

    state.start()
    time.sleep(0.2)
    payload = state.payload()
    assert payload["running"] is False
    assert payload["alive_count"] == 0


def test_world_dashboard_state_saves_checkpoint_to_storage(tmp_path):
    from symbiont_lab.world.persistence import WorldStorage

    storage = WorldStorage(tmp_path / "world")
    state = WorldDashboardState(
        founders=2,
        width=4,
        height=4,
        tick_delay_s=0.01,
        storage=storage,
        checkpoint_interval=2,
    )
    state.start()
    time.sleep(0.15)
    state.stop()

    assert storage.head_file.exists()
    chk = storage.load_latest_checkpoint()
    assert chk.tick >= 2
    assert len(chk.organisms) == 2



def test_incremental_events_endpoint_is_read_only_and_gap_free(running_server):
    _, first_body = _get(running_server, "/api/events?limit=5")
    first_page = json.loads(first_body)
    assert set(first_page) == {"events", "next_after", "has_more"}
    assert len(first_page["events"]) <= 5

    cursor = first_page["next_after"]
    if cursor is None:
        time.sleep(0.2)
        _, first_body = _get(running_server, "/api/events?limit=5")
        first_page = json.loads(first_body)
        cursor = first_page["next_after"]

    assert cursor is not None
    time.sleep(0.2)
    _, second_body = _get(
        running_server,
        f"/api/events?after={cursor}&limit=256",
    )
    second_page = json.loads(second_body)
    assert all(event["event_id"] != cursor for event in second_page["events"])
    ids = [event["event_id"] for event in second_page["events"]]
    assert len(ids) == len(set(ids))


def test_incremental_events_endpoint_rejects_unknown_cursor(running_server):
    port = running_server.server_address[1]
    try:
        urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/events?after=evt-does-not-exist"
        )
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
        payload = json.loads(exc.read())
        assert "unknown after event_id" in payload["error"]
    else:
        raise AssertionError("expected 400 for unknown event cursor")


def test_api_state_does_not_invent_prediction_confidence(running_server):
    _, body = _get(running_server, "/api/state")
    data = json.loads(body)
    assert data["organisms"]
    for org in data["organisms"]:
        assert org["cognition"]["prediction_confidence"] is None
        assert isinstance(org["cognition"]["private_model_bridge_active"], bool)


def test_dashboard_state_uses_restored_population_topology_for_constitution():
    from symbiont_lab.world.genesis_v1 import build_ground_truth
    from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
    from symbiont_world.topology import HexTopology

    topology = HexTopology(width=6, height=5)
    truth = build_ground_truth()
    cells = founder_placement(101, topology, 2)
    population = PopulationGenesisRuntime(
        organism_ids=("a", "b"),
        world_seed=101,
        ground_truth=truth,
        topology=topology,
        start_cells=cells,
    )
    state = WorldDashboardState(
        width=2,
        height=2,
        population=population,
    )

    assert state.topology.width == 6
    assert state.topology.height == 5
    assert state.constitution.world_dimensions == (6, 5)


def test_v4_living_world_components_served(running_server):
    status, body = _get(running_server, "/")
    assert status == 200
    # Epistemological tabs
    assert b"[ Mind ]" in body
    assert b"[ Population ]" in body
    # Viewport & Camera controls
    assert b"viewportContainer" in body
    assert b"zoomInBtn" in body
    assert b"zoomResetBtn" in body
    assert b"followOrgBtn" in body
    # Subjective vision & Ghost mode
    assert b"subjectiveVisionBtn" in body
    assert b"ghostModeBtn" in body
    # Temporal scrubber
    assert b"scrubberSlider" in body
    assert b"playPauseBtn" in body
    # Mind & Population Canvases
    assert b"mindGraphCanvas" in body
    assert b"popClusterCanvas" in body

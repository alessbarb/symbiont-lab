from __future__ import annotations

from pathlib import Path

import pytest

pybullet = pytest.importorskip("pybullet")

from symbiont_lab.physics3d.engine import run
from symbiont_lab.physics3d.persistence import read_symbiont_bundle_runtime


def test_existing_symbiont_reuse_advances_tick_with_fresh_body(tmp_path: Path) -> None:
    symbiont_file = tmp_path / "organism.symbiont"
    first_body = tmp_path / "body-first.json"
    second_body = tmp_path / "body-second.json"
    first_telemetry = tmp_path / "telemetry-first"
    second_telemetry = tmp_path / "telemetry-second"

    assert run(
        headless=True,
        ticks=1,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=True,
        fresh_body=True,
        symbiont_file=symbiont_file,
        body_file=first_body,
        telemetry_file=first_telemetry,
    ) == 0

    first = read_symbiont_bundle_runtime(symbiont_file)
    first_tick = int(first["saved_at_tick"])
    organism_id = str(first["organism_id"])
    assert first_tick >= 1
    assert first["embodiment_lifecycle"]["state"] == "dormant"
    assert first["embodiment_lifecycle"]["epoch"] == 1
    assert first["living_body"]["age_ticks"] == 1
    assert first["living_body"]["senescence"] == 0.0
    first_embodiment_id = str(first["embodiment_episode"]["embodiment_id"])
    first_body_id = str(first["embodiment_episode"]["body_id"])
    assert first["embodiment_episode"]["schema_version"] == 3

    assert run(
        headless=True,
        ticks=1,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=False,
        fresh_body=True,
        symbiont_file=symbiont_file,
        body_file=second_body,
        telemetry_file=second_telemetry,
    ) == 0

    second = read_symbiont_bundle_runtime(symbiont_file)
    assert str(second["organism_id"]) == organism_id
    assert int(second["saved_at_tick"]) == first_tick + 1
    assert second["embodiment_lifecycle"]["state"] == "dormant"
    assert second["embodiment_lifecycle"]["epoch"] == 2
    assert second["embodiment_lifecycle"]["history"][-1]["ended_tick"] == first_tick
    assert second["living_body"]["age_ticks"] == 1
    assert second["living_body"]["senescence"] == 0.0
    assert second["embodiment_lifecycle"]["current"]["known_contract_memory"] is True
    assert second["embodiment_lifecycle"]["current"]["contract_relation"] == "known-contract"
    assert len(second["embodiment_epoch_summaries"]) == 1
    assert second["embodiment_epoch_summaries"][0]["duration_body_ticks"] == 1

    assert "embodiment_memory" not in second
    assert second["embodiment_episode"]["schema_version"] == 3
    assert second["embodiment_episode"]["embodiment_id"] != first_embodiment_id
    assert second["embodiment_episode"]["body_id"] != first_body_id
    memories = second["embodiment_archive"]["body_memories"]
    assert any(item["body_id"] == first_body_id for item in memories)

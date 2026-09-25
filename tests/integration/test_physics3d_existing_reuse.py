from __future__ import annotations

from pathlib import Path
import json

import pytest

pybullet = pytest.importorskip("pybullet")

from symbiont_lab.physics3d.engine import run
from symbiont_lab.physics3d.persistence import (
    load_body_state_file,
    read_symbiont_bundle_runtime,
)


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
    first_physical = load_body_state_file(first_body)
    assert first_physical["body_id"] == first_body_id
    assert first["embodiment_episode"]["schema_version"] == 3
    assert first["embodiment_episode"]["contract"]["schema_version"] == 3
    assert (
        first["embodiment_lifecycle"]["current"]["contract_fingerprint"]
        == first["embodiment_episode"]["contract"]["contract_fingerprint"]
    )

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
    assert second["embodiment_episode"]["contract"]["schema_version"] == 3
    assert (
        second["embodiment_lifecycle"]["current"]["contract_fingerprint"]
        == second["embodiment_episode"]["contract"]["contract_fingerprint"]
    )
    assert second["embodiment_episode"]["embodiment_id"] != first_embodiment_id
    assert second["embodiment_episode"]["body_id"] != first_body_id
    second_body_id = str(second["embodiment_episode"]["body_id"])
    second_physical = load_body_state_file(second_body)
    assert second_physical["body_id"] == second_body_id
    assert second_physical["body_id"] != first_physical["body_id"]
    assert second["embodiment_episode"]["prior"]["relation"] == "same-contract"
    assert second["embodiment_episode"]["prior"]["authority"] == "hypothesis_only"
    assert second["embodiment_episode"]["prior"]["source_body_id"] == first_body_id
    memories = second["embodiment_archive"]["body_memories"]
    assert any(item["body_id"] == first_body_id for item in memories)



def test_existing_symbiont_resume_same_body_preserves_embodiment_identity(
    tmp_path: Path,
) -> None:
    symbiont_file = tmp_path / "organism-resume.symbiont"
    body_file = tmp_path / "body-resume.json"
    telemetry_first = tmp_path / "telemetry-resume-first"
    telemetry_second = tmp_path / "telemetry-resume-second"

    assert run(
        headless=True,
        ticks=1,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=True,
        fresh_body=True,
        symbiont_file=symbiont_file,
        body_file=body_file,
        telemetry_file=telemetry_first,
    ) == 0
    first = read_symbiont_bundle_runtime(symbiont_file)
    first_tick = int(first["saved_at_tick"])
    first_episode = first["embodiment_episode"]
    first_embodiment_id = str(first_episode["embodiment_id"])
    first_body_id = str(first_episode["body_id"])
    first_physical = load_body_state_file(body_file)
    assert first_physical["body_id"] == first_body_id
    first_epoch = int(first_episode["epoch"])
    first_embodiment_tick = int(first_episode["embodiment_tick"])

    assert run(
        headless=True,
        ticks=1,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=False,
        fresh_body=False,
        symbiont_file=symbiont_file,
        body_file=body_file,
        telemetry_file=telemetry_second,
    ) == 0
    second = read_symbiont_bundle_runtime(symbiont_file)
    second_episode = second["embodiment_episode"]

    assert int(second["saved_at_tick"]) == first_tick + 1
    assert str(second_episode["embodiment_id"]) == first_embodiment_id
    assert str(second_episode["body_id"]) == first_body_id
    second_physical = load_body_state_file(body_file)
    assert second_physical["body_id"] == first_body_id
    assert int(second_episode["epoch"]) == first_epoch
    assert int(second_episode["embodiment_tick"]) == first_embodiment_tick + 1
    assert second_episode["contract"]["schema_version"] == 3
    assert second["embodiment_lifecycle"]["history"] == first[
        "embodiment_lifecycle"
    ]["history"]



def test_legacy_physical_checkpoint_adopts_episode_body_identity(
    tmp_path: Path,
) -> None:
    symbiont_file = tmp_path / "organism-legacy-body-id.symbiont"
    body_file = tmp_path / "body-legacy-id.json"
    telemetry_first = tmp_path / "telemetry-legacy-id-first"
    telemetry_second = tmp_path / "telemetry-legacy-id-second"

    assert run(
        headless=True,
        ticks=1,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=True,
        fresh_body=True,
        symbiont_file=symbiont_file,
        body_file=body_file,
        telemetry_file=telemetry_first,
    ) == 0
    first = read_symbiont_bundle_runtime(symbiont_file)
    canonical_body_id = str(first["embodiment_episode"]["body_id"])

    legacy_body = load_body_state_file(body_file)
    assert legacy_body.pop("body_id") == canonical_body_id
    body_file.write_text(
        json.dumps(
            legacy_body,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    assert run(
        headless=True,
        ticks=1,
        show_monitor=False,
        enable_slm=False,
        new_symbiont=False,
        fresh_body=False,
        symbiont_file=symbiont_file,
        body_file=body_file,
        telemetry_file=telemetry_second,
    ) == 0

    migrated_body = load_body_state_file(body_file)
    second = read_symbiont_bundle_runtime(symbiont_file)
    assert migrated_body["body_id"] == canonical_body_id
    assert second["embodiment_episode"]["body_id"] == canonical_body_id

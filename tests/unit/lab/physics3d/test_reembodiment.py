from __future__ import annotations

from copy import deepcopy

from symbiont_lab.physics3d.reembodiment import (
    EmbodimentContract,
    lifecycle_summary,
    migrate_temporal_domains,
    prepare_fresh_embodiment_checkpoint,
    update_lifecycle_for_checkpoint,
)


def _checkpoint(*, vital_state: str = "dead") -> dict:
    return {
        "saved_at_tick": 41,
        "organism_id": "symbiont:persistent",
        "living_body": {
            "schema_version": 3,
            "vital_state": vital_state,
            "energy_reserve": 0.0,
            "max_energy": 1600.0,
            "structural_integrity": 0.4,
            "temperature": 0.5,
            "fatigue": 0.3,
            "growth_progress": 1.0,
            "senescence": 0.5,
            "age_ticks": 41,
            "transitions": 1,
            "death_tick": 41 if vital_state == "dead" else None,
            "metabolic_capacity": {},
            "metabolic_replenishment": {},
            "metabolic_reserve": {},
            "structure_states": {},
        },
        "metabolism": {"marker": "old-metabolism"},
        "homeostasis": {"marker": "old-homeostasis"},
        "physiology": {"marker": "old-physiology"},
        "body_schema": {"schema_version": 3, "state": "partial", "parts": [{"part_id": "old"}]},
        "self_model": {"old-sense": {"confidence": 1}},
        "sensory_development": {"old": True},
        "sensory_system": {"old": True},
        "genome": {
            "genome_id": "genome_symbiont_physics3d_v9",
            "motor": {"slot_count": 62},
        },
        "constitution_fingerprint": {"schema_version": 1, "genome_hash": "old"},
        "actuation": {
            "enabled": True,
            "constitution": {"slots": [{"slot_id": f"motor_slot.{i}"} for i in range(62)]},
            "states": {"old": {"health": 0.0}},
            "proposer": {"learned": "old"},
            "sensorimotor": {
                "schema_version": 8,
                "primitives": [{
                    "primitive_id": "primitive.old",
                    "sequence": [
                        [["actuator.0", 5]],
                        [["actuator.1", 5]],
                        [["actuator.2", 5]],
                        [["actuator.3", 5]],
                    ],
                }],
            },
            "pending_motor_observation": [{"old": True}],
            "pending_proprioception": {"old": 1.0},
        },
        "experience_ledger": {"records": [{"record_id": "experience-1"}]},
        "episodic_memory": {"episodes": [{"episode_id": "episode-1"}]},
        "private_model_registry": {"records": [{"model_id": "model-1", "state": "active"}]},
        "cognitive_bridge": {
            "graph": {
                "nodes": [
                    {"node_id": "concept.old", "kind": "concept"},
                    {"node_id": "readout_motor:actuator.old", "kind": "readout"},
                    {"node_id": "readout_primitive:primitive.old", "kind": "readout"},
                ],
                "edges": [
                    {
                        "source_id": "concept.old",
                        "target_id": "readout_motor:actuator.old",
                        "kind": "excitatory",
                    },
                    {
                        "source_id": "concept.old",
                        "target_id": "readout_primitive:primitive.old",
                        "kind": "excitatory",
                    },
                ],
            },
            "node_born_tick": {
                "concept.old": 1,
                "readout_motor:actuator.old": 2,
                "readout_primitive:primitive.old": 3,
            },
            "structural_candidates": [
                {"candidate_id": "motor:old", "family": "motor_readout"},
                {"candidate_id": "concept:keep", "family": "concept"},
            ],
        },
    }


def _fresh(*, slots: int = 62) -> dict:
    return {
        "living_body": {
            "vital_state": "active",
            "energy_reserve": 1600.0,
        },
        "metabolism": {"marker": "fresh-metabolism"},
        "homeostasis": {"marker": "fresh-homeostasis"},
        "physiology": {"marker": "fresh-physiology"},
        "body_schema": {"schema_version": 3, "state": "undeveloped", "parts": []},
        "self_model": {},
        "sensory_development": {},
        "sensory_system": {"fresh": True},
        "genome": {
            "genome_id": "genome_symbiont_physics3d_v9",
            "motor": {"slot_count": slots},
        },
        "actuation": {
            "enabled": True,
            "constitution": {"slots": [{"slot_id": f"motor_slot.{i}"} for i in range(slots)]},
            "states": {"fresh": {"health": 1.0}},
            "proposer": {"learned": "fresh"},
            "sensorimotor": {"schema_version": 8, "primitives": [], "historical_candidates": []},
            "pending_motor_observation": [],
            "pending_proprioception": {},
        },
    }


def test_dead_body_reembodiment_preserves_identity_but_revalidates_body_knowledge() -> None:
    previous = _checkpoint()
    transformed = prepare_fresh_embodiment_checkpoint(
        previous,
        _fresh(),
        contract=EmbodimentContract("anthropomorphic-v4", 107, 62),
    )

    assert transformed["organism_id"] == "symbiont:persistent"
    assert transformed["experience_ledger"] == previous["experience_ledger"]
    assert transformed["episodic_memory"] == previous["episodic_memory"]

    records = transformed["private_model_registry"]["records"]
    assert records[0]["model_id"] == "model-1"
    assert records[0]["state"] == "degraded"

    active_nodes = {
        node["node_id"]
        for node in transformed["cognitive_bridge"]["graph"]["nodes"]
    }
    assert active_nodes == {"concept.old"}
    assert transformed["cognitive_bridge"]["graph"]["edges"] == []

    assert transformed["living_body"]["vital_state"] == "active"
    assert transformed["living_body"]["energy_reserve"] == 1600.0
    assert transformed["body_schema"]["state"] == "undeveloped"
    assert transformed["actuation"]["states"] == {"fresh": {"health": 1.0}}
    assert transformed["actuation"]["proposer"] == {"learned": "fresh"}

    sensorimotor = transformed["actuation"]["sensorimotor"]
    assert sensorimotor["primitives"] == []
    assert sensorimotor["historical_candidates"] == [{
        "primitive_id": "primitive.old",
        "sequence": [
            [["actuator.0", 5]],
            [["actuator.1", 5]],
            [["actuator.2", 5]],
            [["actuator.3", 5]],
        ],
    }]

    lifecycle = lifecycle_summary(transformed)
    assert lifecycle["state"] == "active"
    assert lifecycle["epoch"] == 2
    assert lifecycle["history_count"] == 1
    current = transformed["embodiment_lifecycle"]["current"]
    assert current["contract_relation"] == "same-known"
    assert current["known_contract_memory"] is True
    assert current["candidate_private_model_ids"] == ["model-1"]
    assert transformed["embodiment_lifecycle"]["history"][0]["end_body_vital_state"] == "dead"
    assert len(transformed["embodiment_epoch_summaries"]) == 1
    assert len(transformed["embodiment_memory"]["contracts"]) == 1

def test_changed_contract_archives_old_schema_and_restarts_body_specific_learning() -> None:
    previous = _checkpoint(vital_state="active")
    transformed = prepare_fresh_embodiment_checkpoint(
        previous,
        _fresh(slots=40),
        contract=EmbodimentContract("compact-v1", 84, 40),
    )

    assert transformed["organism_id"] == previous["organism_id"]
    assert transformed["experience_ledger"] == previous["experience_ledger"]
    records = transformed["private_model_registry"]["records"]
    assert len(records) == 1
    assert records[0]["model_id"] == "model-1"
    assert records[0]["state"] == "degraded"

    active_nodes = {
        node["node_id"]
        for node in transformed["cognitive_bridge"]["graph"]["nodes"]
    }
    assert "concept.old" in active_nodes
    assert "readout_motor:actuator.old" not in active_nodes
    assert "readout_primitive:primitive.old" not in active_nodes
    assert transformed["cognitive_bridge"]["graph"]["edges"] == []
    assert transformed["cognitive_bridge"]["structural_candidates"] == [
        {"candidate_id": "concept:keep", "family": "concept"}
    ]

    assert transformed["body_schema"]["state"] == "undeveloped"
    assert transformed["self_model"] == {}
    assert transformed["sensory_development"] == {}
    assert transformed["actuation"]["sensorimotor"]["primitives"] == []
    assert transformed["actuation"]["sensorimotor"]["historical_candidates"] == []
    assert transformed["actuation"]["proposer"] == {"learned": "fresh"}
    assert transformed["genome"]["motor"]["slot_count"] == 40
    assert transformed["constitution_fingerprint"]["genome_hash"] != "old"

    history = transformed["embodiment_lifecycle"]["history"]
    assert history[-1]["body_schema"] == previous["body_schema"]
    archived = history[-1]["motor_cognitive_surface"]
    assert {node["node_id"] for node in archived["nodes"]} == {
        "readout_motor:actuator.old",
        "readout_primitive:primitive.old",
    }
    assert len(archived["edges"]) == 2
    assert history[-1]["active_private_model_id"] == "model-1"
    assert transformed["embodiment_lifecycle"]["current"]["contract_relation"] == "changed"


def test_stopping_marks_symbiont_dormant_without_changing_body_death_state() -> None:
    payload = deepcopy(_checkpoint(vital_state="active"))
    updated = update_lifecycle_for_checkpoint(
        payload,
        contract=EmbodimentContract("anthropomorphic-v4", 107, 62),
        state="dormant",
    )
    assert updated["living_body"]["vital_state"] == "active"
    assert updated["embodiment_lifecycle"]["state"] == "dormant"



def test_known_contract_return_recovers_hypotheses_without_restoring_authority() -> None:
    humanoid = _checkpoint(vital_state="active")
    crawler = prepare_fresh_embodiment_checkpoint(
        humanoid,
        _fresh(slots=40),
        contract=EmbodimentContract("crawler-v1", 84, 40),
    )
    crawler["saved_at_tick"] = 80
    crawler["living_body"]["age_ticks"] = 39
    crawler["living_body"]["vital_state"] = "active"

    returned = prepare_fresh_embodiment_checkpoint(
        crawler,
        _fresh(slots=62),
        contract=EmbodimentContract("anthropomorphic-v4", 107, 62),
    )

    current = returned["embodiment_lifecycle"]["current"]
    assert current["known_contract_memory"] is True
    assert current["contract_relation"] == "known-return"
    assert current["candidate_private_model_ids"] == ["model-1"]

    sensorimotor = returned["actuation"]["sensorimotor"]
    assert sensorimotor["primitives"] == []
    assert [item["primitive_id"] for item in sensorimotor["historical_candidates"]] == [
        "primitive.old"
    ]

    assert returned["body_schema"]["state"] == "undeveloped"
    assert all(
        not str(node["node_id"]).startswith(("readout_motor:", "readout_primitive:"))
        for node in returned["cognitive_bridge"]["graph"]["nodes"]
    )
    assert returned["private_model_registry"]["records"][0]["state"] == "degraded"


def test_temporal_migration_repairs_only_unambiguous_global_body_age() -> None:
    payload = _checkpoint(vital_state="dead")
    payload["saved_at_tick"] = 10_000
    payload["living_body"]["age_ticks"] = 10_000
    payload["living_body"]["death_tick"] = 10_000
    payload["physiology"] = {"death_tick": 10_000}
    payload["embodiment_lifecycle"] = {
        "schema_version": 1,
        "state": "dormant",
        "epoch": 3,
        "current": {
            "body_kind": "anthropomorphic-v4",
            "receptor_count": 107,
            "effector_count": 62,
            "started_tick": 8_000,
        },
        "history": [],
    }

    migrated = migrate_temporal_domains(payload)

    assert migrated["living_body"]["age_ticks"] == 2_000
    assert migrated["living_body"]["death_tick"] == 2_000
    assert migrated["physiology"]["death_tick"] == 2_000
    assert migrated["living_body"]["senescence"] == 0.5
    assert migrated["temporal_migration"]["source_age_ticks"] == 10_000
    assert migrated["temporal_migration"]["body_age_ticks"] == 2_000


def test_temporal_migration_fails_safe_on_ambiguous_age() -> None:
    payload = _checkpoint(vital_state="active")
    payload["saved_at_tick"] = 10_000
    payload["living_body"]["age_ticks"] = 7_777
    payload["embodiment_lifecycle"] = {
        "schema_version": 1,
        "state": "dormant",
        "epoch": 2,
        "current": {
            "body_kind": "anthropomorphic-v4",
            "receptor_count": 107,
            "effector_count": 62,
            "started_tick": 8_000,
        },
        "history": [],
    }

    migrated = migrate_temporal_domains(payload)

    assert migrated["living_body"]["age_ticks"] == 7_777
    assert "temporal_migration" not in migrated


def test_dead_checkpoint_closes_epoch_summary_and_archives_memory() -> None:
    payload = _checkpoint(vital_state="dead")
    payload["embodiment_lifecycle"] = {
        "schema_version": 1,
        "state": "active",
        "epoch": 4,
        "current": {
            "body_kind": "anthropomorphic-v4",
            "receptor_count": 107,
            "effector_count": 62,
            "started_tick": 0,
        },
        "history": [],
    }

    updated = update_lifecycle_for_checkpoint(
        payload,
        contract=EmbodimentContract("anthropomorphic-v4", 107, 62),
        state="dormant",
        metrics={
            "absorbed_material_total": 12.0,
            "mechanical_work_total": 3.0,
            "physiological_cost_total": 0.5,
            "reacclimation_ticks_consumed": 8,
            "reacclimation_completed": True,
            "vital_state_ticks": {"active": 20, "stressed": 3},
        },
    )

    summary = updated["embodiment_epoch_summaries"][-1]
    assert summary["epoch"] == 4
    assert summary["end_reason"] == "dead_energy"
    assert summary["duration_body_ticks"] == 41
    assert summary["absorbed_material_total"] == 12.0
    assert summary["mechanical_work_total"] == 3.0
    assert summary["reacclimation_completed"] is True
    assert updated["embodiment_lifecycle"]["current"]["closed"] is True
    assert updated["embodiment_memory"]["contracts"]

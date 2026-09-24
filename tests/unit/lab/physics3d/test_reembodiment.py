from __future__ import annotations

from copy import deepcopy

from symbiont_lab.physics3d.reembodiment import (
    EmbodimentContract,
    lifecycle_summary,
    prepare_fresh_embodiment_checkpoint,
    update_lifecycle_for_checkpoint,
)


def _checkpoint(*, vital_state: str = "dead") -> dict:
    return {
        "saved_at_tick": 41,
        "organism_id": "symbiont:persistent",
        "living_body": {
            "vital_state": vital_state,
            "energy_reserve": 0.0,
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
            "constitution": {"slots": ["old"]},
            "states": {"old": {"health": 0.0}},
            "proposer": {"learned": "old"},
            "sensorimotor": {"primitives": ["p1"]},
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
            "constitution": {"slots": [f"slot-{i}" for i in range(slots)]},
            "states": {"fresh": {"health": 1.0}},
            "proposer": {"learned": "fresh"},
            "sensorimotor": {"primitives": []},
            "pending_motor_observation": [],
            "pending_proprioception": {},
        },
    }


def test_dead_body_reembodiment_preserves_symbiont_identity_and_acquired_state() -> None:
    previous = _checkpoint()
    transformed = prepare_fresh_embodiment_checkpoint(
        previous,
        _fresh(),
        contract=EmbodimentContract("anthropomorphic-v4", 107, 62),
    )

    assert transformed["organism_id"] == "symbiont:persistent"
    assert transformed["experience_ledger"] == previous["experience_ledger"]
    assert transformed["episodic_memory"] == previous["episodic_memory"]
    assert transformed["private_model_registry"] == previous["private_model_registry"]
    assert transformed["cognitive_bridge"] == previous["cognitive_bridge"]

    assert transformed["living_body"]["vital_state"] == "active"
    assert transformed["living_body"]["energy_reserve"] == 1600.0
    assert transformed["actuation"]["states"] == {"fresh": {"health": 1.0}}
    assert transformed["actuation"]["sensorimotor"] == previous["actuation"]["sensorimotor"]
    assert transformed["actuation"]["proposer"] == previous["actuation"]["proposer"]

    lifecycle = lifecycle_summary(transformed)
    assert lifecycle["state"] == "active"
    assert lifecycle["epoch"] == 2
    assert lifecycle["history_count"] == 1
    assert transformed["embodiment_lifecycle"]["history"][0]["end_body_vital_state"] == "dead"


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
    assert transformed["actuation"]["sensorimotor"] == {"primitives": []}
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

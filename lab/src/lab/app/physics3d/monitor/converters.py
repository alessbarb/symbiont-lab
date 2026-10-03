"""Conversions between Physics3D telemetry records and monitor payloads."""

from __future__ import annotations

from typing import Any, Mapping

from embodiment.physics3d.humanoid import (
    BODY_KIND,
    BODY_STATE_SCHEMA_VERSION,
    JOINT_LIMITS,
)


def snapshot_to_physical_state(record: Mapping[str, Any]) -> dict[str, object]:
    """Reconstruct an evaluator-safe physical state payload from telemetry."""
    reconstructed_fields: list[str] = []
    joints = record.get("joints")
    if not joints or not isinstance(joints, (list, tuple)):
        reconstructed_fields.append("joints")
        joints = [
            {
                "joint_index": j_id,
                "position": 0.0,
                "velocity": 0.0,
                "applied_torque": 0.0,
            }
            for j_id in sorted(JOINT_LIMITS)
        ]
    contact_links = record.get("contact_links", ())
    base_pos = record.get("base_position", (0.0, 0.0, 0.9))
    base_orient = record.get("base_orientation", (0.0, 0.0, 0.0, 1.0))
    res_info = record.get("locomotion_resource")
    if isinstance(res_info, dict):
        res_pos = res_info.get("position", (float(base_pos[0]) + 3.0, float(base_pos[1]), 0.15))
        res_rem = float(res_info.get("remaining", 200.0))
    else:
        reconstructed_fields.append("resource_position")
        res_dist = float(record.get("resource_distance", 3.0))
        res_rem = float(record.get("resource_remaining", 200.0))
        res_pos = (float(base_pos[0]) + res_dist, float(base_pos[1]), 0.15)
    return {
        "_reconstructed_fields": reconstructed_fields,
        "schema_version": BODY_STATE_SCHEMA_VERSION,
        "body_kind": BODY_KIND,
        "base_position": list(base_pos),
        "base_orientation": list(base_orient),
        "linear_velocity": [0.0, 0.0, 0.0],
        "angular_velocity": [0.0, 0.0, 0.0],
        "joints": list(joints),
        "contact_links": list(contact_links),
        "locomotion_resource": {
            "position": list(res_pos),
            "remaining": res_rem,
        },
    }


def record_to_snapshot(
    record: Mapping[str, Any],
    *,
    fallback_id: str = "subject:replay",
) -> dict[str, object]:
    """Extract a dictionary compatible with apply_snapshot from telemetry."""
    snap = dict(record)
    symb_id = record.get("symbiont_id") or record.get("organism_id") or fallback_id
    snap.setdefault("symbiont_id", symb_id)
    snap.setdefault("embodiment_mode", "replay")
    snap.setdefault("checkpoint_age", 0)
    snap.setdefault("realtime_ratio", 1.0)
    cycle = (
        float(record.get("organism_ms", 0.0))
        + float(record.get("physics_ms", 0.0))
        + float(record.get("diagnostics_ms", 0.0))
    )
    snap.setdefault("cycle_ms", cycle if cycle > 0 else 12.0)
    base_pos = record.get("base_position")
    snap.setdefault(
        "height",
        base_pos[2] if isinstance(base_pos, (list, tuple)) and len(base_pos) >= 3 else 0.9,
    )
    snap.setdefault("strongest_outputs", ())
    snap.setdefault("slm_models", record.get("slm_models", 0))
    snap.setdefault("slm_active", record.get("slm_active", False))
    snap.setdefault("slm_training", False)
    snap.setdefault("slm_error", None)
    snap.setdefault("slm_gate_reason", None)
    snap.setdefault("slm_gate_gain", None)
    snap.setdefault("slm_best_baseline", None)
    snap.setdefault("slm_candidate_loss", None)
    snap.setdefault("slm_best_baseline_loss", None)
    episodic = record.get("episodic_memory", {})
    if not isinstance(episodic, Mapping):
        episodic = {}
    snap.setdefault(
        "episodic_episodes",
        record.get("episodic_episodes", episodic.get("episode_count", 0)),
    )
    snap.setdefault(
        "episodic_pending_records",
        record.get("episodic_pending_records", episodic.get("pending_records", 0)),
    )
    snap.setdefault(
        "episodic_compressed_episodes",
        record.get(
            "episodic_compressed_episodes",
            episodic.get("compressed_episode_count", 0),
        ),
    )
    snap.setdefault(
        "episodic_total_occurrences",
        record.get(
            "episodic_total_occurrences",
            episodic.get("total_occurrences", 0),
        ),
    )
    snap.setdefault(
        "episodic_mean_recurrence",
        record.get(
            "episodic_mean_recurrence",
            episodic.get("mean_recurrence", 0.0),
        ),
    )
    snap.setdefault(
        "episodic_exceptions",
        record.get(
            "episodic_exceptions",
            episodic.get("exception_count", 0),
        ),
    )
    snap.setdefault(
        "episodic_checkpoint_bytes",
        record.get(
            "episodic_checkpoint_bytes",
            episodic.get("checkpoint_bytes", 0),
        ),
    )
    snap.setdefault(
        "episodic_interpretations",
        record.get(
            "episodic_interpretations",
            episodic.get("interpretation_count", 0),
        ),
    )
    snap.setdefault(
        "episodic_contingencies",
        record.get(
            "episodic_contingencies",
            episodic.get("consolidated_contingencies", 0),
        ),
    )
    snap.setdefault(
        "episodic_retrievals",
        record.get("episodic_retrievals", episodic.get("retrieval_count", 0)),
    )
    snap.setdefault(
        "episodic_replays",
        record.get("episodic_replays", episodic.get("replay_count", 0)),
    )
    snap.setdefault(
        "episodic_compactions",
        record.get("episodic_compactions", episodic.get("compaction_count", 0)),
    )
    snap.setdefault(
        "episodic_evictions",
        record.get("episodic_evictions", episodic.get("eviction_count", 0)),
    )
    snap.setdefault(
        "episodic_oldest_age",
        record.get("episodic_oldest_age", episodic.get("oldest_episode_age", 0)),
    )
    snap.setdefault(
        "episodic_mean_age",
        record.get("episodic_mean_age", episodic.get("mean_episode_age", 0.0)),
    )
    snap.setdefault("symbiont_file", "")
    return snap

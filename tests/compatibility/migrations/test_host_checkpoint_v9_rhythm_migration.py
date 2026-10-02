"""Host checkpoint v9 -> v10 (ADR-0042): wall-clock rhythm contexts are retired.

Accepts: v9 payloads whose rhythm projection and replay accumulators are keyed
by the host OS time-of-day bucket ("night", "morning", ...).
Produces: v10 payloads keyed by the organism's internal CyclePhase.
Discards intentionally: every v9 rhythm context and replay accumulator,
because re-keying them to internal phases would invent an alignment.
Everything else is preserved.
"""

from __future__ import annotations

from symbiont.host.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    import_checkpoint,
    normalize_checkpoint,
)


def _v9_payload() -> dict:
    return {
        "schema_version": 9,
        "acclimation": {"cpu": {"center_class": 3, "scale_class": 2, "maturity_class": 2}},
        "rhythms": [
            {
                "percept_name": "cpu",
                "time_bucket": "night",
                "center_class": 3,
                "scale_class": 2,
                "maturity_class": 2,
            }
        ],
        "rhythms_replay": {
            "stats": [
                {
                    "percept_name": "cpu",
                    "time_bucket": "evening",
                    "count": 9,
                    "mean": 0.4,
                    "m2": 0.1,
                }
            ]
        },
    }


def test_v9_wall_clock_rhythms_are_discarded_not_rekeyed() -> None:
    migrated = normalize_checkpoint(_v9_payload())
    assert migrated["schema_version"] == CHECKPOINT_SCHEMA_VERSION == 11
    assert "rhythms" not in migrated
    assert "rhythms_replay" not in migrated
    assert migrated["acclimation"] == _v9_payload()["acclimation"]


def test_v9_payload_restores_with_empty_rhythm_model() -> None:
    _acclimation, rhythm_model, _drift = import_checkpoint(_v9_payload())
    assert rhythm_model.learned_contexts == ()

from __future__ import annotations

from symbiont_lab.experiments.loader import load_experiment_dict


def test_loader_accepts_bounded_ablation_extension():
    spec = load_experiment_dict(
        {
            "schema_version": 1,
            "experiment": {
                "id": "learning.embodied-behavioral-ablation",
                "protocol": "learning.embodied-behavioral-ablation",
                "protocol_version": 3,
            },
            "world": {"steps": 3000},
            "design": {"seeds": [101, 127, 149]},
            "ablation": {"horizon_ticks": 256},
        }
    )

    assert spec.extra_params["ablation"]["horizon_ticks"] == 256


def test_loader_rejects_unknown_ablation_keys():
    try:
        load_experiment_dict(
            {
                "experiment": {
                    "id": "x",
                    "protocol": "learning.embodied-behavioral-ablation",
                },
                "ablation": {"unknown": 1},
            }
        )
    except ValueError as exc:
        assert "unknown keys in ablation" in str(exc)
    else:
        raise AssertionError("unknown ablation key should be rejected")

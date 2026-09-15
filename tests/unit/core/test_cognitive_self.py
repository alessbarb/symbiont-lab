from __future__ import annotations

from symbiont.core.cognitive_self import (
    MAX_COGNITIVE_CHANNELS_PER_TICK,
    project_cognitive_self_observation,
)


def test_cognitive_self_observation_excludes_known_sensory_channels_and_inactive_nodes():
    observation = project_cognitive_self_observation(
        {
            "sense.alpha": 0.9,
            "concept_secret_0001": 0.7,
            "concept_inactive": 0.01,
        },
        sensory_ids={"sense.alpha"},
    )

    assert observation["schema_version"] == 1
    assert len(observation["channels"]) == 1
    channel = observation["channels"][0]
    assert channel["channel_id"].startswith("channel.cognition.")
    assert "concept_secret_0001" not in repr(observation)
    assert "concept_inactive" not in repr(observation)
    assert 1 <= channel["activity_class"] <= 15


def test_same_internal_channel_has_stable_opaque_token():
    first = project_cognitive_self_observation({"concept_a": 0.5}, sensory_ids=set())
    second = project_cognitive_self_observation({"concept_a": -0.8}, sensory_ids=set())

    assert first["channels"][0]["channel_id"] == second["channels"][0]["channel_id"]
    assert first["channels"][0]["channel_id"] != "concept_a"


def test_observation_is_bounded_to_strongest_channels():
    activations = {f"concept_{index}": 0.11 + index / 1000 for index in range(80)}
    observation = project_cognitive_self_observation(activations, sensory_ids=set())

    assert len(observation["channels"]) == MAX_COGNITIVE_CHANNELS_PER_TICK
    classes = [entry["activity_class"] for entry in observation["channels"]]
    assert classes == sorted(classes, reverse=True)


def test_nonfinite_or_non_numeric_activation_is_ignored():
    observation = project_cognitive_self_observation(
        {
            "nan": float("nan"),
            "inf": float("inf"),
            "bad": "not-a-number",
            "good": 0.4,
        },
        sensory_ids=set(),
    )

    assert len(observation["channels"]) == 1
    assert "good" not in repr(observation)

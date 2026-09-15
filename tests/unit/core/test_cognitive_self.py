from __future__ import annotations

import pytest

from symbiont.core.cognitive_self import (
    MAX_COGNITIVE_CHANNELS_PER_TICK,
    derive_cognitive_self_namespace,
    project_cognitive_self_observation,
)

NAMESPACE_A = derive_cognitive_self_namespace("1" * 32)
NAMESPACE_B = derive_cognitive_self_namespace("2" * 32)


def project(activations, *, sensory_ids=(), namespace_key=NAMESPACE_A):
    return project_cognitive_self_observation(
        activations,
        sensory_ids=sensory_ids,
        namespace_key=namespace_key,
    )


def test_cognitive_self_observation_excludes_known_sensory_channels_and_inactive_nodes():
    observation = project(
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


def test_same_internal_channel_has_stable_opaque_token_within_one_organism_namespace():
    first = project({"concept_a": 0.5})
    second = project({"concept_a": -0.8})

    assert first["channels"][0]["channel_id"] == second["channels"][0]["channel_id"]
    assert first["channels"][0]["channel_id"] != "concept_a"


def test_equal_internal_node_ids_are_not_linkable_across_organism_namespaces():
    first = project({"concept_a": 0.5}, namespace_key=NAMESPACE_A)
    second = project({"concept_a": 0.5}, namespace_key=NAMESPACE_B)

    assert first["channels"][0]["channel_id"] != second["channels"][0]["channel_id"]


def test_namespace_derivation_is_stable_for_checkpointed_private_salt():
    assert derive_cognitive_self_namespace("a" * 32) == derive_cognitive_self_namespace("a" * 32)
    assert derive_cognitive_self_namespace("a" * 32) != derive_cognitive_self_namespace("b" * 32)


def test_invalid_private_salt_or_namespace_is_rejected():
    with pytest.raises(ValueError, match="private_id_salt"):
        derive_cognitive_self_namespace("not-a-salt")
    with pytest.raises(ValueError, match="namespace_key"):
        project_cognitive_self_observation(
            {"concept_a": 0.5},
            sensory_ids=set(),
            namespace_key="bad",
        )


def test_observation_is_bounded_to_strongest_channels():
    activations = {f"concept_{index}": 0.11 + index / 1000 for index in range(80)}
    observation = project(activations)

    assert len(observation["channels"]) == MAX_COGNITIVE_CHANNELS_PER_TICK
    classes = [entry["activity_class"] for entry in observation["channels"]]
    assert classes == sorted(classes, reverse=True)


def test_nonfinite_or_non_numeric_activation_is_ignored():
    observation = project(
        {
            "nan": float("nan"),
            "inf": float("inf"),
            "bad": "not-a-number",
            "good": 0.4,
        }
    )

    assert len(observation["channels"]) == 1
    assert "good" not in repr(observation)

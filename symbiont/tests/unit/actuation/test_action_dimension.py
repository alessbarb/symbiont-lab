"""ActionDimension is acquired from causal evidence, never bootstrapped (§17-§20, §94)."""

from __future__ import annotations

import pytest

from symbiont.actuation.acquisition import AgencyAcquisition
from symbiont.actuation.dimension import (
    ActionDimension,
    ActionDimensionDiscoveryPolicy,
    ActionDimensionRegistry,
    opaque_dimension_id,
)
from symbiont.actuation.intervention import opaque_channel_ref
from symbiont.actuation.surface import derive_actuator_constitution

from .acquisition_support import SURFACE, A, B
from .acquisition_support import act as _act
from .acquisition_support import fresh_acquisition as _acquisition
from .acquisition_support import rest as _rest


def test_opaque_dimension_id_is_deterministic_and_opaque():
    first = opaque_dimension_id((opaque_channel_ref(A),))
    second = opaque_dimension_id((opaque_channel_ref(A),))
    other = opaque_dimension_id((opaque_channel_ref(B),))
    assert first == second
    assert first != other
    assert first.startswith("action.dimension.")
    assert A not in first


def test_action_dimension_rejects_non_opaque_or_ungrounded_identity():
    with pytest.raises(ValueError):
        ActionDimension(
            dimension_id="right_knee",
            intervention_signature_refs=("intervention.signature.x",),
            availability=True,
            controllability=0.0,
            confidence=0.0,
            usage_count=0,
            embodiment_bound=False,
        )
    with pytest.raises(ValueError):
        ActionDimension(
            dimension_id=opaque_dimension_id(("channel.a",)),
            intervention_signature_refs=(),
            availability=True,
            controllability=0.0,
            confidence=0.0,
            usage_count=0,
            embodiment_bound=False,
        )


def test_action_dimension_rejects_out_of_range_scores():
    with pytest.raises(ValueError):
        ActionDimension(
            dimension_id=opaque_dimension_id(("channel.a",)),
            intervention_signature_refs=("intervention.signature.x",),
            availability=True,
            controllability=1.5,
            confidence=0.0,
            usage_count=0,
            embodiment_bound=True,
        )


def test_discovery_policy_rejects_incoherent_parameters():
    with pytest.raises(ValueError):
        ActionDimensionDiscoveryPolicy(minimum_attempt_support=0)
    with pytest.raises(ValueError):
        ActionDimensionDiscoveryPolicy(minimum_consistency=1.5)
    with pytest.raises(ValueError):
        ActionDimensionDiscoveryPolicy(minimum_attempt_support=2, minimum_effect_support=3)


def test_surface_does_not_bootstrap_action_dimensions():
    acquisition = _acquisition()
    assert acquisition.action_dimensions.items == ()


def test_single_attempt_does_not_create_dimension():
    acquisition = _acquisition()
    _rest(acquisition, 0, {})
    _rest(acquisition, 1, {})
    update = _act(acquisition, 2, {A: 0.6}, {"signal.a": 0.4})
    assert update.dimension is None
    assert acquisition.action_dimensions.items == ()


def test_repeated_related_interventions_can_create_dimension():
    acquisition = _acquisition()
    for tick in range(0, 8, 2):
        _rest(acquisition, tick, {})
    update = None
    for tick in range(10, 20, 2):
        # Intensity varies; the family and its consequence recur.
        update = _act(acquisition, tick, {A: 0.3 + 0.1 * (tick % 3)}, {"signal.a": 0.4})
    assert update is not None and update.dimension is not None
    dimension = update.dimension
    assert dimension.dimension_id == opaque_dimension_id((opaque_channel_ref(A),))
    assert dimension.availability and dimension.embodiment_bound
    assert dimension.usage_count == 5
    assert dimension.controllability > 0.0


def test_dimension_can_span_multiple_channels():
    acquisition = _acquisition()
    for tick in range(0, 8, 2):
        _rest(acquisition, tick, {})
    update = None
    for tick in range(10, 20, 2):
        update = _act(acquisition, tick, {A: 0.7, B: 0.3}, {"signal.ab": 0.5})
    assert update is not None and update.dimension is not None
    channels = acquisition.action_dimensions.channel_refs(update.dimension.dimension_id)
    assert channels == tuple(sorted((opaque_channel_ref(A), opaque_channel_ref(B))))


def test_dimension_identity_does_not_equal_actuator_identity():
    acquisition = _acquisition()
    for tick in range(0, 8, 2):
        _rest(acquisition, tick, {})
    for tick in range(10, 20, 2):
        _act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
    (dimension,) = acquisition.action_dimensions.items
    assert dimension.dimension_id not in SURFACE.actuator_ids
    assert all(actuator_id not in dimension.dimension_id for actuator_id in SURFACE.actuator_ids)
    assert all(
        ref.startswith("intervention.signature.") for ref in dimension.intervention_signature_refs
    )


def test_effect_common_without_intervention_does_not_create_dimension():
    acquisition = _acquisition()
    for tick in range(0, 12, 2):
        _rest(acquisition, tick, {"signal.a": 0.4})
    update = None
    for tick in range(20, 30, 2):
        update = _act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
    assert update is not None and update.dimension is None


def test_dimension_survives_checkpoint():
    acquisition = _acquisition()
    for tick in range(0, 8, 2):
        _rest(acquisition, tick, {})
    for tick in range(10, 20, 2):
        _act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
    before = acquisition.action_dimensions.items
    restored = AgencyAcquisition()
    restored.restore_causal_state(
        effect_space=acquisition.effect_space.checkpoint(),
        causal_evidence=acquisition.causal_evidence.checkpoint(),
        acquisition=acquisition.checkpoint(),
        body_schema=None,
    )
    restored.bind_surface(SURFACE.actuator_ids, surface_fingerprint=SURFACE.contract_fingerprint)
    assert restored.action_dimensions.items == before
    assert restored.agentic_dimension_ids() == acquisition.agentic_dimension_ids()


def test_reembodiment_does_not_fake_current_binding():
    acquisition = _acquisition()
    for tick in range(0, 8, 2):
        _rest(acquisition, tick, {})
    for tick in range(10, 20, 2):
        _act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
    # A new body with the same opaque channel count exposes the same channel
    # ids; that must not make the old dimension count as bound to it.
    other_body = derive_actuator_constitution(3, physical_contract="other-body")
    assert other_body.actuator_ids == SURFACE.actuator_ids
    acquisition.bind_surface(
        other_body.actuator_ids, surface_fingerprint=other_body.contract_fingerprint
    )
    (dimension,) = acquisition.action_dimensions.items
    assert dimension.availability
    assert not dimension.embodiment_bound
    # A body lacking the channel makes it unavailable; knowledge persists.
    smaller = derive_actuator_constitution(0, physical_contract="no-output-body")
    acquisition.bind_surface(smaller.actuator_ids, surface_fingerprint=smaller.contract_fingerprint)
    (dimension,) = acquisition.action_dimensions.items
    assert not dimension.availability and not dimension.embodiment_bound
    acquisition.bind_surface(SURFACE.actuator_ids, surface_fingerprint=SURFACE.contract_fingerprint)
    assert acquisition.action_dimensions.items[0].embodiment_bound


def test_legacy_surface_dimensions_are_discarded_on_restore():
    legacy = {
        "schema_version": 1,
        "capacity": 8,
        "items": [{"dimension_id": "action.dimension.aaaa", "actuator_slot_id": "slot.0"}],
    }
    assert ActionDimensionRegistry.restore(legacy).items == ()


def test_registry_restore_rejects_wrong_schema_version():
    with pytest.raises(ValueError):
        ActionDimensionRegistry.restore({"schema_version": 99, "capacity": 8, "items": []})

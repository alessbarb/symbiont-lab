import inspect

import pytest

from symbiont.modeling import (
    CulturalAction,
    CulturalPolicy,
    CulturalPolicyConfig,
    ModeledOrganismRuntime,
    SocialChannel,
)


def test_policy_is_deterministic_and_does_not_accept_evaluator_truth():
    policy = CulturalPolicy("organism", seed=101)
    assert "ground_truth" not in inspect.signature(policy.transmission).parameters
    assert "ground_truth" not in inspect.signature(policy.composition).parameters
    assert policy.checkpoint() == CulturalPolicy.restore(policy.checkpoint(), organism_id="organism").checkpoint()


def test_autonomous_step_selects_content_and_recipient_from_local_state():
    a = ModeledOrganismRuntime(
        organism_id="a", bootstrap_semantic_senses=False,
        cultural_policy_seed=101,
        cultural_policy_config=CulturalPolicyConfig(retention_capacity=2),
    )
    b = ModeledOrganismRuntime(organism_id="b", bootstrap_semantic_senses=False)
    c = ModeledOrganismRuntime(organism_id="c", bootstrap_semantic_senses=False)
    claim = a.originate_social_claim(proposition_tokens=("native.x",), evidence_id="e.x")
    channel = SocialChannel(authorized_pairs={("a", "b"), ("a", "c")})
    decisions = ()
    for tick in range(8):
        decisions = a.autonomous_cultural_step(channel, (b, c), tick=tick)
        if any(item.selected_action is CulturalAction.TRANSMIT for item in decisions):
            break
    transmission = next(item for item in decisions if item.selected_action is CulturalAction.TRANSMIT)
    assert transmission.selected_item_ids == (claim.claim_id,)
    assert transmission.selected_recipient_id in {"b", "c"}
    assert transmission.available_options_digest
    assert a.cultural_policy.cost > 0


def test_policy_checkpoint_and_offspring_isolation_preserve_no_acquired_culture():
    runtime = ModeledOrganismRuntime(organism_id="parent", bootstrap_semantic_senses=False, cultural_policy_seed=7)
    runtime.originate_social_claim(proposition_tokens=("native.x",), evidence_id="e.x")
    runtime.autonomous_retention_step(tick=0)
    restored = ModeledOrganismRuntime.from_checkpoint(runtime.checkpoint(), bootstrap_semantic_senses=False)
    assert restored.cultural_policy.checkpoint() == runtime.cultural_policy.checkpoint()
    assert restored.social_evidence_ledger.checkpoint() == runtime.social_evidence_ledger.checkpoint()


def test_policy_bounds_options_and_allows_silence():
    with pytest.raises(ValueError):
        CulturalPolicyConfig(retention_capacity=65)
    policy = CulturalPolicy("organism", seed=1, config=CulturalPolicyConfig(max_transmissions_per_tick=0))
    runtime = ModeledOrganismRuntime(organism_id="organism", bootstrap_semantic_senses=False, cultural_policy_seed=1, cultural_policy_config=policy.config)
    runtime.originate_social_claim(proposition_tokens=("native.x",), evidence_id="e.x")
    decision = policy.transmission(runtime.social_evidence_ledger, ("neighbor",), tick=0)
    assert decision.selected_action is CulturalAction.SILENCE

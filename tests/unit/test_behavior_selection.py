import json

import pytest

from symbiont.core.behavior import (
    ActionKind,
    ActionOpportunity,
    ExpectedOutcome,
    InteroceptiveActionModel,
    LocalActionModel,
    select_action,
)
from symbiont.core.development import DevelopmentalTracker
from symbiont.core.runtime import OrganismRuntime


def opportunity(action_id, *, authorized=True, preconditions_met=True, viability=.5,
                integrity=.5, information_gain=.0, novelty=.0, uncertainty=.0, cost=.1):
    return ActionOpportunity(action_id, ActionKind(action_id), authorized, preconditions_met,
                             ExpectedOutcome(viability, integrity, 0.0, information_gain, 0.0, 0.0, 0.0),
                             cost, novelty, uncertainty)


def test_selection_never_chooses_unauthorized_or_unready_action():
    result = select_action([
        opportunity("rest", authorized=False, viability=1.0),
        opportunity("wait", preconditions_met=False, viability=1.0),
    ])
    assert result.selected is None
    assert result.rejected_count == 2


def test_selection_uses_local_pareto_frontier_and_is_deterministic():
    safe = opportunity("rest", viability=.9, integrity=.9)
    informative = opportunity("observe", viability=.2, integrity=.2, information_gain=1.0)
    dominated = opportunity("wait", viability=.1, integrity=.1)
    first = select_action([safe, informative, dominated])
    second = select_action([safe, informative, dominated])
    assert {item.action_id for item in first.frontier} == {"rest", "observe"}
    assert first.selected == second.selected


def test_exploration_can_prefer_novel_uncertain_frontier_action():
    result = select_action([
        opportunity("rest", viability=.9, integrity=.9),
        opportunity("observe", viability=.4, integrity=.4, information_gain=1.0, novelty=1.0, uncertainty=1.0),
    ], exploration=1.0)
    assert result.selected.action_id == "observe"


def test_values_and_capacity_are_bounded():
    with pytest.raises(ValueError):
        ExpectedOutcome(2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        select_action([opportunity("wait")] * 65)


def test_local_action_model_learns_bounded_outcomes_and_restores():
    model = LocalActionModel()
    base = ExpectedOutcome(.1, .1, 0.0, 0.0, 0.0, 0.0, 0.0)
    model.observe(ActionKind.INTAKE, executed=True, resource_delta=.8)
    predicted = model.predict(ActionKind.INTAKE, base)
    assert predicted.resource_change > base.resource_change
    restored = LocalActionModel.from_checkpoint(model.checkpoint())
    assert restored.predict(ActionKind.INTAKE, base) == predicted


def test_local_predictor_gets_behavioral_credit_only_when_it_beats_prior():
    model = LocalActionModel()
    prior = ExpectedOutcome(.1, .1, .0, 0.0, 0.0, 0.0, 0.0)
    for _ in range(4):
        model.observe(ActionKind.INTAKE, executed=True, viability_delta=.8,
                      integrity_delta=.7, resource_delta=.9,
                      expected=ExpectedOutcome(.8, .7, .9, 0.0, 0.0, 0.0, 0.0))

    opportunity = ActionOpportunity(
        "intake", ActionKind.INTAKE, True, True, prior, .1,
    )
    adjusted = model.adjust(opportunity)
    assert adjusted.expected.viability > prior.viability
    assert adjusted.prediction_advantage > 0.0

    untrained = model.adjust(ActionOpportunity(
        "wait", ActionKind.WAIT, True, True, prior, .1,
    ))
    assert select_action([adjusted, untrained]).selected == adjusted


def test_local_predictor_keeps_distinct_opportunity_outcomes_separate():
    model = LocalActionModel()
    prior = ExpectedOutcome(.1, .1, 0.0, 0.0, 0.0, 0.0, 0.0)
    for _ in range(3):
        model.observe(ActionKind.INTAKE, action_id="intake:resource_a", executed=True,
                      resource_delta=.8, expected=ExpectedOutcome(.1, .1, .8, 0.0, 0.0, 0.0, 0.0))
        model.observe(ActionKind.INTAKE, action_id="intake:resource_b", executed=True,
                      resource_delta=-.8, expected=ExpectedOutcome(.1, .1, -.8, 0.0, 0.0, 0.0, 0.0))

    a = model.adjust(ActionOpportunity("intake:resource_a", ActionKind.INTAKE, True, True, prior, .1))
    b = model.adjust(ActionOpportunity("intake:resource_b", ActionKind.INTAKE, True, True, prior, .1))

    assert a.expected.resource_change > prior.resource_change
    assert b.expected.resource_change < prior.resource_change
    restored = LocalActionModel.from_checkpoint(model.checkpoint())
    assert restored.adjust(ActionOpportunity("intake:resource_a", ActionKind.INTAKE, True, True, prior, .1)) == a
    assert restored.adjust(ActionOpportunity("intake:resource_b", ActionKind.INTAKE, True, True, prior, .1)) == b


def test_interoceptive_predictor_learns_separate_bounded_signal_contexts():
    model = InteroceptiveActionModel()
    learned_success = ExpectedOutcome(.8, .7, .9, 0.0, 0.0, 0.0, 0.0)
    learned_failure = ExpectedOutcome(-.8, -.7, -.9, 0.0, 0.0, 0.0, 0.0)
    for _ in range(2):
        model.observe(.1, ActionKind.INTAKE, executed=True,
                      viability_delta=.8, integrity_delta=.7, resource_delta=.9,
                      expected=learned_success)
        model.observe(.9, ActionKind.INTAKE, executed=True,
                      viability_delta=-.8, integrity_delta=-.7, resource_delta=-.9,
                      expected=learned_failure)

    prior = ExpectedOutcome(.1, .1, 0.0, 0.0, 0.0, 0.0, 0.0)
    opportunity = ActionOpportunity("intake", ActionKind.INTAKE, True, True, prior, .1)
    low_pressure = model.adjust(opportunity, signal=.1)
    high_pressure = model.adjust(opportunity, signal=.9)

    assert low_pressure.expected.resource_change > prior.resource_change
    assert high_pressure.expected.resource_change < prior.resource_change
    assert low_pressure.expected != high_pressure.expected

    restored = InteroceptiveActionModel.from_checkpoint(model.checkpoint())
    assert restored.checkpoint() == model.checkpoint()
    assert restored.adjust(opportunity, signal=.1) == low_pressure
    assert restored.adjust(opportunity, signal=.9) == high_pressure


def test_interoceptive_experience_can_change_action_selection_without_policy_rules():
    model = InteroceptiveActionModel()
    rest_expected = ExpectedOutcome(.1, .1, 0.0, 0.0, 0.0, 0.0, 0.0)
    intake_expected = ExpectedOutcome(.1, .1, .4, 0.0, 0.0, 0.0, 0.0)
    for _ in range(4):
        model.observe(.9, ActionKind.REST, executed=True,
                      viability_delta=.4, integrity_delta=.3,
                      expected=ExpectedOutcome(.4, .3, 0.0, 0.0, 0.0, 0.0, 0.0))
        model.observe(.9, ActionKind.INTAKE, executed=True,
                      viability_delta=-.4, integrity_delta=-.3, resource_delta=-.5,
                      expected=ExpectedOutcome(.1, .1, .4, 0.0, 0.0, 0.0, 0.0))

    candidates = [
        ActionOpportunity("rest", ActionKind.REST, True, True, rest_expected, .02),
        ActionOpportunity("intake", ActionKind.INTAKE, True, True, intake_expected, .01),
    ]
    adjusted = [model.adjust(item, signal=.9) for item in candidates]

    assert select_action(adjusted).selected.action_id == "rest"


def test_runtime_exposes_local_opportunities_without_mutating_state():
    runtime = OrganismRuntime(explicit_metabolism=True)
    before = runtime.metabolism.snapshot()
    opportunities = runtime.action_opportunities()
    selected = runtime.select_local_action()
    assert {item.kind for item in opportunities} >= {ActionKind.WAIT, ActionKind.REST, ActionKind.REPAIR}
    assert selected.selected is not None
    assert runtime.tick_count == 0
    assert runtime.metabolism.snapshot() == before


def test_interoceptive_pressure_does_not_encode_a_threshold_action_policy():
    runtime = OrganismRuntime(explicit_metabolism=True, autonomous_behavior=True)
    provider = runtime._interoception_provider
    assert provider is not None
    provider.update_metrics(tick_latency=0.0, epistemic_surprise=0.0, metabolic_reserve=1.0)
    abundant = {item.action_id: (item.expected, item.authorized, item.preconditions_met)
                for item in runtime.action_opportunities()}
    provider.update_metrics(tick_latency=0.0, epistemic_surprise=1.0, metabolic_reserve=0.0)
    depleted = {item.action_id: (item.expected, item.authorized, item.preconditions_met)
                for item in runtime.action_opportunities()}

    assert abundant == depleted


def test_runtime_revalidates_and_executes_selected_rest_opportunity():
    runtime = OrganismRuntime(explicit_metabolism=True)
    selected = next(item for item in runtime.action_opportunities() if item.kind is ActionKind.REST)
    result = runtime.execute_local_action(selected)
    assert result.executed is True
    assert runtime.resting_requested is True


def test_damaged_runtime_can_select_repair_from_local_expected_consequence():
    runtime = OrganismRuntime(explicit_metabolism=True, interoception_mode="absent")
    runtime.apply_environmental_damage(0.2)

    selected = runtime.select_local_action(exploration=0.0).selected

    assert selected is not None
    assert selected.kind is ActionKind.REPAIR


def test_runtime_exposes_and_executes_observe_opportunity():
    runtime = OrganismRuntime(explicit_metabolism=True)
    selected = next(item for item in runtime.action_opportunities() if item.kind is ActionKind.OBSERVE)

    result = runtime.execute_local_action(selected)

    assert result.executed is True
    assert result.reason is None
    assert runtime.action_evidence[-1].outcome == "observation"


def test_runtime_tick_emits_bounded_lifecycle_events():
    runtime = OrganismRuntime(explicit_metabolism=True)
    result = runtime.tick()
    second = runtime.tick()

    assert "development" in result.runtime_events
    assert "first_sense" in result.runtime_events
    assert "first_sense" not in second.runtime_events
    assert all(isinstance(event, str) and len(event) <= 32 for event in result.runtime_events)
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint())
    assert "first_sense" not in restored.tick().runtime_events


def test_runtime_rejects_stale_unready_opportunity():
    runtime = OrganismRuntime(explicit_metabolism=True)
    selected = next(item for item in runtime.action_opportunities() if item.kind is ActionKind.REST)
    stale = ActionOpportunity(selected.action_id, selected.kind, True, False,
                              selected.expected, selected.cost)
    result = runtime.execute_local_action(stale)
    assert result.executed is False
    assert result.reason == "stale_or_unavailable"


def test_autonomous_action_step_composes_selection_and_execution():
    runtime = OrganismRuntime(explicit_metabolism=True)
    result = runtime.autonomous_action_step()
    assert result.executed is True
    assert result.action_id in {"wait", "rest"}


def test_action_evidence_is_bounded_and_checkpoint_safe():
    runtime = OrganismRuntime(explicit_metabolism=True)
    selected = next(item for item in runtime.action_opportunities() if item.kind is ActionKind.REST)
    runtime.execute_local_action(selected)

    assert runtime.action_evidence[-1].outcome == "rest_requested"
    encoded = json.dumps(runtime.checkpoint(), allow_nan=False)
    assert "_physiology" not in encoded
    restored = OrganismRuntime.from_checkpoint(json.loads(encoded), explicit_metabolism=True)
    assert restored.action_evidence == runtime.action_evidence


def test_pending_action_observation_survives_checkpoint():
    runtime = OrganismRuntime(explicit_metabolism=True)
    selected = next(item for item in runtime.action_opportunities() if item.kind is ActionKind.REST)
    runtime.execute_local_action(selected)

    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(), explicit_metabolism=True)
    assert restored.checkpoint()["pending_action_observation"]["kind"] == "rest"
    restored.tick()
    assert restored.checkpoint()["action_model"]["stats"]["rest"]["attempts"] == 1


def test_pending_action_observation_uses_pre_action_interoceptive_signal(monkeypatch):
    runtime = OrganismRuntime(
        explicit_metabolism=True,
        autonomous_behavior=True,
    )
    provider = runtime._interoception_provider
    assert provider is not None
    signals = iter((0.1, 0.2, 0.8))
    monkeypatch.setattr(provider, "local_action_pressure", lambda: next(signals))

    selected = next(item for item in runtime.action_opportunities() if item.kind is ActionKind.REST)
    runtime.execute_local_action(selected)

    assert runtime.checkpoint()["pending_action_observation"]["signal"] == 0.8


def test_malformed_action_evidence_is_rejected_as_checkpoint_error():
    runtime = OrganismRuntime(explicit_metabolism=True)
    payload = runtime.checkpoint()
    payload["action_evidence"] = [{"tick": 0, "action_id": "wait", "kind": "wait"}]
    with pytest.raises(ValueError, match="action evidence"):
        OrganismRuntime.from_checkpoint(payload, explicit_metabolism=True)


def test_autonomous_behavior_can_be_enabled_as_part_of_the_tick_cycle():
    runtime = OrganismRuntime(explicit_metabolism=True, autonomous_behavior=True)
    result = runtime.tick()
    assert result.action_result is not None
    assert result.action_result.executed is True
    assert len(runtime.action_evidence) == 1


def test_autonomous_rest_does_not_permanently_lock_the_runtime():
    runtime = OrganismRuntime(autonomous_behavior=True, explicit_metabolism=True)
    runtime.request_rest()
    runtime.tick()
    assert runtime.resting_requested is False


def test_action_prediction_is_updated_from_the_following_cycle():
    runtime = OrganismRuntime(explicit_metabolism=True, autonomous_behavior=True)
    runtime.tick()
    before = runtime.checkpoint()["action_model"]["stats"]
    assert before == {}
    runtime.tick()
    after = runtime.checkpoint()["action_model"]["stats"]
    assert sum(item["attempts"] for item in after.values()) == 1
    assert all(0.0 <= item["mean_prediction_error"] <= 1.0 for item in after.values())


def test_autonomous_behavior_configuration_survives_checkpoint():
    runtime = OrganismRuntime(
        explicit_metabolism=True, autonomous_behavior=True, behavior_exploration=0.7
    )
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(), explicit_metabolism=True)
    assert restored.effective_configuration()["autonomous_behavior"] is True
    assert restored.effective_configuration()["behavior_exploration"] == 0.7


def test_social_partner_loss_removes_only_the_opaque_presence_opportunity():
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.social import SocialHabitat

    habitat = SocialHabitat(EcologicalResourcePool({"channel": 1.0}), max_members=2)
    runtime = OrganismRuntime(organism_id="observer", social_habitat=habitat,
                              bootstrap_semantic_senses=False, discover_senses=False)
    assert runtime.join_social_habitat(habitat)
    assert habitat.admit("partner")
    assert len(runtime.observe_social_presence()) == 1
    assert habitat.release("partner")
    assert runtime.observe_social_presence() == ()


def test_negative_local_social_evidence_exposes_bounded_competition_action():
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.social import SocialHabitat

    habitat = SocialHabitat(EcologicalResourcePool({"channel": 1.0}), max_members=2)
    runtime = OrganismRuntime(organism_id="observer", social_habitat=habitat,
                              bootstrap_semantic_senses=False, discover_senses=False,
                              explicit_metabolism=True)
    assert runtime.join_social_habitat(habitat)
    assert habitat.admit("partner")
    runtime._social_ledger.observe("observer", "partner", cost=0.5,
                                   tick=0, channel="channel")

    opportunity = next(item for item in runtime.action_opportunities()
                       if item.kind is ActionKind.COMPETE)
    result = runtime.execute_local_action(opportunity)

    assert result.executed is True
    assert result.action_id == "compete"
    assert runtime.action_evidence[-1].outcome == "competition"


def test_parent_death_releases_shared_boundaries_without_killing_offspring():
    from dataclasses import replace
    from importlib import resources
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.reproduction import ReproductivePressure
    from symbiont.core.social import SocialHabitat
    from symbiont.core.physiology import PhysiologyController, VitalState

    payload = json.loads(resources.files("symbiont.cognition").joinpath(
        "defaults/base-genome.json").read_text())
    genome = replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")
    authority = HabitatBirthAuthority(habitat_id="lineage", capacity=2, resource_budget=2.0)
    social = SocialHabitat(EcologicalResourcePool({"channel": 2.0}), max_members=2)
    metabolism = MetabolicLedger(
        replenishment={kind: 0.0 for kind in ("observation", "cognition", "persistence", "maintenance")}
    )
    parent = OrganismRuntime(
        organism_id="parent", genome=genome, birth_authority=authority,
        reproductive_pressure=ReproductivePressure(threshold_ticks=1),
        social_habitat=social, metabolism=metabolism, explicit_metabolism=True,
        bootstrap_semantic_senses=False, discover_senses=False,
    )
    assert parent.join_social_habitat(social)
    parent.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    child = parent.materialize_clonal_bud()
    assert child is not None and child.join_social_habitat(social)
    assert set(social.members) == {"parent", child.organism_id}

    metabolism.charge("maintenance", 2.0)
    death = parent.tick()
    assert death.physiology.state is VitalState.DEAD
    assert "parent" not in social.members
    assert child.organism_id in social.members
    assert child.organism_id in authority.live_ids
    assert child.tick().physiology.state is not VitalState.DEAD


def test_autonomous_birth_mutates_bounded_heritable_layer_and_restores_it():
    from dataclasses import replace
    from importlib import resources
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.heredity import HeritableGenome
    from symbiont.core.reproduction import ReproductivePressure

    payload = json.loads(resources.files("symbiont.cognition").joinpath(
        "defaults/base-genome.json").read_text())
    genome = replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")
    authority = HabitatBirthAuthority(habitat_id="lineage", capacity=2, resource_budget=2.0)
    parent = OrganismRuntime(
        organism_id="parent", genome=genome,
        heritable_genome=HeritableGenome("founder", (("learning_rate", 0.2),)),
        mutation_seed=3, birth_authority=authority,
        reproductive_pressure=ReproductivePressure(threshold_ticks=1),
        bootstrap_semantic_senses=False, discover_senses=False,
    )
    parent.observe_reproductive_pressure(adaptive=True, capacity_exhausted=True, blocked_growth=True)
    child = parent.materialize_clonal_bud()
    assert child is not None
    assert child.heritable_genome is not None
    assert child.heritable_genome != parent.heritable_genome
    assert child.genome is not None and child.genome.genome_id == child.heritable_genome.identity
    assert child.genome.parent_ids == (parent.genome.genome_id,)
    assert 0.0 <= child.genome.plasticity.learning_rate.initial <= 1.0

    restored = OrganismRuntime.from_checkpoint(parent.checkpoint(), birth_authority=authority,
                                               bootstrap_semantic_senses=False)
    assert restored.heritable_genome == parent.heritable_genome
    assert restored.checkpoint()["mutation_seed"] == 3


def test_epigenetic_prior_is_coarse_and_decays_without_transmitting_knowledge():
    from symbiont.core.inheritance import EpigeneticPrior

    runtime = OrganismRuntime(
        epigenetic_priors=(EpigeneticPrior("exploration_bias", 1.0),),
        epigenetic_decay=0.5,
    )
    assert runtime.epigenetic_priors[0].value == 1.0
    runtime.tick()
    assert runtime.epigenetic_priors[0].value == 0.5
    restored = OrganismRuntime.from_checkpoint(runtime.checkpoint())
    assert restored.epigenetic_priors == runtime.epigenetic_priors
    assert all(item.key != "resource_17" for item in restored.epigenetic_priors)


def test_checkpoints_are_available_during_stress_and_dormancy_but_not_after_death():
    from symbiont.core.physiology import PhysiologyController, VitalState

    for state in (VitalState.STRESSED, VitalState.DORMANT):
        runtime = OrganismRuntime(
            physiology=PhysiologyController(state=state),
            explicit_metabolism=True,
            bootstrap_semantic_senses=False,
            discover_senses=False,
        )
        restored = OrganismRuntime.from_checkpoint(runtime.checkpoint(),
                                                   explicit_metabolism=True,
                                                   bootstrap_semantic_senses=False,
                                                   discover_senses=False)
        assert restored.checkpoint()["physiology"]["state"] == state.value

    runtime = OrganismRuntime(explicit_metabolism=True,
                              bootstrap_semantic_senses=False,
                              discover_senses=False)
    runtime.metabolism.charge("maintenance", 2.0)
    before_death = runtime.checkpoint()
    assert before_death["physiology"]["state"] == "active"
    result = runtime.tick()
    assert result.physiology.state is VitalState.DEAD
    with pytest.raises(ValueError):
        OrganismRuntime.from_checkpoint(runtime.checkpoint(), explicit_metabolism=True)


def test_reproduction_opportunity_requires_a_slot_but_pressure_is_developmental():
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.reproduction import ReproductivePressure

    authority = HabitatBirthAuthority(habitat_id="h", capacity=2, resource_budget=2.0)
    runtime = OrganismRuntime(
        organism_id="parent", birth_authority=authority,
        reproductive_pressure=ReproductivePressure(threshold_ticks=1),
        explicit_metabolism=True, bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    runtime.observe_reproductive_pressure(
        adaptive=True, capacity_exhausted=True, blocked_growth=True
    )
    reproduction = next(item for item in runtime.action_opportunities()
                        if item.kind.value == "reproduce")
    assert reproduction.authorized is True
    assert reproduction.preconditions_met is True

    full = HabitatBirthAuthority(habitat_id="full", capacity=1, resource_budget=1.0)
    blocked = OrganismRuntime(
        organism_id="only", birth_authority=full,
        reproductive_pressure=ReproductivePressure(threshold_ticks=1),
        explicit_metabolism=True, bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    blocked.observe_reproductive_pressure(
        adaptive=True, capacity_exhausted=True, blocked_growth=True
    )
    unavailable = next(item for item in blocked.action_opportunities()
                       if item.kind.value == "reproduce")
    assert unavailable.authorized is False


def test_denied_reproduction_is_not_reported_as_executed(monkeypatch):
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.reproduction import ReproductivePressure

    runtime = OrganismRuntime(
        organism_id="parent",
        birth_authority=HabitatBirthAuthority(habitat_id="h", capacity=2, resource_budget=2.0),
        reproductive_pressure=ReproductivePressure(threshold_ticks=1),
        explicit_metabolism=True, bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    runtime.observe_reproductive_pressure(
        adaptive=True, capacity_exhausted=True, blocked_growth=True
    )
    opportunity = next(item for item in runtime.action_opportunities()
                       if item.kind.value == "reproduce")
    monkeypatch.setattr(runtime, "materialize_clonal_bud", lambda: None)

    result = runtime.execute_local_action(opportunity)

    assert result.executed is False
    assert result.reason == "birth_denied"
    assert runtime.action_evidence[-1].outcome == "reproduction_denied"
    assert runtime.action_evidence[-1].executed is False


def test_autonomous_reproductive_pressure_advances_once_per_tick():
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.reproduction import ReproductivePressure

    pressure = ReproductivePressure(threshold_ticks=3)
    runtime = OrganismRuntime(
        organism_id="parent",
        birth_authority=HabitatBirthAuthority(habitat_id="h", capacity=2, resource_budget=2.0),
        reproductive_pressure=pressure,
        autonomous_behavior=True,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    runtime.homeostasis.integrity = 0.5
    runtime.tick()
    runtime.tick()
    assert pressure.blocked_ticks == 1


def test_opaque_resource_surfaces_are_separate_local_intake_choices():
    from symbiont.core.ecology import SharedHabitat

    first = SharedHabitat(habitat_id="surface-a", capacity=1, resources=2.0)
    second = SharedHabitat(habitat_id="surface-b", capacity=1, resources=2.0)
    runtime = OrganismRuntime(
        organism_id="org", resource_habitats={"opaque_a": first, "opaque_b": second},
        explicit_metabolism=True, bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    for habitat in (first, second):
        habitat.set_environment_resources(2.0)
    runtime.metabolism.charge("maintenance", 0.2)

    choices = [item for item in runtime.action_opportunities()
               if item.action_id.startswith("intake:")]
    assert {item.action_id for item in choices} == {"intake:opaque_a", "intake:opaque_b"}
    selected = next(item for item in choices if item.action_id == "intake:opaque_b")
    result = runtime.execute_local_action(selected)
    assert result.executed is True
    assert second.snapshot().available_resources < first.snapshot().available_resources


def test_interoception_can_be_ablated_without_changing_other_runtime_bounds():
    enabled = OrganismRuntime(discover_senses=True, interoception_enabled=True)
    disabled = OrganismRuntime(discover_senses=True, interoception_enabled=False)
    enabled_result = enabled.tick()
    disabled_result = disabled.tick()
    enabled_ids = {capability.capability_id for capability in enabled_result.snapshot.manifest.available}
    disabled_ids = {capability.capability_id for capability in disabled_result.snapshot.manifest.available}
    assert any(capability_id.startswith("internal.") for capability_id in enabled_ids)
    assert not any(capability_id.startswith("internal.") for capability_id in disabled_ids)
    assert enabled.effective_configuration()["interoception_enabled"] is True
    assert disabled.effective_configuration()["interoception_enabled"] is False


def test_runtime_accepts_external_lifecycle_for_sensor_disappearance_and_return():
    from symbiont.host.contracts import Capability, CapabilityKind
    from symbiont.host.discovery import HostDiscovery
    from symbiont.host.lifecycle import HostLifecycle

    class Discovery:
        provider_id = "synthetic_sensor"
        available = True

        def discover(self):
            return (
                (Capability("signal.synthetic", CapabilityKind.SIGNAL, self.provider_id),)
                if self.available else ()
            )

    class Reader:
        provider_id = "synthetic_sensor"

        def sample(self, capabilities):
            return ()

    discovery = Discovery()
    lifecycle = HostLifecycle(
        discovery=HostDiscovery((discovery,)), reading_providers=(Reader(),)
    )
    runtime = OrganismRuntime(
        host_lifecycle=lifecycle,
        host_reading_providers=(Reader(),),
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    assert runtime.tick().snapshot.manifest.supports("signal.synthetic")
    discovery.available = False
    assert not runtime.tick().snapshot.manifest.supports("signal.synthetic")
    discovery.available = True
    assert runtime.tick().snapshot.manifest.supports("signal.synthetic")


def test_runtime_exposes_derived_ontogenetic_phase_and_checkpoints_history():
    runtime = OrganismRuntime(bootstrap_semantic_senses=False, discover_senses=False)
    first = runtime.tick()
    assert first.development is not None
    assert first.development.phase.value == "germinal"

    restored = OrganismRuntime.from_checkpoint(
        runtime.checkpoint(), bootstrap_semantic_senses=False, discover_senses=False
    )
    second = restored.tick()
    assert second.development is not None
    assert second.development.tick == 2


def test_developmental_decline_uses_accumulated_burden_not_an_age_counter():
    tracker = DevelopmentalTracker()
    snapshot = None
    for _ in range(10):
        snapshot = tracker.observe(
            state="active", integrity=0.7, topology_health="adaptive",
            sensory_count=4, action_attempts=12, maintenance_ratio=0.9,
            retained_items=64, degradation_excreted=1, repaired=True,
            plasticity_enabled=False,
        )

    assert snapshot is not None
    assert snapshot.phase.value == "declining"
    assert snapshot.repair_events == 10
    assert snapshot.excretion_events == 10
    assert snapshot.senescence_index > 0.55

    restored = DevelopmentalTracker.from_checkpoint(tracker.checkpoint())
    continued = restored.observe(
        state="active", integrity=0.7, topology_health="adaptive",
        sensory_count=4, action_attempts=12,
    )
    assert continued.senescence_index > 0.0

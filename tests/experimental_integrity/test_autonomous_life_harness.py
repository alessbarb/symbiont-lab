from dataclasses import dataclass
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))

import pytest

from research.autonomous_life.harness import (
    AutonomousLifeHarness,
    HarnessConfig,
    LifeEvent,
    LifeTrace,
    SubjectObservation,
    run_autonomous_life,
)
from research.autonomous_life.genesis import build_genesis_harness


@dataclass
class FakeResult:
    action_result: object | None = None
    physiology: object | None = None
    metabolism: object | None = None


class FakeOrganism:
    def __init__(self, organism_id: str):
        self.organism_id = organism_id
        self.ticks = 0

    def tick(self):
        self.ticks += 1
        return FakeResult()

    def checkpoint(self):
        return {"organism_id": self.organism_id, "ticks": self.ticks}


class OrganismDeadError(RuntimeError):
    pass


class DeadOrganism(FakeOrganism):
    def tick(self):
        raise OrganismDeadError()


class ResultDeadOrganism(FakeOrganism):
    def tick(self):
        return FakeResult(physiology=type("Physiology", (), {
            "state": type("State", (), {"value": "dead"})(),
        })())


class InfrastructureFailure(FakeOrganism):
    def tick(self):
        raise RuntimeError("infrastructure failure")


class ChildProducingOrganism(FakeOrganism):
    def __init__(self, organism_id: str):
        super().__init__(organism_id)
        self.child = FakeOrganism(f"{organism_id}-child")

    def tick(self):
        self.ticks += 1
        if self.ticks == 1:
            return FakeResult(action_result=type("Action", (), {
                "executed": True, "action_id": "reproduce", "result": self.child
            })())
        return FakeResult()


def config(**overrides):
    return HarnessConfig(ticks=6, checkpoint_interval=2, random_checkpoint_count=2, **overrides)


def test_harness_keeps_environment_schedule_out_of_organism_tick():
    organisms = [FakeOrganism(f"org-{index}") for index in range(8)]
    trace = AutonomousLifeHarness(organisms, config=config()).run()

    assert [item.regime for item in trace.environment] == [
        "abundance", "scarcity", "shift", "recovery", "novelty", "novelty"
    ]
    assert all(organism.ticks == 6 for organism in organisms)
    assert all(record.event in {LifeEvent.BIRTH, LifeEvent.DEVELOPMENT, LifeEvent.LEARNING, LifeEvent.CHECKPOINT}
               for record in trace.records)
    assert len(trace.checkpoints) >= 8
    metrics = trace.metrics()
    assert metrics.births == 8
    assert metrics.deaths == 0
    assert metrics.population_peak == 8
    assert metrics.final_population == 8
    assert metrics.mean_population == 8.0
    assert metrics.regime_counts == {
        "abundance": 1, "scarcity": 1, "shift": 1,
        "recovery": 1, "novelty": 2,
    }


def test_evaluator_metrics_cover_subject_development_and_ecology_without_feedback():
    trace = LifeTrace(
        records=[
            # The metric input is apparatus-owned, not supplied to a tick.
            type("Record", (), {"event": LifeEvent.BIRTH, "organism_id": "a", "tick": 0})(),
            type("Record", (), {"event": LifeEvent.DEATH, "organism_id": "a", "tick": 3})(),
        ],
        population=[(1, 1), (2, 1), (3, 0)],
        observations=[
            SubjectObservation(1, "a", "active", integrity=.9, reserve=.8,
                               phase="developing", sensory_count=1,
                               topology_health="developing", prediction_error=.1,
                               action_attempts=1, resource_id="opaque_a", resource_amount=.2),
            SubjectObservation(2, "a", "active", integrity=.95, reserve=.7,
                               phase="juvenile", sensory_count=2,
                               topology_health="adaptive", prediction_error=.1,
                               action_attempts=2, resource_id="opaque_b", resource_amount=.3),
            SubjectObservation(3, "a", "dead", integrity=0.0, reserve=-1.0,
                               phase="dead", sensory_count=2,
                               topology_health="adaptive", prediction_error=.1,
                               action_attempts=2),
            SubjectObservation(2, "b", "active", integrity=.95, reserve=.7,
                               phase="juvenile", sensory_count=2,
                               topology_health="adaptive", prediction_error=.1,
                               action_attempts=2, resource_id="opaque_b", resource_amount=.3),
        ],
    )

    metrics = trace.metrics()

    assert metrics.mean_lifespan == 3.0
    assert metrics.viability_transitions == 1
    assert metrics.time_to_first_cognitive_path == {"a": 2, "b": 2}
    assert metrics.time_to_stable_prediction == {"a": 1}
    assert metrics.resource_distribution == {"opaque_a": .2, "opaque_b": .6}
    assert metrics.phenotypic_diversity == 3
    assert metrics.niche_overlap == pytest.approx(.5)
    assert metrics.carrying_capacity_occupancy == pytest.approx(2 / 96)


def test_harness_defaults_are_bounded_and_reject_invalid_population():
    with pytest.raises(ValueError, match="population"):
        HarnessConfig(population=7)
    with pytest.raises(ValueError, match="resource_classes"):
        HarnessConfig(resource_classes=("a", "b"))
    with pytest.raises(ValueError, match="adversarial"):
        HarnessConfig(adversarial_conditions=("unknown",))


def test_adversarial_matrix_covers_the_full_life_cycle_protocol():
    from research.autonomous_life.scenarios import (
        AdversarialScenario, SCENARIO_MATRIX, validate_scenario_matrix,
    )

    validate_scenario_matrix()
    assert {item.scenario for item in SCENARIO_MATRIX} == set(AdversarialScenario)
    assert len(SCENARIO_MATRIX) == len(AdversarialScenario)
    assert all(item.apparatus_surface and item.invariant for item in SCENARIO_MATRIX)


def test_lineage_measurement_is_evaluator_only_and_detects_extinction():
    from research.autonomous_life.evolution import measure_lineages
    from symbiont.core.birth_authority import HabitatBirthAuthority

    authority = HabitatBirthAuthority(habitat_id="evolution", capacity=3, resource_budget=3.0)
    first = authority.birth(genome_id="genome_a", generation=0)
    second = authority.birth(genome_id="genome_b", generation=1)
    assert first is not None and second is not None
    authority.death(first.organism_id)
    snapshot = measure_lineages(authority)

    assert snapshot.live_population == 1
    assert snapshot.live_genome_frequencies == {"genome_b": 1}
    assert snapshot.extinct_genomes == ("genome_a",)
    assert snapshot.observed_generations == (0, 1)
    assert snapshot.deaths == 1
    assert snapshot.genetic_diversity == 2
    assert snapshot.lineage_persistence == {"genome_a": 0.0, "genome_b": 1.0}
    assert snapshot.selection_differentials == {"genome_a": -0.5, "genome_b": 0.5}
    assert snapshot.offspring_viability is None
    assert not hasattr(snapshot, "fitness")


def test_lineage_measurement_reports_descendant_cohort_viability():
    from research.autonomous_life.evolution import measure_lineages
    from symbiont.core.birth_authority import HabitatBirthAuthority

    authority = HabitatBirthAuthority(habitat_id="offspring", capacity=3, resource_budget=3.0)
    parent = authority.register_existing(organism_id="parent", genome_id="genome_a")
    assert parent is not None
    child = authority.birth(genome_id="genome_b", parent_ids=("parent",), generation=1)
    assert child is not None

    snapshot = measure_lineages(authority)
    assert snapshot.offspring_viability == 1.0
    authority.death(child.organism_id)
    assert measure_lineages(authority).offspring_viability == 0.0


def test_life_metrics_include_evaluator_lineage_viability():
    from research.autonomous_life.evolution import measure_lineages
    from symbiont.core.birth_authority import HabitatBirthAuthority

    authority = HabitatBirthAuthority(habitat_id="metrics", capacity=2, resource_budget=2.0)
    parent = authority.register_existing(organism_id="parent", genome_id="founder")
    assert parent is not None
    child = authority.birth(genome_id="child", parent_ids=("parent",), generation=1)
    assert child is not None
    trace = LifeTrace(evolutionary=[measure_lineages(authority)])

    assert trace.metrics().offspring_viability == 1.0


def test_harness_records_lineage_measurements_after_each_population_tick():
    from research.autonomous_life.evolution import measure_lineages
    from symbiont.core.birth_authority import HabitatBirthAuthority

    organisms = [FakeOrganism(f"org-{index}") for index in range(8)]
    authority = HabitatBirthAuthority(habitat_id="run", capacity=8, resource_budget=8.0)
    for organism in organisms:
        assert authority.register_existing(organism_id=organism.organism_id, genome_id="genome_a")
    trace = AutonomousLifeHarness(
        organisms, config=HarnessConfig(ticks=3, checkpoint_interval=2,
                                        random_checkpoint_count=1),
        birth_authority=authority,
    ).run()

    assert len(trace.evolutionary) == 3
    assert trace.evolutionary[-1] == measure_lineages(authority)
    assert trace.evolutionary[-1].live_genome_frequencies == {"genome_a": 8}
    assert "fitness" not in trace.as_dict()["evolutionary"][0]


def test_harness_factory_is_the_only_population_construction_boundary():
    seen = []

    def factory(population, selected):
        seen.append((population, selected.regimes))
        return [FakeOrganism(f"org-{index}") for index in range(population)]

    trace = run_autonomous_life(factory, config=config())
    assert seen == [(8, ("abundance", "scarcity", "shift", "recovery", "novelty"))]
    assert len(trace.environment) == 6


def test_generations_extend_the_longitudinal_horizon_and_schedule():
    organisms = [FakeOrganism(f"org-{index}") for index in range(8)]
    trace = AutonomousLifeHarness(organisms, config=config(generations=2)).run()

    assert len(trace.environment) == 12
    assert all(organism.ticks == 12 for organism in organisms)
    assert trace.environment[0].regime == "abundance"
    assert trace.environment[-1].regime == "novelty"


def test_harness_registers_organism_created_offspring_without_directing_birth():
    organisms = [ChildProducingOrganism("org-0")] + [FakeOrganism(f"org-{i}") for i in range(1, 8)]
    trace = AutonomousLifeHarness(organisms, config=config()).run()

    assert any(record.organism_id == "org-0-child" and record.event is LifeEvent.BIRTH
               for record in trace.records)
    assert organisms[0].child.ticks == 5


def test_harness_does_not_hide_infrastructure_failures_as_death():
    organisms = [InfrastructureFailure("org-0")] + [FakeOrganism(f"org-{i}") for i in range(1, 8)]
    with pytest.raises(RuntimeError, match="infrastructure failure"):
        AutonomousLifeHarness(organisms, config=config()).run()


def test_harness_removes_organisms_that_report_irreversible_death():
    organisms = [ResultDeadOrganism(f"org-{index}") for index in range(8)]
    trace = AutonomousLifeHarness(
        organisms,
        config=HarnessConfig(ticks=1, checkpoint_interval=1, random_checkpoint_count=0),
    ).run()
    assert sum(record.event is LifeEvent.DEATH for record in trace.records) == 8
    assert sum(record.event is LifeEvent.RESOURCE_RELEASE for record in trace.records) == 8
    assert trace.metrics().mean_lifespan == 1.0
    assert trace.metrics().final_population == 0
    assert trace.metrics().extinction_events == 1


def test_harness_removes_organisms_that_reject_ticks_after_death():
    organisms = [DeadOrganism(f"org-{index}") for index in range(8)]
    trace = AutonomousLifeHarness(
        organisms,
        config=HarnessConfig(ticks=2, checkpoint_interval=1, random_checkpoint_count=0),
    ).run()
    assert trace.metrics().deaths == 8
    assert trace.metrics().final_population == 0
    assert trace.metrics().extinction_events == 1


def test_harness_checkpoint_restores_environment_rng_and_organism_state():
    from symbiont.core.ecology import SharedHabitat

    organisms = [FakeOrganism(f"org-{index}") for index in range(8)]
    habitats = {
        name: SharedHabitat(habitat_id=name, capacity=8, resources=1.0)
        for name in config().resource_classes
    }
    original = AutonomousLifeHarness(organisms, config=config(), resource_habitats=habitats)
    original.run(max_ticks=3)
    checkpoint = json.loads(json.dumps(original.checkpoint()))
    checkpointed_resources = {
        name: habitat.snapshot().available_resources for name, habitat in habitats.items()
    }
    for habitat in habitats.values():
        habitat.set_environment_resources(0.0)

    def restore(payload):
        organism = FakeOrganism(payload["organism_id"])
        organism.ticks = payload["ticks"]
        return organism

    restored = AutonomousLifeHarness.from_checkpoint(
        checkpoint, config=config(), organism_restorer=restore,
        resource_habitats=habitats,
    )
    assert {
        name: habitat.snapshot().available_resources for name, habitat in habitats.items()
    } == checkpointed_resources
    continuation = restored.run()
    assert len(continuation.environment) == 3
    assert [snapshot.regime for snapshot in continuation.environment] == [
        "recovery", "novelty", "novelty"
    ]
    assert all(organism.ticks == 6 for organism in restored._organisms)


def test_harness_records_recovery_as_a_transition_not_as_a_regime_label():
    @dataclass
    class Physiology:
        state: object

    class TransitioningOrganism(FakeOrganism):
        def tick(self):
            self.ticks += 1
            state = type("State", (), {"value": "stressed" if self.ticks == 1 else "active"})()
            return FakeResult(physiology=Physiology(state))

    organisms = [TransitioningOrganism("org-0")] + [FakeOrganism(f"org-{i}") for i in range(1, 8)]
    trace = AutonomousLifeHarness(organisms, config=config()).run()
    assert any(record.organism_id == "org-0" and record.event is LifeEvent.RECOVERY
               for record in trace.records)


def test_harness_records_repair_attempts_even_when_repair_yields_no_change():
    class FailedRepairOrganism(FakeOrganism):
        def tick(self):
            self.ticks += 1
            return FakeResult(action_result=type("Action", (), {
                "executed": True, "action_id": "repair", "result": 0.0,
            })())

    organisms = [FailedRepairOrganism("org-0")] + [FakeOrganism(f"org-{i}") for i in range(1, 8)]
    trace = AutonomousLifeHarness(organisms, config=config()).run()
    assert trace.metrics().repair_events == 6


def test_environment_applies_quantities_to_opaque_surfaces_without_exposing_regime():
    from symbiont.core.ecology import SharedHabitat

    habitats = {
        name: SharedHabitat(habitat_id=name, capacity=8, resources=1.0)
        for name in config().resource_classes
    }
    organisms = [FakeOrganism(f"org-{index}") for index in range(8)]
    trace = AutonomousLifeHarness(organisms, config=config(), resource_habitats=habitats).run()

    assert habitats["resource_a"].snapshot().available_resources == 0.1
    assert trace.environment[0].regime == "abundance"
    # Fake organisms have no environment argument or regime observation path.
    assert all(organism.ticks == 6 for organism in organisms)


def test_adversarial_conditions_change_only_opaque_resource_quantities():
    from symbiont.core.ecology import SharedHabitat

    selected = config(adversarial_conditions=(
        "false_correlations", "resource_inversion", "stale_resources",
    ))
    habitats = {
        name: SharedHabitat(habitat_id=name, capacity=8, resources=1.0)
        for name in selected.resource_classes
    }
    assert habitats["resource_a"].admit("org-0", 0.2)
    organisms = [FakeOrganism(f"org-{index}") for index in range(8)]
    trace = AutonomousLifeHarness(
        organisms, config=selected, resource_habitats=habitats,
    ).run(max_ticks=2)

    assert all(snapshot.resources == tuple((name, 0.0) for name in selected.resource_classes)
               for snapshot in trace.environment)
    assert all(habitat.snapshot().available_resources == 0.0 for habitat in habitats.values())
    assert habitats["resource_a"].has_allocation("org-0")
    # The evaluator retains its condition/regime labels in the trace, but the
    # organism-facing fake API received neither argument nor directive.
    assert trace.environment[0].regime == "abundance"
    assert all(organism.ticks == 2 for organism in organisms)


def test_damage_pulses_cross_only_as_integrity_change_and_enable_repair_measurement():
    selected = config(damage_pulses=(2,))

    class DamagedFake(FakeOrganism):
        def __init__(self, organism_id):
            super().__init__(organism_id)
            self.integrity = 1.0

        def apply_environmental_damage(self, amount):
            self.integrity -= amount
            return amount

        def tick(self):
            self.ticks += 1
            return FakeResult(physiology=type("P", (), {"state": type("S", (), {"value": "active"})()})())

    organisms = [DamagedFake(f"org-{index}") for index in range(8)]
    trace = AutonomousLifeHarness(organisms, config=selected).run()
    assert trace.metrics().repair_events == 0
    assert sum(record.event is LifeEvent.DAMAGE for record in trace.records) == 8
    assert all(organism.integrity == 0.8 for organism in organisms)


def test_harness_checkpoint_restores_social_and_birth_boundaries_in_place():
    from symbiont.core.birth_authority import HabitatBirthAuthority
    from symbiont.core.interactions import EcologicalResourcePool
    from symbiont.core.social import SocialHabitat

    organisms = [FakeOrganism(f"org-{index}") for index in range(8)]
    social = SocialHabitat(EcologicalResourcePool({"opaque": 3.0}), max_members=8)
    for organism in organisms:
        assert social.admit(organism.organism_id)
    authority = HabitatBirthAuthority(habitat_id="lineage", capacity=8, resource_budget=8.0)
    for organism in organisms:
        assert authority.register_existing(organism_id=organism.organism_id, genome_id="g")

    harness = AutonomousLifeHarness(
        organisms, config=config(), social_habitat=social, birth_authority=authority,
    )
    harness.run(max_ticks=1)
    checkpoint = json.loads(json.dumps(harness.checkpoint()))
    expected_members = social.members
    expected_budget = authority.resource_budget
    social.release("org-0")
    authority.death("org-0")

    def restore(payload):
        organism = FakeOrganism(payload["organism_id"])
        organism.ticks = payload["ticks"]
        return organism

    AutonomousLifeHarness.from_checkpoint(
        checkpoint, config=config(), organism_restorer=restore,
        social_habitat=social, birth_authority=authority,
    )
    assert social.members == expected_members
    assert authority.live_ids == expected_members
    assert authority.resource_budget == expected_budget


def test_genesis_builds_identical_germinal_population_behind_apparatus_boundaries():
    selected = HarnessConfig(population=8, generations=1, ticks=1,
                             checkpoint_interval=1, random_checkpoint_count=0)
    harness = build_genesis_harness(selected)
    # Founder admission is transactional and reserves one unit on each
    # surface; Genesis must leave a finite surplus for actual acquisition.
    assert all(
        habitat.snapshot().available_resources > 0.0
        for habitat in harness._resource_habitats.values()
    )
    trace = harness.run()

    assert trace.metrics().births == 8
    assert trace.population == [(1, 8)]
    assert sum(record.event is LifeEvent.FIRST_SENSE for record in trace.records) == 8
    assert len(trace.evolutionary) == 1
    assert len(trace.evolutionary[0].observed_genomes) == 1
    assert set(trace.evolutionary[0].live_generation_frequencies) == {0}


def test_genesis_can_hold_founder_cohort_fixed_for_matched_ablations():
    selected = HarnessConfig(
        population=8, generations=1, ticks=32,
        checkpoint_interval=32, random_checkpoint_count=0,
    )
    trace = build_genesis_harness(selected, reproduction_enabled=False).run()

    assert trace.metrics().births == 8
    assert trace.metrics().reproduction_events == 0
    assert trace.metrics().organism_count == 8


def test_genesis_produces_autonomous_descendants_and_heritable_divergence():
    selected = HarnessConfig(
        population=8, generations=1, ticks=600, checkpoint_interval=600,
        random_checkpoint_count=0,
    )
    trace = build_genesis_harness(selected).run()
    metrics = trace.metrics()
    evolutionary = trace.evolutionary[-1]

    assert metrics.reproduction_events > 0
    assert metrics.interaction_events > 0
    assert any(record.event is LifeEvent.FIRST_CONCEPT for record in trace.records)
    assert any(record.event is LifeEvent.FIRST_PREDICTION for record in trace.records)
    assert evolutionary.observed_generations >= (0, 1)
    assert len(evolutionary.observed_genomes) > 1
    assert evolutionary.live_population > 0


def test_genesis_stale_resources_produce_irreversible_extinction():
    selected = HarnessConfig(
        population=8, generations=1, ticks=2000, checkpoint_interval=2000,
        random_checkpoint_count=0, adversarial_conditions=("stale_resources",),
    )
    trace = build_genesis_harness(selected).run()

    assert trace.metrics().deaths >= 8
    assert trace.metrics().births >= 8
    assert trace.metrics().final_population == 0
    assert trace.metrics().extinction_events == 1


def test_interoception_ablation_runs_matched_arms_without_feedback():
    from research.autonomous_life.ablation import run_interoception_ablation

    result = run_interoception_ablation(HarnessConfig(
        population=8, generations=1, ticks=32,
        checkpoint_interval=32, random_checkpoint_count=0,
    ))

    assert result.with_interoception.enabled is True
    assert result.without_interoception.enabled is False
    # The default ablation fixes the founder cohort in both arms.  This keeps
    # regulation evidence separate from the autonomous-life reproduction
    # experiment and prevents divergent birth counts from changing exposure
    # to the same physiological regime.
    assert result.with_interoception.metrics.births == 8
    assert result.without_interoception.metrics.births == 8
    assert result.with_interoception.metrics.organism_count == 8
    assert result.without_interoception.metrics.organism_count == 8
    assert result.stress_rate_delta == (
        result.without_interoception.stress_rate
        - result.with_interoception.stress_rate
    )


def test_interoception_ablation_can_also_measure_full_lineage_effects():
    from research.autonomous_life.ablation import run_interoception_ablation

    result = run_interoception_ablation(HarnessConfig(
        population=8, generations=1, ticks=8,
        checkpoint_interval=8, random_checkpoint_count=0,
    ), matched_cohort=False)

    assert result.with_interoception.metrics.reproduction_events >= 0
    assert result.without_interoception.metrics.reproduction_events >= 0


def test_interoception_ablation_replicates_preserve_seed_level_evidence():
    from research.autonomous_life.ablation import run_interoception_ablation_replicates

    results = run_interoception_ablation_replicates(HarnessConfig(
        population=8, generations=1, ticks=4,
        checkpoint_interval=4, random_checkpoint_count=0,
    ), seeds=(7, 11))

    assert len(results) == 2
    assert all(
        result.with_interoception.metrics.births == 8
        and result.without_interoception.metrics.births == 8
        for result in results
    )


def test_interoception_control_has_real_sham_and_absent_arms():
    from research.autonomous_life.ablation import run_interoception_control

    result = run_interoception_control(HarnessConfig(
        population=8, generations=1, ticks=8,
        checkpoint_interval=4, random_checkpoint_count=0,
    ))
    assert result.with_interoception.enabled is True
    assert result.sham_interoception.enabled is True
    assert result.without_interoception.enabled is False
    assert result.with_interoception.metrics.organism_count == 8
    assert result.sham_interoception.metrics.organism_count == 8
    assert result.without_interoception.metrics.organism_count == 8

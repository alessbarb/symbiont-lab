"""Wave 0 measurement coherence (Cross-Domain Revision Coherence v1 §2.1).

Instrumentation observes decisions after they resolve and is never read back:
counts must be right, checkpoint-stable, and absent-tolerant for older payloads.
"""

from __future__ import annotations

from symbiont.actuation.binding import CompetenceExecutionBindingRegistry
from symbiont.actuation.effects import EffectSpace
from symbiont.agency.executive_outcome import ExecutiveOutcomeLedger
from symbiont.capacity import CapacityPressure
from symbiont.cognition.generative.consolidation import GenerativeUseTracker
from symbiont.core.embodiment.adaptation import EmbodimentAdaptation
from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject


def test_pressure_counts_evictions_and_relearning_across_checkpoint():
    pressure = CapacityPressure(2)
    for ref in ("a", "b", "c"):
        pressure.note_admitted(ref)
    pressure.note_evicted(("a",))
    restored = CapacityPressure.restore(pressure.checkpoint(), capacity=2)
    restored.note_admitted("a")  # reappears after eviction
    snapshot = restored.snapshot(occupancy=2)
    assert snapshot["admissions"] == 4 and snapshot["evictions"] == 1
    assert snapshot["relearned_after_eviction"] == 1 and snapshot["pressure"] == 1.0
    assert CapacityPressure.restore(None, capacity=2).snapshot(0)["evictions"] == 0


def test_effect_space_eviction_is_unchanged_and_now_counted():
    space = EffectSpace(max_effects=2)
    for value in (0.2, 0.4, 0.2, 0.6, 0.8):
        space.observe({"signal.a": value})
    retained = sorted(effect.effect_id for effect in space.effects)
    # The existing policy (support, confidence, id) still decides survivors.
    assert len(retained) == 2
    snapshot = space.capacity_snapshot()
    assert snapshot["occupancy"] == 2 and snapshot["evictions"] == 2
    restored = EffectSpace.restore(space.checkpoint())
    assert sorted(effect.effect_id for effect in restored.effects) == retained
    assert restored.capacity_snapshot()["evictions"] == 2


def test_binding_and_executive_bounds_are_counted():
    registry = CompetenceExecutionBindingRegistry(capacity=1)
    for tick, competence in enumerate(("c1", "c2")):
        registry.bind_from_evidence(
            competence_id=competence,
            surface_fingerprint="s",
            effect_id="effect.e",
            evidence_refs=("ev",),
            reliability=1.0,
            controllability=1.0,
            tick=tick,
        )
    assert registry.pressure.snapshot(len(registry.items))["evictions"] == 1
    assert CompetenceExecutionBindingRegistry.restore(registry.checkpoint()).pressure.evictions == 1

    ledger = ExecutiveOutcomeLedger(max_keys=1)
    ledger._evidence_for(("c1", "e"))
    ledger._evidence_for(("c2", "e"))
    assert ledger.keys_evicted == 1 and ledger.pressure.evictions == 1
    assert ledger.suppressed_competences() == frozenset()


def test_sterile_reactivation_needs_same_context_and_no_new_source():
    tracker = GenerativeUseTracker()

    def use(episode, sources=()):
        tracker.record(
            representation_ref="rep.a", episode_id=episode, state_id="s", source_refs=sources
        )

    use("ep.1")  # first use: admission, not sterile
    use("ep.2")  # new context
    use("ep.2", ("src.1",))  # new source
    use("ep.2")  # nothing new
    use("ep.2")
    assert tracker.sterile_reactivations == {"rep.a": 2}
    restored = GenerativeUseTracker.from_checkpoint(tracker.checkpoint())
    assert restored.sterile_reactivations == {"rep.a": 2}
    assert restored.pressure.admissions == 1


def test_adaptation_state_is_not_the_reacclimation_timer():
    adaptation = EmbodimentAdaptation()
    assert adaptation.adaptation_state(window_completed=False) == "reacquiring"
    assert adaptation.adaptation_state(window_completed=True) == "unstable"
    adaptation._stable_ticks = 3
    assert adaptation.adaptation_state(window_completed=True) == "stabilizing"
    adaptation.recovery_tick = 42
    assert adaptation.adaptation_state(window_completed=True) == "adapted"


def test_measurement_snapshot_is_read_only():
    body = CausalBody(actuator_count=4, seed=101)
    runtime = build_subject(body, organism_id="wave0", factorized_effects=True)
    for _ in range(200):
        runtime.tick()
        body.advance(runtime.last_actuations)
    before = runtime.checkpoint()
    first = runtime.measurement_snapshot()
    assert runtime.measurement_snapshot() == first
    after = runtime.checkpoint()
    for volatile in ("checkpoint_lineage",):
        before.pop(volatile, None)
        after.pop(volatile, None)
    assert before == after
    counts = first["competence_availability"]
    assert counts["admissible"] <= counts["executable"] <= counts["known"]
    assert set(first["capacity"]) >= {"effect_space", "execution_bindings", "executive_keys"}
    assert set(first["passive_evidence"]) == {"motor_baseline_frames", "ledger_passive_windows"}

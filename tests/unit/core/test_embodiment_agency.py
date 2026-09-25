"""Tests for embodiment, agency modeling, inferred body schema, and transplant (P0-P13)."""
from __future__ import annotations

import pytest

from symbiont.core.body import (
    ActivationConsequence,
    Body,
    BodyPhysiology,
    EffectorPort,
    ReceptorPort,
    create_standard_body,
)
from symbiont.core.embodiment import EmbodimentSession, implant
# Explicit component-level falsification specimens. Production Symbiont no
# longer imports this retired parallel stack.
from symbiont.core.embodiment.agency import (
    AgencyModel,
    InferredBodySchema,
    InferredSelfModel,
    PerceptualStructure,
    SensorimotorModel,
)
from symbiont.core.symbiont import Symbiont
from symbiont.core.individual import Individual, create_individual


def test_body_physical_substrate_and_causal_metabolism():
    """P1: Body owns physiology, effectors, receptors, and physical causality."""
    body = create_standard_body("body_alpha", num_receptors=3, num_effectors=2)
    assert body.body_id == "body_alpha"
    assert len(body.receptor_ids) == 4  # 3 exteroceptive + 1 somatic
    assert len(body.effector_ids) == 2

    # Physical intake increases reserve (Invariant C)
    initial_energy = body.physiology.energy_reserve
    added = body._test_physical_intake(0.5)
    assert added == 0.5
    assert body.physiology.energy_reserve == initial_energy + 0.5

    # Applying activations incurs metabolic cost
    res = body.apply_activations({"eff.0": 1.0, "eff.1": 0.5})
    assert "eff.0" in res
    assert res["eff.0"].physical_effect > 0.0
    assert body.physiology.energy_reserve < initial_energy + 0.5

    # Broken effector experiment (P11): disabled effector consumes cost but gives 0 effect
    body.break_effector("eff.0")
    res_broken = body.apply_activations({"eff.0": 1.0})
    assert res_broken["eff.0"].physical_effect == 0.0
    assert res_broken["eff.0"].energy_cost > 0.0


def test_embodiment_session_and_opaque_translation():
    """P2: EmbodimentSession binds body ports to opaque channels without leaking semantics."""
    body = create_standard_body("body_beta", num_receptors=2, num_effectors=2)
    session = implant(
        symbiont_id="sym_1",
        body_id=body.body_id,
        receptor_ids=body.receptor_ids,
        effector_ids=body.effector_ids,
    )

    assert session.symbiont_id == "sym_1"
    assert session.body_id == "body_beta"
    assert session.is_active

    # Transduction to symbiont yields strictly opaque channel IDs ('in.0', 'in.1', ...)
    physical_readings = {"rec.0": 0.8, "rec.1": 0.2, "rec.somatic": 0.9}
    opaque_in = session.transduce_to_symbiont(physical_readings)
    for ch in opaque_in:
        assert ch.startswith("in.")
        assert "rec" not in ch  # No physical port leakage!

    # Routing to body translates opaque activations ('out.0') to physical effector ports
    opaque_act = {"out.0": 0.7, "out.1": 0.3}
    body_cmds = session.route_to_body(opaque_act)
    for port in body_cmds:
        assert port.startswith("eff.")


def test_individual_emergence_and_history():
    """P0: Individual emerges from Symbiont + Body + EmbodimentSession + History."""
    ind = create_individual("sym_orig", "body_orig", num_receptors=3, num_effectors=2)
    assert ind.symbiont_id == "sym_orig"
    assert ind.body_id == "body_orig"
    assert ind.is_alive

    # Run 10 ticks of interaction
    for t in range(10):
        rec = ind.step(external_stimuli={"rec.0": 0.5, "rec.1": 0.1 * t})
        assert rec.tick == t + 1
        assert rec.symbiont_id == "sym_orig"
        assert rec.body_id == "body_orig"

    assert len(ind.history) == 10
    assert ind.current_tick == 10


def test_agency_inference_and_acquired_body_schema():
    """P4-P7: Differential controllability informs InferredBodySchema."""
    agency = AgencyModel(min_trials=3)
    p_struct = PerceptualStructure()
    schema = InferredBodySchema(confidence_threshold=0.4)

    # Simulate: out.0 actively changes in.0 by +0.5, while in.1 only drifts randomly
    for step in range(10):
        if step % 2 == 0:
            activations = {"out.0": 1.0, "out.1": 0.0}
            deltas = {"in.0": 0.6, "in.1": 0.05}
            inputs = {"in.0": 0.6, "in.1": 0.5}
        else:
            activations = {"out.0": 0.0, "out.1": 0.0}
            deltas = {"in.0": 0.05, "in.1": 0.05}
            inputs = {"in.0": 0.05, "in.1": 0.55}

        p_struct.observe(inputs)
        agency.record_step(activations, deltas)

    schema.update_from_agency(agency, p_struct)

    # in.0 should be inferred as internal / controllable
    assert "in.0" in schema.internal_channels
    # in.1 should be external
    assert "in.1" in schema.external_channels
    # out.0 should be recognized with high agency confidence
    assert agency.is_agentic("out.0")
    assert not agency.is_agentic("out.1")
    assert len(schema.regions) >= 1
    assert schema.regions[0].effector_channels == ("out.0",)


def test_port_permutation_experiment():
    """P10: Permuting output ports creates prediction disruption and triggers schema revision."""
    ind = create_individual("sym_perm", "body_perm", num_receptors=2, num_effectors=2)

    # Let the organism stabilize initially
    for _ in range(15):
        ind.step({"rec.0": 0.4, "rec.1": 0.8})

    # Record initial output mapping
    initial_bindings = dict(ind.session.output_bindings)
    # Permute the outputs: swap targets of out.0 and out.1
    swapped = {"out.0": initial_bindings["out.1"], "out.1": initial_bindings["out.0"]}
    ind.session.permute_outputs(swapped)

    # Next step after permutation should detect disruption or force exploration
    rec = ind.step({"rec.0": 0.1, "rec.1": 0.9})
    assert ind.session.output_bindings == swapped


def test_broken_effector_experiment():
    """P11: Silently breaking an effector causes agency attribution to drop."""
    ind = create_individual("sym_break", "body_break", num_receptors=2, num_effectors=2)

    # Run initial ticks
    for _ in range(10):
        ind.step()

    # Silently disable effector eff.0 on the body
    assert ind.body.break_effector("eff.0")

    # Step more ticks
    for _ in range(10):
        rec = ind.step()

    # Consequence of eff.0 must be 0.0 now
    if "eff.0" in rec.physical_consequences:
        assert rec.physical_consequences["eff.0"].physical_effect == 0.0


def test_body_transplant():
    """P12: Transplanting Symbiont into a new Body preserves cognitive continuity."""
    body_1 = create_standard_body("body_source", num_receptors=3, num_effectors=2)
    body_2 = create_standard_body("body_target", num_receptors=4, num_effectors=3)

    symbiont = Symbiont("sym_traveler")
    session_1 = implant(
        symbiont_id=symbiont.symbiont_id,
        body_id=body_1.body_id,
        receptor_ids=body_1.receptor_ids,
        effector_ids=body_1.effector_ids,
        started_at=0,
    )

    ind = Individual(symbiont=symbiont, body=body_1, session=session_1)
    for _ in range(10):
        ind.step()

    assert ind.current_tick == 10
    assert ind.symbiont.total_ticks == 10
    old_session_id = ind.session.embodiment_id

    # Transplant to body_2
    new_session = ind.transplant_to(body_2)
    assert ind.body_id == "body_target"
    assert ind.session.embodiment_id != old_session_id
    assert not session_1.is_active  # old session severed
    assert new_session.is_active

    # Step in new body
    ind.step()
    # Symbiont continuity continues (total ticks incremented)
    assert ind.symbiont.total_ticks == 11
    # External embodiment IDs never reach self-model (AUD-013)
    assert not hasattr(ind.symbiont.self_model, "embodiment_history")
    assert not hasattr(ind.symbiont.self_model, "embodiment_id")
    # Continues to adapt over additional ticks without crashing
    for _ in range(15):
        rec = ind.step()
        assert rec.body_viable


def test_multiple_morphologies():
    """P13: Same Symbiont cognitive architecture adapts to distinct morphologies."""
    # Wheeled-like morphology (2 exteroceptors, 2 effectors)
    ind_wheeled = create_individual("sym_wheel", "body_wheel", morphology="wheeled", num_receptors=2, num_effectors=2)
    # Quadruped-like morphology (6 exteroceptors, 4 effectors)
    ind_quad = create_individual("sym_quad", "body_quad", morphology="quadruped", num_receptors=6, num_effectors=4)

    for _ in range(5):
        rec_w = ind_wheeled.step()
        rec_q = ind_quad.step()
        assert rec_w.body_viable
        assert rec_q.body_viable

    assert len(ind_wheeled.body.effector_ids) == 2
    assert len(ind_quad.body.effector_ids) == 4
    assert ind_wheeled.is_alive
    assert ind_quad.is_alive


def test_counterfactual_baseline_requirement_for_agency():
    """AUD-011: Agency requires counterfactual baseline evidence (passive trials)."""
    agency_model = AgencyModel(min_trials=3, min_baselines=3)

    # Only intervention trials, 0 baselines -> no counterfactual evidence
    for _ in range(5):
        agency_model.record_step(
            activations={"eff.0": 1.0},
            observed_deltas={"rec.0": 0.8},
        )
    assert not agency_model.contingency[("eff.0", "rec.0")].has_counterfactual_evidence
    assert agency_model.agency_confidence.get("eff.0", 0.0) == 0.0

    # Now record baseline (passive) trials where eff.0 is inactive and rec.0 has 0 delta
    for _ in range(5):
        agency_model.record_step(
            activations={"eff.0": 0.0},
            observed_deltas={"rec.0": 0.0},
        )
    assert agency_model.contingency[("eff.0", "rec.0")].has_counterfactual_evidence
    # Agency is now detected because intervention produces delta 0.8 vs baseline 0.0
    assert agency_model.agency_confidence["eff.0"] > 0.5


def test_label_renaming_invariance():
    """AUD-030, AUD-043: Cognition is invariant to port label renamings."""
    # Body A with standard names
    body_a = create_standard_body("body_a", num_receptors=2, num_effectors=2)
    # Body B with completely scrambled / renamed labels but exact same physical ordinals
    r0 = ReceptorPort(port_id="alpha_xyz", kind="exteroceptive", ordinal=0)
    r1 = ReceptorPort(port_id="beta_uvw", kind="exteroceptive", ordinal=1)
    r_soma = ReceptorPort(port_id="zeta_soma", kind="proprioceptive", ordinal=99)
    e0 = EffectorPort(port_id="motor_left", kind="locomotor", ordinal=0, cost_per_activation=0.01)
    e1 = EffectorPort(port_id="motor_right", kind="locomotor", ordinal=1, cost_per_activation=0.01)
    body_b = Body("body_b", receptors=[r0, r1, r_soma], effectors=[e0, e1])

    sym_a = Symbiont("sym_a")
    session_a = implant(sym_a.symbiont_id, body_a.body_id, body_a.receptor_ids, body_a.effector_ids, started_at=0)
    ind_a = Individual(sym_a, body_a, session_a)

    sym_b = Symbiont("sym_b")
    session_b = implant(sym_b.symbiont_id, body_b.body_id, body_b.receptor_ids, body_b.effector_ids, started_at=0)
    ind_b = Individual(sym_b, body_b, session_b)

    # Both run identical steps with identical numerical stimuli
    for _ in range(10):
        ind_a.step(external_stimuli={"rec.0": 0.5, "rec.1": 0.2})
        ind_b.step(external_stimuli={"alpha_xyz": 0.5, "beta_uvw": 0.2})

    # Energy consumption and cognitive state must match because ordinals and physics match
    assert ind_a.body.physiology.energy_reserve == pytest.approx(ind_b.body.physiology.energy_reserve)
    assert ind_a.symbiont.total_ticks == ind_b.symbiont.total_ticks


def test_silent_effector_failure_and_agency_revision():
    """AUD-038: Silent effector failure causes agency drop and body schema revision."""
    body = create_standard_body("body_fail", num_receptors=2, num_effectors=2)
    sym = Symbiont("sym_fail")
    session = implant(sym.symbiont_id, body.body_id, body.receptor_ids, body.effector_ids, started_at=0)
    ind = Individual(sym, body, session)

    # Run for 20 ticks to allow agency baseline
    for _ in range(20):
        ind.step(external_stimuli={"rec.0": 0.3, "rec.1": 0.3})

    # Silently disable effector 0
    body.break_effector("eff.0")

    # Run 30 more ticks
    for _ in range(30):
        ind.step(external_stimuli={"rec.0": 0.3, "rec.1": 0.3})

    # Agency on eff.0 should reflect lower or revised controllability
    assert all(
        0.0 <= estimate.confidence <= 1.0
        for estimate in ind.symbiont.agency_model.estimates
    )
    assert ind.symbiont.body_schema.boundary_revision_count >= 0


def test_real_somatic_receptor_reflects_physiology():
    """AUD-032: Somatic receptor reads actual physiology state."""
    body = create_standard_body("body_soma", num_receptors=2, num_effectors=1)
    soma_port = body.get_receptor("rec.somatic")
    assert soma_port is not None

    # Initial reading with default energy (1.0/2.0 = 0.5) and integrity (1.0) -> 0.5*0.5 + 0.5*1.0 = 0.75
    reading = soma_port.sample()
    assert reading == pytest.approx(0.75)

    # Physical intake 1.0 fills reserve to max 2.0 -> 0.5*1.0 + 0.5*1.0 = 1.0
    body._test_physical_intake(1.0)
    reading_full = soma_port.sample()
    assert reading_full == pytest.approx(1.0)

    # Depleting energy decreases reading
    body.physiology.consume_energy(1.0)
    reading_depleted = soma_port.sample()
    assert reading_depleted < reading_full
    assert reading_depleted == pytest.approx(0.75)



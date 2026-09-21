from __future__ import annotations

from symbiont.modeling import ModeledOrganismRuntime
from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning import replay_pressure_curve as study


def test_replay_pressure_curve_registered():
    assert get_protocol("learning.replay-pressure-curve").__name__ == "run_replay_pressure_curve_study"


def test_replay_pressure_budget_mapping_is_bounded_and_monotone():
    budgets = [study._budget_for_pressure(p) for p in study.PRESSURES]
    assert budgets[0] == (2, 12)
    assert budgets[-1] == (8, 48)
    assert all(r[0] <= n[0] and r[1] <= n[1] for r, n in zip(budgets, budgets[1:]))


def test_pressure_requests_keep_everything_except_replay_budget():
    runtime = ModeledOrganismRuntime(
        organism_id="pressure-curve-test",
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    for record in study._transition_history(
        organism_id=runtime.organism_id,
        seed=101,
        ticks=128,
    ):
        runtime.record_experience(record)
    plan = runtime.autonomous_private_learning_plan()
    assert plan is not None

    low = study._request_at_pressure(plan, 0.25)
    high = study._request_at_pressure(plan, 0.75)

    assert low.organism_id == high.organism_id == plan.request.organism_id
    assert low.corpus_hash == high.corpus_hash == plan.request.corpus_hash
    assert low.tokenizer_hash == high.tokenizer_hash == plan.request.tokenizer_hash
    assert low.seed == high.seed == plan.request.seed
    assert low.architecture_id is high.architecture_id is plan.request.architecture_id
    assert low.objective is high.objective is plan.request.objective
    assert low.context_window == high.context_window == plan.request.context_window
    assert low.requested_parameters == high.requested_parameters == plan.request.requested_parameters
    assert low.requested_epochs < high.requested_epochs
    assert low.requested_steps < high.requested_steps

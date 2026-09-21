from __future__ import annotations

from types import SimpleNamespace

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.studies.learning import autonomous_replay_stopping as study


def test_autonomous_replay_stopping_protocol_registered():
    assert (
        get_protocol("learning.autonomous-replay-stopping").__name__
        == "run_autonomous_replay_stopping_study"
    )


def test_autonomous_request_differs_only_by_stopping_policy_and_budget():
    plan = SimpleNamespace(
        request=SimpleNamespace(
            organism_id="o",
            corpus_hash="a" * 64,
            tokenizer_hash="b" * 64,
            architecture_id=study.ArchitectureId.GRU_V1 if hasattr(study, "ArchitectureId") else None,
            objective=study.ModelObjective.NEXT_TOKEN,
            seed=7,
            context_window=32,
            requested_parameters=1_000_000,
            created_tick_class=128,
        )
    )
    if plan.request.architecture_id is None:
        from symbiont.modeling import ArchitectureId
        plan.request.architecture_id = ArchitectureId.GRU_V1

    minimum = study._request(plan, epochs=2, steps=12, autonomous_stopping=False)
    autonomous = study._request(plan, epochs=8, steps=48, autonomous_stopping=True)
    maximum = study._request(plan, epochs=8, steps=48, autonomous_stopping=False)

    assert autonomous.corpus_hash == maximum.corpus_hash == minimum.corpus_hash
    assert autonomous.tokenizer_hash == maximum.tokenizer_hash == minimum.tokenizer_hash
    assert autonomous.seed == maximum.seed == minimum.seed
    assert autonomous.requested_epochs == maximum.requested_epochs == 8
    assert autonomous.requested_steps == maximum.requested_steps == 48
    assert autonomous.autonomous_stopping is True
    assert maximum.autonomous_stopping is False
    assert autonomous.requested_patience == 2
    assert autonomous.requested_min_validation_gain == 0.005

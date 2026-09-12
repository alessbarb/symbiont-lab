from symbiont.core.collective import CollectiveMemory
from symbiont.core.metacognition import MetacognitionEngine
from symbiont.core.model import Assessment
from symbiont.simulation import Evaluator, run_simulation


def _assessment(*, uncertainty: float, novelty: float, believes: bool) -> Assessment:
    probability = 0.90 if believes else 0.10
    return Assessment(
        novelty=novelty,
        uncertainty=uncertainty,
        relevance=0.6,
        information_gain=0.3,
        curiosity=0.1,
        risk=0.7 if believes else 0.2,
        collective_threat=0.5,
        collective_certainty=0.2,
        fingerprint="M-M-M-M-M",
        should_investigate=True,
        believes_threat=believes,
        threat_probability=probability,
    )


def test_internal_metacognition_uses_no_ground_truth():
    engine = MetacognitionEngine()
    state = engine.assess(
        [_assessment(uncertainty=0.8, novelty=0.5, believes=True)],
        CollectiveMemory(),
    )

    assert 0 <= state.self_confidence <= 1
    assert 0 <= state.epistemic_pressure <= 1
    assert state.status in {"uncertain", "novel", "contested", "stable", "watchful"}


def test_evaluator_measures_overconfidence_without_feeding_it_back():
    evaluator = Evaluator()
    wrong = _assessment(uncertainty=0.1, novelty=0.1, believes=False)
    evaluator.record(is_threat=True, investigated=False, assessment=wrong)

    assert evaluator.overconfidence_rate == 1.0
    assert evaluator.blind_spot_rate == 1.0
    assert evaluator.brier_score > 0.5


def test_live_snapshots_expose_internal_and_external_meta_metrics():
    snapshots = []
    result, _ = run_simulation(hosts=12, steps=80, seed=17, on_snapshot=snapshots.append)
    final = snapshots[-1]

    assert 0 <= final.self_confidence <= 1
    assert 0 <= final.epistemic_pressure <= 1
    assert 0 <= final.calibration_error <= 1
    assert 0 <= final.brier_score <= 1
    assert 0 <= final.overconfidence_rate <= 1
    assert 0 <= final.blind_spot_rate <= 1
    assert 0 <= final.classification_recall <= 1
    assert final.metacognitive_status == result.metacognitive_status

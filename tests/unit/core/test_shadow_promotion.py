import pytest

from tests.unit.core.test_cognition_bridge import _genome, _simple_graph
from symbiont.cognition.limits import KernelLimits
from symbiont.core.cognition_bridge import CognitiveBridge, GraphError

def test_shadow_promotion_requires_gain_and_adds_predictor():
 b=CognitiveBridge(graph=_simple_graph(),genome=_genome(),kernel_limits=KernelLimits(),develop_senses=True)
 for _ in range(8): b._shadow_predictions.setdefault(("s","c"), __import__('symbiont.cognition.learning',fromlist=['ShadowPrediction']).ShadowPrediction("s","c")).observe(1,1,0)
 assert b.promote_shadow_prediction("s","c",tick=8)
 assert any(n.kind.value == "predictor" for n in b.graph.nodes)


def test_restore_shadow_predictions_supports_large_cohort():
    entries = [
        {"source_id": f"s_{i}", "target_id": f"t_{i}", "samples": 5, "model_loss": 0.1, "persistence_loss": 0.2, "status": "candidate"}
        for i in range(1000)
    ]
    restored = CognitiveBridge._restore_shadow_predictions(entries)
    assert len(restored) == 1000


def test_restore_shadow_predictions_rejects_payload_above_bound():
    entries = [
        {"source_id": f"s_{i}", "target_id": f"t_{i}", "samples": 5,
         "model_loss": 0.1, "persistence_loss": 0.2, "status": "candidate"}
        for i in range(16_385)
    ]
    with pytest.raises(GraphError):
        CognitiveBridge._restore_shadow_predictions(entries)

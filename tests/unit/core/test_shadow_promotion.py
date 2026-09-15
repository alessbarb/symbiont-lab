from tests.unit.core.test_cognition_bridge import _genome, _simple_graph
from symbiont.cognition.limits import KernelLimits
from symbiont.core.cognition_bridge import CognitiveBridge

def test_shadow_promotion_requires_gain_and_adds_predictor():
 b=CognitiveBridge(graph=_simple_graph(),genome=_genome(),kernel_limits=KernelLimits(),develop_senses=True)
 for _ in range(8): b._shadow_predictions.setdefault(("s","c"), __import__('symbiont.cognition.learning',fromlist=['ShadowPrediction']).ShadowPrediction("s","c")).observe(1,1,0)
 assert b.promote_shadow_prediction("s","c",tick=8)
 assert any(n.kind.value == "predictor" for n in b.graph.nodes)

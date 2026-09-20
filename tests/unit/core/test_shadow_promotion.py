import pytest

from tests.unit.core.test_cognition_bridge import _genome, _simple_graph
from symbiont.cognition.limits import KernelLimits
from symbiont.core.cognition_bridge import CognitiveBridge, GraphError
from symbiont.cognition.learning import ShadowPrediction
from symbiont.cognition.types import EdgeKind, NodeKind

def test_shadow_promotion_requires_gain_and_materializes_learned_sense_input():
    bridge = CognitiveBridge(
        graph=_simple_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    shadow = ShadowPrediction("s", "c")
    bridge._shadow_predictions[("s", "c")] = shadow
    for _ in range(8):
        shadow.observe(1.0, 1.0, 0.0)

    assert bridge.promote_shadow_prediction("s", "c", tick=8)

    predictors = [node for node in bridge.graph.nodes if node.kind is NodeKind.PREDICTOR]
    assert len(predictors) == 1
    predictor = predictors[0]
    assert predictor.predicts_node_id == "c"
    assert any(
        edge.source_id == "s"
        and edge.target_id == predictor.node_id
        and edge.kind is EdgeKind.PREDICTIVE
        and edge.delay_ticks == 0
        for edge in bridge.graph.edges
    )


def test_shadow_promotion_does_not_wire_latent_source_with_wrong_lag():
    bridge = CognitiveBridge(
        graph=_simple_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    shadow = ShadowPrediction("c", "s")
    bridge._shadow_predictions[("c", "s")] = shadow
    for _ in range(8):
        shadow.observe(1.0, 1.0, 0.0)

    assert bridge.promote_shadow_prediction("c", "s", tick=8) is False
    assert not any(node.kind is NodeKind.PREDICTOR for node in bridge.graph.nodes)


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



def test_shadow_pruning_drops_retired_and_non_sensory_sources():
    bridge = CognitiveBridge(
        graph=_simple_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    bridge._shadow_predictions = {
        ("s", "c"): ShadowPrediction(
            "s", "c", samples=8, model_loss=0.0, persistence_loss=1.0, status="supported"
        ),
        ("c", "s"): ShadowPrediction(
            "c", "s", samples=8, model_loss=0.0, persistence_loss=1.0, status="supported"
        ),
        ("s", "r"): ShadowPrediction(
            "s", "r", samples=16, model_loss=2.0, persistence_loss=1.0, status="retired"
        ),
    }

    bridge._prune_shadow_predictions()

    assert set(bridge._shadow_predictions) == {("s", "c")}

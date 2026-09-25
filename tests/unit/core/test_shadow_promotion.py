import pytest
from symbiont.core.cognition_bridge import CognitiveBridge, GraphError

from symbiont.cognition.learning import ShadowPrediction
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind
from tests.unit.core.test_cognition_bridge import _genome, _simple_graph


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
    assert not any(node.kind is NodeKind.PREDICTOR for node in bridge.graph.nodes)
    assert "predictor:s:c" in bridge._structural_candidates

    bridge.tick({"s": 1.0}, tick=12)

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
        {
            "source_id": f"s_{i}",
            "target_id": f"t_{i}",
            "samples": 5,
            "model_loss": 0.1,
            "persistence_loss": 0.2,
            "status": "candidate",
        }
        for i in range(1000)
    ]
    restored = CognitiveBridge._restore_shadow_predictions(entries)
    assert len(restored) == 1000


def test_restore_shadow_predictions_rejects_payload_above_bound():
    entries = [
        {
            "source_id": f"s_{i}",
            "target_id": f"t_{i}",
            "samples": 5,
            "model_loss": 0.1,
            "persistence_loss": 0.2,
            "status": "candidate",
        }
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


def test_shadow_prediction_ordered_view_is_cached_and_invalidated():
    bridge = CognitiveBridge(
        graph=_simple_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    a = ShadowPrediction("sense.b", "concept")
    b = ShadowPrediction("sense.a", "concept")
    bridge._shadow_predictions[(a.source_id, a.target_id)] = a
    bridge._shadow_predictions[(b.source_id, b.target_id)] = b
    bridge._invalidate_shadow_predictions_cache()

    first = bridge.shadow_predictions
    second = bridge.shadow_predictions
    assert first is second
    assert [(item.source_id, item.target_id) for item in first] == [
        ("sense.a", "concept"),
        ("sense.b", "concept"),
    ]

    c = ShadowPrediction("sense.c", "concept")
    bridge._shadow_predictions[(c.source_id, c.target_id)] = c
    bridge._invalidate_shadow_predictions_cache()
    refreshed = bridge.shadow_predictions
    assert refreshed is not first
    assert refreshed[-1] is c


def test_shadow_prune_fast_path_skips_unchanged_full_scan(monkeypatch):
    bridge = CognitiveBridge(
        graph=_simple_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    bridge._shadow_predictions[("s", "c")] = ShadowPrediction(
        "s",
        "c",
        samples=8,
        model_loss=0.0,
        persistence_loss=1.0,
        status="supported",
    )

    # First pass establishes the clean revision marker.
    bridge._prune_shadow_predictions()
    assert bridge._shadow_prune_dirty is False
    assert bridge._shadow_prune_topology_revision == bridge.topology_revision

    def fail_if_called():
        raise AssertionError("unchanged shadow pool should not rescan topology")

    monkeypatch.setattr(bridge, "_topology_cache", fail_if_called)
    bridge._prune_shadow_predictions()


def test_shadow_prune_rescans_after_topology_revision_change():
    bridge = CognitiveBridge(
        graph=_simple_graph(),
        genome=_genome(),
        kernel_limits=KernelLimits(),
        develop_senses=True,
    )
    bridge._shadow_predictions[("s", "c")] = ShadowPrediction(
        "s",
        "c",
        samples=8,
        model_loss=0.0,
        persistence_loss=1.0,
        status="supported",
    )
    bridge._prune_shadow_predictions()

    bridge._topology_revision += 1
    bridge._prune_shadow_predictions()

    assert bridge._shadow_prune_topology_revision == bridge.topology_revision

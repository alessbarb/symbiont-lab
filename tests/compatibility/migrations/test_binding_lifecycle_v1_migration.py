"""Execution binding checkpoint v1 -> v2 (Cross-Domain Revision Coherence v1 §3.2).

Accepts: schema 1 bindings (no lifecycle). Produces: schema 2 bindings with
status VALID, no reason, revision 0. Discards: nothing (v1 had no lifecycle).
"""

from symbiont.actuation.binding import BindingStatus, CompetenceExecutionBindingRegistry

V1 = {
    "schema_version": 1,
    "capacity": 512,
    "items": [
        {
            "competence_id": "competence.a",
            "surface_fingerprint": "surface.s",
            "effect_id": "effect.e",
            "evidence_refs": ["ev.1"],
            "reliability": 0.9,
            "controllability": 0.8,
            "last_evidence_tick": 12,
        }
    ],
}


def test_v1_bindings_migrate_as_valid_revision_zero():
    registry = CompetenceExecutionBindingRegistry.restore(V1)
    (binding,) = registry.items
    assert binding.status is BindingStatus.VALID and binding.status_reason is None
    assert binding.revision == 0 and binding.last_evidence_tick == 12
    assert registry.checkpoint()["schema_version"] == 2

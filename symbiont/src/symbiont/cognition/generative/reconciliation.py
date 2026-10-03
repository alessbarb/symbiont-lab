"""Explicit boundary from factual evidence to generative hypothesis status."""

from __future__ import annotations

from .hypothesis import GenerativeHypothesis
from .types import bounded_identifier


class GenerativeReconciler:
    """Applies externally produced evidence; generated output is not evidence."""

    def reconcile(
        self, hypothesis: GenerativeHypothesis, *, evidence_ref: str, supported: bool
    ) -> GenerativeHypothesis:
        if not isinstance(supported, bool):
            raise ValueError("supported must be a bool supplied by an evidence-producing path")
        bounded_identifier(evidence_ref, name="evidence_ref")
        hypothesis._reconcile(evidence_ref=evidence_ref, supported=supported)
        return hypothesis


__all__ = ["GenerativeReconciler"]

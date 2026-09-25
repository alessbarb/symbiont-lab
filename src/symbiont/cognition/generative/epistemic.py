"""Boundary guards preventing generated cognition from becoming evidence."""

from __future__ import annotations

from .types import EpistemicOrigin, GenerativeState, GenerativeTransition


class EpistemicBoundaryError(ValueError):
    """Raised when temporary cognition is sent to an authoritative sink."""


class EpistemicFirewall:
    """Fail-closed guards for factual and executive boundaries.

    The firewall does not store factual records and does not attempt to
    reinterpret generated output.  Callers must use the canonical factual
    pathway when independently observed evidence is available.
    """

    @staticmethod
    def require_known_origin(origin: EpistemicOrigin | None) -> EpistemicOrigin:
        if not isinstance(origin, EpistemicOrigin):
            raise EpistemicBoundaryError("missing or unknown generative provenance")
        return origin

    @classmethod
    def reject_factual_evidence(cls, value: GenerativeState | GenerativeTransition) -> None:
        if not isinstance(value, (GenerativeState, GenerativeTransition)):
            raise EpistemicBoundaryError("only generative values may be checked by this boundary")
        origin = value.origin if isinstance(value, GenerativeState) else None
        if origin is not None:
            cls.require_known_origin(origin)
        raise EpistemicBoundaryError("generative cognition cannot create factual evidence")

    @classmethod
    def reject_execution(cls, value: GenerativeState | GenerativeTransition) -> None:
        if not isinstance(value, (GenerativeState, GenerativeTransition)):
            raise EpistemicBoundaryError("execution requires an explicit non-generative authority")
        raise EpistemicBoundaryError("generative cognition has no execution authority")

    @classmethod
    def reject_factual_learning(cls, value: GenerativeState | GenerativeTransition) -> None:
        if not isinstance(value, (GenerativeState, GenerativeTransition)):
            raise EpistemicBoundaryError("factual learning requires canonical evidence")
        raise EpistemicBoundaryError("generated cognition cannot update factual learning")


__all__ = ["EpistemicBoundaryError", "EpistemicFirewall"]

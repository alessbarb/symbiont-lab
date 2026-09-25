from __future__ import annotations

from dataclasses import dataclass, field
from math import exp


@dataclass(slots=True)
class BeliefState:
    """One revisable local belief built only from an agent's own perceptions."""

    probability: float = 0.5
    evidence: float = 0.0
    conflict: float = 0.0
    revisions: int = 0
    reversals: int = 0
    last_step: int = -1

    @property
    def certainty(self) -> float:
        evidence_certainty = 1.0 - exp(-self.evidence / 4.0)
        return max(0.0, min(1.0, evidence_certainty * (1.0 - 0.60 * self.conflict)))


@dataclass(slots=True, frozen=True)
class BeliefRevision:
    fingerprint: str
    prior_probability: float
    posterior_probability: float
    certainty: float
    surprise: float
    reversed: bool
    step: int


@dataclass(slots=True)
class BeliefModel:
    """Bounded, truth-free model of what recurring synthetic patterns may mean.

    A belief is evidence, not a label: it can strengthen, weaken, conflict with
    itself and cross the decision boundary in either direction.
    """

    max_patterns: int = 256
    max_evidence: float = 32.0
    states: dict[str, BeliefState] = field(default_factory=dict)

    def belief(self, fingerprint: str) -> tuple[float, float]:
        state = self.states.get(fingerprint)
        if state is None:
            return 0.5, 0.0
        return state.probability, state.certainty

    def revise(
        self,
        *,
        fingerprint: str,
        probability: float,
        confidence: float,
        step: int,
    ) -> BeliefRevision:
        if not fingerprint:
            raise ValueError("fingerprint must not be empty")
        if not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        state = self.states.get(fingerprint)
        if state is None:
            self._make_room()
            state = self.states.setdefault(fingerprint, BeliefState())
        if step < state.last_step:
            raise ValueError("belief revisions must be chronological")

        prior = state.probability
        surprise = abs(probability - prior)
        weight = max(0.05, confidence)
        posterior = (prior * state.evidence + probability * weight) / (state.evidence + weight)
        reversed_belief = (prior >= 0.5) != (posterior >= 0.5) and state.revisions > 0

        state.probability = max(0.0, min(1.0, posterior))
        state.evidence = min(self.max_evidence, state.evidence + weight)
        state.conflict = min(1.0, 0.75 * state.conflict + 0.25 * surprise)
        state.revisions += 1
        state.reversals += int(reversed_belief)
        state.last_step = step

        return BeliefRevision(
            fingerprint=fingerprint,
            prior_probability=prior,
            posterior_probability=state.probability,
            certainty=state.certainty,
            surprise=surprise,
            reversed=reversed_belief,
            step=step,
        )

    def _make_room(self) -> None:
        if len(self.states) < self.max_patterns:
            return
        least_useful = min(
            self.states,
            key=lambda key: (
                self.states[key].certainty,
                self.states[key].last_step,
                self.states[key].revisions,
                key,
            ),
        )
        del self.states[least_useful]

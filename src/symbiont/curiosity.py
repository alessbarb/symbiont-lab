from __future__ import annotations

from dataclasses import asdict, dataclass

from .collective import CollectiveMemory
from .model import FEATURES
from .reasoning import Hypothesis


@dataclass(slots=True, frozen=True)
class CuriosityProbe:
    """A shadow-only counterfactual question. It never acts on a host."""

    source_fingerprint: str
    counterfactual_fingerprint: str
    feature: str
    change: str
    expected_information_gain: float
    expected_cost: float
    utility: float
    question: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class CuriosityPlanner:
    """Rank safe synthetic counterfactuals by expected information gain.

    The planner sees only coarse fingerprints, hypotheses and collective beliefs.
    It cannot inspect or modify a host, run commands, or access evaluator truth.
    """

    def plan(
        self,
        hypotheses: tuple[Hypothesis, ...],
        collective: CollectiveMemory,
        limit: int = 3,
    ) -> tuple[CuriosityProbe, ...]:
        candidates: list[CuriosityProbe] = []
        for hypothesis in hypotheses:
            candidates.extend(self._probes_for(hypothesis, collective))
        candidates.sort(key=lambda probe: (-probe.utility, probe.feature, probe.counterfactual_fingerprint))
        return tuple(candidates[: max(0, limit)])

    def _probes_for(
        self,
        hypothesis: Hypothesis,
        collective: CollectiveMemory,
    ) -> list[CuriosityProbe]:
        bins = hypothesis.fingerprint.split("-")
        if len(bins) != len(FEATURES):
            return []

        base_probability, base_certainty = collective.belief(hypothesis.fingerprint)
        probes: list[CuriosityProbe] = []
        for index, (feature, level) in enumerate(zip(FEATURES, bins)):
            targets = self._adjacent_levels(level)
            for target in targets:
                neighbor = list(bins)
                neighbor[index] = target
                counterfactual = "-".join(neighbor)
                neighbor_probability, neighbor_certainty = collective.belief(counterfactual)
                known_neighbor = counterfactual in collective.patterns

                discrimination = (
                    abs(base_probability - neighbor_probability)
                    if known_neighbor
                    else 0.25
                )
                evidence_gap = 1.0 - neighbor_certainty if known_neighbor else 1.0
                uncertainty = 1.0 - base_certainty
                information_gain = min(
                    1.0,
                    uncertainty
                    * (0.45 + 0.35 * discrimination + 0.20 * evidence_gap)
                    * (0.65 + 0.35 * hypothesis.priority),
                )
                expected_cost = 0.10 + 0.04 * (index / max(len(FEATURES) - 1, 1))
                utility = min(1.0, information_gain / (0.55 + expected_cost))
                direction = "raise" if self._rank(target) > self._rank(level) else "lower"
                probes.append(
                    CuriosityProbe(
                        source_fingerprint=hypothesis.fingerprint,
                        counterfactual_fingerprint=counterfactual,
                        feature=feature,
                        change=f"{level}→{target}",
                        expected_information_gain=information_gain,
                        expected_cost=expected_cost,
                        utility=utility,
                        question=(
                            f"In a shadow-only counterfactual, does {direction}ing synthetic "
                            f"{feature} from {level} to {target} materially change collective belief?"
                        ),
                    )
                )
        return probes

    @staticmethod
    def _adjacent_levels(level: str) -> tuple[str, ...]:
        if level == "L":
            return ("M",)
        if level == "H":
            return ("M",)
        if level == "M":
            return ("L", "H")
        return ()

    @staticmethod
    def _rank(level: str) -> int:
        return {"L": 0, "M": 1, "H": 2}.get(level, 1)

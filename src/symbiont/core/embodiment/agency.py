"""Perceptual structure, sensorimotor modeling, agency inference, and inferred body schema.

Implements the epistemological hierarchy defined in the design document:
    PerceptualStructure (P4)
            ↓
    SensorimotorModel (P5)
            ↓
    AgencyModel (P6)
            ↓
    InferredBodySchema (P7)
            ↓
    InferredSelfModel (P8)

All processing operates exclusively on opaque channel tokens (e.g. 'in.0', 'out.1').
No physical names, morphology or world semantics enter this layer (Invariant A).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence


@dataclass(slots=True)
class ChannelStat:
    """Online statistics for an opaque perceptual channel."""

    count: int = 0
    mean: float = 0.0
    m2: float = 0.0
    last_value: float = 0.0

    def update(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2
        self.last_value = value

    @property
    def variance(self) -> float:
        return self.m2 / self.count if self.count > 1 else 0.0

    @property
    def std(self) -> float:
        return math.sqrt(max(0.0, self.variance))


class PerceptualStructure:
    """Discovers covariance and regularities among opaque perceptual channels (P4).

    Answers: 'Which signals maintain stable relations?'
    Does NOT assume self-causality or intentionality.
    """

    def __init__(self, *, alpha: float = 0.05) -> None:
        self.alpha = alpha
        self.channel_stats: dict[str, ChannelStat] = {}
        self.cross_cov: dict[tuple[str, str], float] = {}
        self._history_ticks: int = 0

    def observe(self, inputs: Mapping[str, float]) -> None:
        """Update statistical regularities across observed opaque inputs."""
        self._history_ticks += 1
        for ch, val in inputs.items():
            if ch not in self.channel_stats:
                self.channel_stats[ch] = ChannelStat()
            self.channel_stats[ch].update(float(val))

        # Online tracking of pairwise cross-covariance
        channels = sorted(inputs.keys())
        for i in range(len(channels)):
            ch_a = channels[i]
            val_a = float(inputs[ch_a])
            mean_a = self.channel_stats[ch_a].mean
            for j in range(i + 1, len(channels)):
                ch_b = channels[j]
                val_b = float(inputs[ch_b])
                mean_b = self.channel_stats[ch_b].mean
                pair_key = (ch_a, ch_b)
                current_cov = (val_a - mean_a) * (val_b - mean_b)
                if pair_key not in self.cross_cov:
                    self.cross_cov[pair_key] = current_cov
                else:
                    self.cross_cov[pair_key] = (
                        (1.0 - self.alpha) * self.cross_cov[pair_key]
                        + self.alpha * current_cov
                    )

    def correlation(self, ch_a: str, ch_b: str) -> float:
        """Compute Pearson correlation coefficient between two channels."""
        if ch_a == ch_b:
            return 1.0
        pair = (min(ch_a, ch_b), max(ch_a, ch_b))
        cov = self.cross_cov.get(pair, 0.0)
        std_a = self.channel_stats.get(ch_a, ChannelStat()).std
        std_b = self.channel_stats.get(ch_b, ChannelStat()).std
        denom = std_a * std_b
        if denom <= 1e-9:
            return 0.0
        return max(-1.0, min(1.0, cov / denom))

    def find_clusters(self, threshold: float = 0.5) -> list[set[str]]:
        """Group channels that exhibit high mutual correlation."""
        channels = list(self.channel_stats.keys())
        clusters: list[set[str]] = []
        visited: set[str] = set()
        for ch in channels:
            if ch in visited:
                continue
            cluster = {ch}
            visited.add(ch)
            for other in channels:
                if other not in visited and abs(self.correlation(ch, other)) >= threshold:
                    cluster.add(other)
                    visited.add(other)
            clusters.append(cluster)
        return clusters


class SensorimotorModel:
    """Models forward contingencies between activations and sensory consequences (P5).

    Answers: 'What consequences usually follow my activity?'
    Represents: activation(t) -> future delta(t+1)
    """

    def __init__(self, *, learning_rate: float = 0.1) -> None:
        self.learning_rate = learning_rate
        # Weights mapping (out_channel, in_channel) -> expected delta
        self.weights: dict[tuple[str, str], float] = {}
        self.last_predictions: dict[str, float] = {}
        self.last_activations: dict[str, float] = {}
        self.prediction_errors: dict[str, float] = {}
        self.cumulative_error: float = 0.0
        self.prediction_count: int = 0

    def predict_deltas(
        self, activations: Mapping[str, float], in_channels: Sequence[str]
    ) -> dict[str, float]:
        """Predict expected change in input channels given outgoing activations."""
        predictions: dict[str, float] = {}
        for in_ch in in_channels:
            pred = 0.0
            for out_ch, act_level in activations.items():
                w = self.weights.get((out_ch, in_ch), 0.0)
                pred += w * float(act_level)
            predictions[in_ch] = pred
        self.last_predictions = dict(predictions)
        self.last_activations = dict(activations)
        return predictions

    def update(
        self, actual_deltas: Mapping[str, float], activations: Mapping[str, float] | None = None
    ) -> dict[str, float]:
        """Update sensorimotor weights based on observed deltas and record error."""
        acts = activations if activations is not None else self.last_activations
        errors: dict[str, float] = {}
        for in_ch, actual_delta in actual_deltas.items():
            predicted_delta = self.last_predictions.get(in_ch, 0.0)
            err = actual_delta - predicted_delta
            errors[in_ch] = abs(err)
            self.cumulative_error += abs(err)
            self.prediction_count += 1

            # LMS weight update
            for out_ch, act_level in acts.items():
                if abs(act_level) > 1e-4:
                    pair = (out_ch, in_ch)
                    current_w = self.weights.get(pair, 0.0)
                    self.weights[pair] = current_w + self.learning_rate * err * act_level

        self.prediction_errors = dict(errors)
        return errors

    @property
    def mean_prediction_error(self) -> float:
        if self.prediction_count == 0:
            return 0.0
        return self.cumulative_error / self.prediction_count


@dataclass(slots=True)
class ChannelInterventionRecord:
    """Intervention vs baseline contrast evidence for agency evaluation.

    Strictly requires both intervention and baseline trials to compute differential effect (AUD-011).
    Tracks consistency across replications (AUD-046).
    """

    intervention_delta_sum: float = 0.0
    intervention_count: int = 0
    baseline_delta_sum: float = 0.0
    baseline_count: int = 0
    consistent_replications: int = 0
    last_intervention_delta: float = 0.0

    def record(self, delta: float, *, was_active: bool) -> None:
        if was_active:
            if self.intervention_count > 0:
                if (delta * self.last_intervention_delta > 0) and abs(delta) > 0.02:
                    self.consistent_replications += 1
            self.last_intervention_delta = delta
            self.intervention_count += 1
            self.intervention_delta_sum += abs(delta)
        else:
            self.baseline_count += 1
            self.baseline_delta_sum += abs(delta)

    @property
    def has_counterfactual_evidence(self) -> bool:
        """True only if both active intervention and passive baseline have been observed."""
        return self.intervention_count > 0 and self.baseline_count > 0

    @property
    def differential_effect(self) -> float:
        """Difference between effect under intervention vs baseline.

        Returns 0.0 if there is no counterfactual baseline (AUD-011).
        """
        if not self.has_counterfactual_evidence:
            return 0.0
        int_mean = self.intervention_delta_sum / self.intervention_count
        base_mean = self.baseline_delta_sum / self.baseline_count
        diff = int_mean - base_mean
        return max(0.0, diff)


class AgencyModel:
    """Discovers differential dependence of perceptual changes on own activity (P6).

    Answers: 'Which changes depend differentially on my activity?'
    Contrasts interventions vs non-interventions, tracks temporal ordering,
    and quantifies confidence of agency per channel and effector.
    """

    def __init__(self, *, min_trials: int = 4, min_baselines: int = 2) -> None:
        self.min_trials = min_trials
        self.min_baselines = min_baselines
        # (out_ch, in_ch) -> ChannelInterventionRecord
        self.contingency: dict[tuple[str, str], ChannelInterventionRecord] = {}
        self.controllability: dict[str, float] = {}  # in_ch -> score [0.0, 1.0]
        self.agency_confidence: dict[str, float] = {}  # out_ch -> score [0.0, 1.0]

    def record_step(
        self,
        activations: Mapping[str, float],
        observed_deltas: Mapping[str, float],
    ) -> None:
        """Observe one sensorimotor step and update agency evidence."""
        for out_ch, act in activations.items():
            was_active = abs(float(act)) > 0.05
            for in_ch, delta in observed_deltas.items():
                pair = (out_ch, in_ch)
                if pair not in self.contingency:
                    self.contingency[pair] = ChannelInterventionRecord()
                self.contingency[pair].record(delta, was_active=was_active)

        self._recompute_scores()

    def _recompute_scores(self) -> None:
        """Recompute controllability and agency confidence with counterfactual gating."""
        in_effects: dict[str, list[float]] = {}
        out_effects: dict[str, list[float]] = {}

        for (out_ch, in_ch), rec in self.contingency.items():
            # AUD-011: require both intervention count AND baseline count
            if rec.intervention_count < self.min_trials or rec.baseline_count < self.min_baselines:
                continue
            diff = rec.differential_effect
            # Factor in replication consistency (AUD-046)
            consistency_factor = min(1.0, 0.5 + 0.25 * rec.consistent_replications)
            adjusted_diff = diff * consistency_factor

            in_effects.setdefault(in_ch, []).append(adjusted_diff)
            out_effects.setdefault(out_ch, []).append(adjusted_diff)

        # Controllability for an input channel is max differential effect achieved by any effector
        for in_ch, diffs in in_effects.items():
            max_diff = max(diffs) if diffs else 0.0
            score = 1.0 / (1.0 + math.exp(-6.0 * (max_diff - 0.15)))
            self.controllability[in_ch] = max(0.0, min(1.0, score))

        # Agency confidence for an output channel is reliability of effecting differential change
        for out_ch, diffs in out_effects.items():
            max_diff = max(diffs) if diffs else 0.0
            conf = 1.0 / (1.0 + math.exp(-6.0 * (max_diff - 0.15)))
            self.agency_confidence[out_ch] = max(0.0, min(1.0, conf))

    def is_agentic(self, out_ch: str, threshold: float = 0.5) -> bool:
        return self.agency_confidence.get(out_ch, 0.0) >= threshold


@dataclass(slots=True)
class InferredBodyRegion:
    """An inferred region of somatic controllability."""

    region_id: str
    effector_channels: tuple[str, ...]
    correlated_sensor_channels: tuple[str, ...]
    confidence: float


class InferredBodySchema:
    """Dynamically acquired representation of embodiment based on agency (P7).

    Answers: 'What relatively stable set of agency relations constitutes my embodiment?'
    Contains NO anatomical terms or ground-truth body topology (Invariant A).
    Evolves purely from experience and updates when disruptions occur.
    """

    def __init__(self, *, confidence_threshold: float = 0.4) -> None:
        self.confidence_threshold = confidence_threshold
        self.self_caused_channels: set[str] = set()
        self.somatic_correlated_channels: set[str] = set()
        self.external_channels: set[str] = set()
        self.internal_channels: set[str] = set()
        self.regions: list[InferredBodyRegion] = []
        self.overall_confidence: float = 0.0
        self.disruption_detected: bool = False
        self.revision_count: int = 0

    def update_from_agency(
        self,
        agency_model: AgencyModel,
        perceptual_structure: PerceptualStructure,
        prediction_error: float = 0.0,
    ) -> None:
        """Update body schema boundaries based on agency and perceptual evidence."""
        previous_internal = set(self.internal_channels)
        new_self_caused: set[str] = set()
        new_somatic: set[str] = set()
        new_external: set[str] = set()

        for in_ch, score in agency_model.controllability.items():
            if score >= self.confidence_threshold:
                new_self_caused.add(in_ch)
            else:
                # Check if correlated with self-caused channels (somatic but less directly controllable, AUD-047)
                is_somatic = any(
                    abs(perceptual_structure.correlation(in_ch, sc)) > 0.5
                    for sc in new_self_caused
                )
                if is_somatic:
                    new_somatic.add(in_ch)
                else:
                    new_external.add(in_ch)

        new_internal = new_self_caused | new_somatic

        # Detect disruption (e.g. port permutation or effector failure causing sudden loss/shift)
        if previous_internal and (previous_internal != new_internal or prediction_error > 0.5):
            self.disruption_detected = True
            self.revision_count += 1
        else:
            self.disruption_detected = False

        self.self_caused_channels = new_self_caused
        self.somatic_correlated_channels = new_somatic
        self.internal_channels = new_internal
        self.external_channels = new_external

        # Construct inferred controllable regions
        new_regions: list[InferredBodyRegion] = []
        for out_ch, conf in agency_model.agency_confidence.items():
            if conf >= self.confidence_threshold:
                paired_inputs: list[str] = []
                for (o, in_ch), rec in agency_model.contingency.items():
                    if o == out_ch and in_ch in new_internal and rec.differential_effect > 0.05:
                        paired_inputs.append(in_ch)
                region_id = f"region.{out_ch}"
                new_regions.append(
                    InferredBodyRegion(
                        region_id=region_id,
                        effector_channels=(out_ch,),
                        correlated_sensor_channels=tuple(sorted(paired_inputs)),
                        confidence=conf,
                    )
                )

        self.regions = new_regions
        confs = [r.confidence for r in self.regions]
        self.overall_confidence = sum(confs) / len(confs) if confs else 0.0


class InferredSelfModel:
    """Models continuity, cognitive persistence, and integrity (P8).

    Answers: 'Which processes seem to form part of my own continuity?'
    Strictly decoupled from BodySchema: does NOT describe physical body parts.
    Starts uncalibrated (AUD-048) and NEVER receives external embodiment IDs (AUD-013).
    """

    def __init__(self, symbiont_id: str) -> None:
        self.symbiont_id = symbiont_id
        self.ticks_experienced: int = 0
        # AUD-048: starts uncalibrated at 0.5, building confidence from experience
        self.historical_stability: float = 0.5
        self.integrity_confidence: float = 0.5

    def record_tick(
        self,
        *,
        body_schema_confidence: float,
        prediction_error: float,
    ) -> None:
        """Update self-model continuity metrics purely from internal signals."""
        self.ticks_experienced += 1

        # Update stability based on prediction errors
        error_penalty = min(0.5, prediction_error)
        self.historical_stability = (
            0.95 * self.historical_stability + 0.05 * (1.0 - error_penalty)
        )
        self.integrity_confidence = (
            0.9 * self.integrity_confidence + 0.1 * body_schema_confidence
        )


__all__ = [
    "AgencyModel",
    "ChannelInterventionRecord",
    "ChannelStat",
    "InferredBodyRegion",
    "InferredBodySchema",
    "InferredSelfModel",
    "PerceptualStructure",
    "SensorimotorModel",
]

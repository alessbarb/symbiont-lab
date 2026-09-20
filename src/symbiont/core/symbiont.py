"""Autonomous cognitive seed with continuous identity (v1.0 embodiment architecture).

Under the multidimensional evolutionary inheritance architecture, Symbiont is:
'un germen de organización cognitiva autónoma capaz de ser implantado en un
cuerpo digital desconocido y convertir progresivamente ese acoplamiento en un individuo.'

Key properties:
- Autonomous cognitive continuity with persistent `symbiont_id`.
- Operates strictly on opaque signal channels (Invariant A).
- Builds inferred perceptual, sensorimotor, agency, and body representations
  purely from experiential contingency.
- When transplanted to a new Body, its cognitive continuity is preserved while
  its body schema adjusts to the new causal reality.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import random
from typing import Mapping, Sequence

from .agency import (
    AgencyModel,
    InferredBodySchema,
    InferredSelfModel,
    PerceptualStructure,
    SensorimotorModel,
)
from .germline import GermlineState, SymbiontGenome


class Symbiont:
    """Autonomous cognitive seed capable of embodiment in unknown digital bodies."""

    def __init__(
        self,
        symbiont_id: str,
        *,
        learning_rate: float = 0.1,
        exploration_rate: float = 0.2,
        seed: int = 42,
        genome: SymbiontGenome | None = None,
        germline: GermlineState | None = None,
    ) -> None:
        if not symbiont_id:
            raise ValueError("symbiont_id must not be empty")
        self.symbiont_id = symbiont_id
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate
        self._rng = random.Random(seed)
        self.genome = genome
        self.germline = germline

        # Inferred models hierarchy (P4 - P8)
        self.perceptual_structure = PerceptualStructure()
        self.sensorimotor_model = SensorimotorModel(learning_rate=learning_rate)
        self.agency_model = AgencyModel()
        self.body_schema = InferredBodySchema()
        self.self_model = InferredSelfModel(symbiont_id)

        # Operational state
        self.last_inputs: dict[str, float] = {}
        self.last_activations: dict[str, float] = {}
        self.total_ticks: int = 0
        self.current_output_channels: set[str] = set()
        self.historical_output_channels: set[str] = set()

    def register_output_channels(self, channels: Sequence[str]) -> None:
        """Inform the cognitive seed of currently available opaque output channels (AUD-031)."""
        self.current_output_channels = set(channels)
        self.historical_output_channels.update(channels)

    @property
    def known_output_channels(self) -> set[str]:
        return set(self.current_output_channels)

    def step(
        self,
        opaque_inputs: Mapping[str, float],
    ) -> dict[str, float]:
        """Perform one cognitive tick given purely opaque input readings.

        Answers only to opaque experiential inputs. Does NOT receive external
        embodiment IDs or ground truth indicators (AUD-013).
        """
        self.total_ticks += 1
        current_inputs = {k: float(v) for k, v in opaque_inputs.items()}

        # 1. Perceptual regularities
        self.perceptual_structure.observe(current_inputs)

        # 2. Compute deltas
        deltas: dict[str, float] = {}
        for ch, val in current_inputs.items():
            prev = self.last_inputs.get(ch, val)
            deltas[ch] = val - prev

        # 3. Sensorimotor and Agency updates
        pred_err = 0.0
        if self.last_activations and deltas:
            errors = self.sensorimotor_model.update(deltas, self.last_activations)
            if errors:
                pred_err = sum(errors.values()) / len(errors)
            self.agency_model.record_step(self.last_activations, deltas)

        # 4. Body schema & Self model updates (strictly internal cues, AUD-013, AUD-014)
        self.body_schema.update_from_agency(
            self.agency_model, self.perceptual_structure, prediction_error=pred_err
        )
        self.self_model.record_tick(
            body_schema_confidence=self.body_schema.overall_confidence,
            prediction_error=pred_err,
        )

        # 5. Generate next activations
        outputs_to_drive = list(self.current_output_channels)
        if not outputs_to_drive and self.last_activations:
            outputs_to_drive = list(self.last_activations.keys())

        next_activations: dict[str, float] = {}
        for out_ch in outputs_to_drive:
            # Natural alternation of active exploration vs passive resting trials (AUD-012, AUD-045)
            # 25% chance of passive baseline trial to allow counterfactual contrast
            if self._rng.random() < 0.25:
                level = 0.0
            else:
                conf = self.agency_model.agency_confidence.get(out_ch, 0.0)
                if self.body_schema.disruption_detected or conf < 0.4:
                    level = self._rng.uniform(0.1, 1.0)
                else:
                    prev = self.last_activations.get(out_ch, 0.5)
                    noise = self._rng.gauss(0.0, self.exploration_rate)
                    level = max(0.0, min(1.0, prev + noise))
            next_activations[out_ch] = level

        # Form forward predictions for the chosen activations
        if current_inputs:
            self.sensorimotor_model.predict_deltas(
                next_activations, list(current_inputs.keys())
            )

        self.last_inputs = current_inputs
        self.last_activations = dict(next_activations)
        return next_activations


__all__ = ["Symbiont"]

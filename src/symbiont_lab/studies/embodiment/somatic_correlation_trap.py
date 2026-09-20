"""E5 adversarial falsification study: somatic-correlation trap.

The genuine somatic signal is produced by an actual Body physiological state
and routed through an actual ReceptorPort + EmbodimentSession. External controls
are evaluator/world processes transduced through separate physical receptors.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Sequence

from symbiont.core.agency import AgencyModel, InferredBodySchema, PerceptualStructure
from symbiont.core.body import Body, BodyPhysiology, EffectorPort, ReceptorPort
from symbiont.core.embodiment import implant_body

_STUDY_ID = "embodiment.somatic-correlation-trap"
MAX_EXTERNAL_ASSIMILATION_RATE = 0.10
MIN_TRUE_SOMATIC_RATE = 0.70


@dataclass(frozen=True, slots=True)
class SomaticTrapSeedResult:
    seed: int
    self_caused_detected: bool
    true_somatic_detected: bool
    external_correlated_assimilated: bool
    external_independent_assimilated: bool
    self_controllability: float
    true_somatic_controllability: float
    external_correlated_controllability: float
    true_somatic_correlation: float
    external_correlated_correlation: float
    body_schema_confidence: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SomaticCorrelationTrapStudy:
    seeds: tuple[int, ...]
    steps: int
    per_seed: tuple[SomaticTrapSeedResult, ...]
    true_somatic_rate: float
    external_assimilation_rate: float
    independent_assimilation_rate: float
    e5_true_somatic_gate: bool
    e5_external_rejection_gate: bool
    replay_deterministic: bool
    h1_supported: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": _STUDY_ID,
            "seeds": list(self.seeds),
            "steps": self.steps,
            "per_seed": [item.as_dict() for item in self.per_seed],
            "true_somatic_rate": self.true_somatic_rate,
            "external_assimilation_rate": self.external_assimilation_rate,
            "independent_assimilation_rate": self.independent_assimilation_rate,
            "e5_true_somatic_gate": self.e5_true_somatic_gate,
            "e5_external_rejection_gate": self.e5_external_rejection_gate,
            "replay_deterministic": self.replay_deterministic,
            "h1_supported": self.h1_supported,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise ValueError("seeds must be a sequence of unique integers")
    result = tuple(seeds)
    if not result or len(result) > 64 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 64 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must contain integers only")
    return result


def _make_body(seed: int) -> tuple[Body, EffectorPort]:
    physiology = BodyPhysiology(
        energy_reserve=100.0,
        max_energy=100.0,
        structural_integrity=1.0,
        temperature=0.0,
        basal_metabolic_rate=0.0,
        degradation_rate=0.0,
    )
    eff = EffectorPort(
        port_id=f"physical-eff-{seed}",
        kind="impulse",
        ordinal=0,
        efficiency=1.0,
        cost_per_activation=0.02,
    )
    self_sensor = ReceptorPort(
        port_id=f"physical-self-{seed}",
        kind="proprioceptive",
        ordinal=0,
        read_fn=lambda: eff.last_consequence,
    )
    somatic_sensor = ReceptorPort(
        port_id=f"physical-soma-{seed}",
        kind="interoceptive",
        ordinal=1,
        read_fn=lambda: physiology.temperature,
    )
    ext_corr = ReceptorPort(
        port_id=f"physical-extcorr-{seed}",
        kind="exteroceptive",
        ordinal=2,
    )
    ext_indep = ReceptorPort(
        port_id=f"physical-extindep-{seed}",
        kind="exteroceptive",
        ordinal=3,
    )
    body = Body(
        f"e5-body-{seed}",
        morphology_name="e5-physical-assay",
        receptors=(self_sensor, somatic_sensor, ext_corr, ext_indep),
        effectors=(eff,),
        physiology=physiology,
    )
    return body, eff


def _run_seed(seed: int, *, steps: int) -> SomaticTrapSeedResult:
    rng = random.Random(seed)
    perceptual = PerceptualStructure()
    agency = AgencyModel()
    schema = InferredBodySchema()
    body, eff = _make_body(seed)
    session = implant_body(f"e5-sym-{seed}", body)

    previous_inputs: dict[str, float] | None = None

    for _ in range(steps):
        act = 0.0 if rng.random() < 0.30 else rng.uniform(0.25, 1.0)

        # Real physical actuation.
        body.apply_activations({eff.port_id: act})

        # Body-internal physical thermal response: activity raises temperature,
        # rest lets it decay. This is apparatus physics, not a cognitive label.
        body.physiology.temperature = max(
            0.0,
            min(1.0, 0.65 * body.physiology.temperature + 0.35 * eff.last_consequence),
        )

        # External world processes. One shadows bodily activity closely; the
        # other is an independent bounded environmental process.
        ext_corr_port = body.ordered_receptors[2]
        ext_indep_port = body.ordered_receptors[3]
        ext_corr_port.current_value = max(
            0.0, min(1.0, 0.82 * eff.last_consequence + rng.gauss(0.0, 0.02))
        )
        ext_indep_port.current_value = max(
            0.0, min(1.0, 0.75 * ext_indep_port.current_value + rng.uniform(-0.12, 0.12))
        )

        physical = body.transduce_signals()
        opaque = session.transduce_to_symbiont(physical)
        perceptual.observe(opaque)

        if previous_inputs is not None:
            deltas = {
                ch: value - previous_inputs.get(ch, value)
                for ch, value in opaque.items()
            }
            agency.record_step({"out.0": act}, deltas)
        previous_inputs = dict(opaque)

    schema.update_from_agency(agency, perceptual)

    # Ordinals define canonical opaque mapping: 0=self, 1=somatic,
    # 2=external-correlated, 3=external-independent.
    self_ch, soma_ch, ext_corr_ch, ext_indep_ch = "in.0", "in.1", "in.2", "in.3"

    return SomaticTrapSeedResult(
        seed=seed,
        self_caused_detected=self_ch in schema.self_caused_channels,
        true_somatic_detected=soma_ch in schema.somatic_correlated_channels,
        external_correlated_assimilated=ext_corr_ch in schema.internal_channels,
        external_independent_assimilated=ext_indep_ch in schema.internal_channels,
        self_controllability=float(agency.controllability.get(self_ch, 0.0)),
        true_somatic_controllability=float(agency.controllability.get(soma_ch, 0.0)),
        external_correlated_controllability=float(agency.controllability.get(ext_corr_ch, 0.0)),
        true_somatic_correlation=float(perceptual.correlation(soma_ch, self_ch)),
        external_correlated_correlation=float(perceptual.correlation(ext_corr_ch, self_ch)),
        body_schema_confidence=float(schema.overall_confidence),
    )


def run_somatic_correlation_trap_study(
    *,
    seeds: Sequence[int] = (101,127,149,173,211,257,307,353,401,457),
    steps: int = 600,
) -> SomaticCorrelationTrapStudy:
    normalized = _normalize_seeds(seeds)
    if steps < 50 or steps > 100_000:
        raise ValueError("steps must be within [50,100000]")

    results = tuple(_run_seed(seed, steps=steps) for seed in normalized)
    replay = tuple(_run_seed(seed, steps=steps) for seed in normalized)

    true_rate = sum(item.true_somatic_detected for item in results) / len(results)
    external_rate = sum(item.external_correlated_assimilated for item in results) / len(results)
    independent_rate = sum(item.external_independent_assimilated for item in results) / len(results)

    true_gate = true_rate >= MIN_TRUE_SOMATIC_RATE
    external_gate = external_rate <= MAX_EXTERNAL_ASSIMILATION_RATE
    replay_deterministic = results == replay

    return SomaticCorrelationTrapStudy(
        seeds=normalized,
        steps=steps,
        per_seed=results,
        true_somatic_rate=true_rate,
        external_assimilation_rate=external_rate,
        independent_assimilation_rate=independent_rate,
        e5_true_somatic_gate=true_gate,
        e5_external_rejection_gate=external_gate,
        replay_deterministic=replay_deterministic,
        h1_supported=true_gate and external_gate and replay_deterministic,
    )


__all__ = [
    "SomaticTrapSeedResult",
    "SomaticCorrelationTrapStudy",
    "run_somatic_correlation_trap_study",
]

"""Portable durable representation of one Symbiont cognitive identity.

The file deliberately excludes Body, EmbodimentSession and world/physics state.
It can therefore be implanted into a different body without carrying anatomical
ground truth across the boundary.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .agency import (
    AgencyModel,
    ChannelInterventionRecord,
    ChannelStat,
    InferredBodyRegion,
    InferredBodySchema,
    InferredSelfModel,
    PerceptualStructure,
    SensorimotorModel,
)
from .germline import (
    EpigeneticMark,
    GermlineState,
    LocusSpec,
    LocusType,
    SymbiontGenome,
)
from .regulation import PhenotypicRegulationState
from .symbiont import Symbiont


SYMBIONT_FILE_SCHEMA_VERSION = 1


class SymbiontFileError(ValueError):
    """Raised when a portable Symbiont file is malformed or incompatible."""


def _jsonable_state(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable_state(item) for item in value]
    if isinstance(value, list):
        return [_jsonable_state(item) for item in value]
    return value


def _tuple_state(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuple_state(item) for item in value)
    return value


def _export_spec(spec: LocusSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "locus_type": str(spec.locus_type),
        "minimum": spec.minimum,
        "maximum": spec.maximum,
        "default_value": spec.default_value,
        "mutation_rate": spec.mutation_rate,
        "mutation_sigma": spec.mutation_sigma,
        "inheritable": spec.inheritable,
        "epigenetically_regulable": spec.epigenetically_regulable,
    }


def _restore_spec(payload: Mapping[str, Any]) -> LocusSpec:
    return LocusSpec(
        name=str(payload["name"]),
        locus_type=LocusType(str(payload["locus_type"])),
        minimum=payload["minimum"],
        maximum=payload["maximum"],
        default_value=payload["default_value"],
        mutation_rate=float(payload.get("mutation_rate", 0.1)),
        mutation_sigma=float(payload.get("mutation_sigma", 0.05)),
        inheritable=bool(payload.get("inheritable", True)),
        epigenetically_regulable=bool(payload.get("epigenetically_regulable", True)),
    )


def _export_mark(mark: EpigeneticMark) -> dict[str, Any]:
    return {
        "locus": mark.locus,
        "delta": mark.delta,
        "strength": mark.strength,
        "generations_left": mark.generations_left,
    }


def _restore_mark(payload: Mapping[str, Any]) -> EpigeneticMark:
    return EpigeneticMark(
        locus=str(payload["locus"]),
        delta=float(payload["delta"]),
        strength=float(payload.get("strength", 1.0)),
        generations_left=int(payload.get("generations_left", 3)),
    )


def export_symbiont(symbiont: Symbiont) -> dict[str, Any]:
    """Export organism-owned cognitive continuity only."""
    genome = None
    if symbiont.genome is not None:
        genome = {
            "genome_id": symbiont.genome.genome_id,
            "loci_values": dict(symbiont.genome.loci_values),
            "parent_ids": list(symbiont.genome.parent_ids),
            "specs": {
                name: _export_spec(spec)
                for name, spec in symbiont.genome.specs.items()
            },
        }

    germline = None
    if symbiont.germline is not None:
        germline = {
            "birth_expression": dict(symbiont.germline.birth_expression),
            "inherited_marks": {
                name: _export_mark(mark)
                for name, mark in symbiont.germline.inherited_marks.items()
            },
            "acquired_marks": {
                name: _export_mark(mark)
                for name, mark in symbiont.germline.acquired_marks.items()
            },
        }

    percept = symbiont.perceptual_structure
    sensorimotor = symbiont.sensorimotor_model
    agency = symbiont.agency_model
    schema = symbiont.body_schema
    self_model = symbiont.self_model

    regulator = None
    if symbiont.phenotypic_regulator is not None:
        r = symbiont.phenotypic_regulator
        regulator = {
            "birth_expression": dict(r.birth_expression),
            "current_expression": dict(r.current_expression),
            "prediction_error_ema": r.prediction_error_ema,
            "error_initialized": r.error_initialized,
            "stable_shift_ticks": dict(r.stable_shift_ticks),
            "min_capture_delta": r.min_capture_delta,
            "persistence_ticks_required": r.persistence_ticks_required,
            "error_ema_alpha": r.error_ema_alpha,
            "expression_adaptation_rate": r.expression_adaptation_rate,
        }

    return {
        "schema_version": SYMBIONT_FILE_SCHEMA_VERSION,
        "artifact_type": "portable-symbiont",
        "symbiont_id": symbiont.symbiont_id,
        "genome": genome,
        "germline": germline,
        "phenotype": {
            "learning_rate": symbiont.learning_rate,
            "exploration_rate": symbiont.exploration_rate,
            "expressed_loci": dict(symbiont.expressed_loci),
            "regulator": regulator,
            "last_epigenetic_capture": list(symbiont.last_epigenetic_capture),
            "epigenetic_capture_count": symbiont.epigenetic_capture_count,
        },
        "continuity": {
            "total_ticks": symbiont.total_ticks,
            "rng_state": _jsonable_state(symbiont._rng.getstate()),
            "last_inputs": dict(symbiont.last_inputs),
            "last_activations": dict(symbiont.last_activations),
            "current_output_channels": sorted(symbiont.current_output_channels),
            "historical_output_channels": sorted(symbiont.historical_output_channels),
        },
        "perceptual_structure": {
            "alpha": percept.alpha,
            "history_ticks": percept._history_ticks,
            "channel_stats": {
                channel: {
                    "count": stat.count,
                    "mean": stat.mean,
                    "m2": stat.m2,
                    "last_value": stat.last_value,
                }
                for channel, stat in percept.channel_stats.items()
            },
            "cross_cov": [
                [a, b, value]
                for (a, b), value in sorted(percept.cross_cov.items())
            ],
        },
        "sensorimotor_model": {
            "learning_rate": sensorimotor.learning_rate,
            "weights": [
                [out_ch, in_ch, value]
                for (out_ch, in_ch), value in sorted(sensorimotor.weights.items())
            ],
            "last_predictions": dict(sensorimotor.last_predictions),
            "last_activations": dict(sensorimotor.last_activations),
            "prediction_errors": dict(sensorimotor.prediction_errors),
            "cumulative_error": sensorimotor.cumulative_error,
            "prediction_count": sensorimotor.prediction_count,
        },
        "agency_model": {
            "min_trials": agency.min_trials,
            "min_baselines": agency.min_baselines,
            "contingency": [
                {
                    "out": out_ch,
                    "in": in_ch,
                    "intervention_delta_sum": rec.intervention_delta_sum,
                    "intervention_count": rec.intervention_count,
                    "baseline_delta_sum": rec.baseline_delta_sum,
                    "baseline_count": rec.baseline_count,
                    "consistent_replications": rec.consistent_replications,
                    "last_intervention_delta": rec.last_intervention_delta,
                }
                for (out_ch, in_ch), rec in sorted(agency.contingency.items())
            ],
            "controllability": dict(agency.controllability),
            "agency_confidence": dict(agency.agency_confidence),
        },
        "body_schema": {
            "confidence_threshold": schema.confidence_threshold,
            "self_caused_channels": sorted(schema.self_caused_channels),
            "somatic_correlated_channels": sorted(schema.somatic_correlated_channels),
            "external_channels": sorted(schema.external_channels),
            "internal_channels": sorted(schema.internal_channels),
            "regions": [
                {
                    "region_id": region.region_id,
                    "effector_channels": list(region.effector_channels),
                    "correlated_sensor_channels": list(region.correlated_sensor_channels),
                    "confidence": region.confidence,
                }
                for region in schema.regions
            ],
            "overall_confidence": schema.overall_confidence,
            "disruption_detected": schema.disruption_detected,
            "revision_count": schema.revision_count,
        },
        "self_model": {
            "ticks_experienced": self_model.ticks_experienced,
            "historical_stability": self_model.historical_stability,
            "integrity_confidence": self_model.integrity_confidence,
        },
    }


def restore_symbiont(payload: Mapping[str, Any]) -> Symbiont:
    """Restore a portable cognitive identity without restoring any Body."""
    if int(payload.get("schema_version", -1)) != SYMBIONT_FILE_SCHEMA_VERSION:
        raise SymbiontFileError("unsupported portable Symbiont schema")
    if payload.get("artifact_type") != "portable-symbiont":
        raise SymbiontFileError("not a portable Symbiont artifact")

    genome_payload = payload.get("genome")
    genome = None
    if genome_payload is not None:
        specs = {
            str(name): _restore_spec(spec_payload)
            for name, spec_payload in dict(genome_payload.get("specs", {})).items()
        }
        genome = SymbiontGenome(
            genome_id=str(genome_payload["genome_id"]),
            loci_values=dict(genome_payload.get("loci_values", {})),
            parent_ids=tuple(str(x) for x in genome_payload.get("parent_ids", ())),
            specs=specs,
        )

    germline_payload = payload.get("germline")
    germline = None
    if germline_payload is not None:
        germline = GermlineState(
            birth_expression={
                str(k): float(v)
                for k, v in dict(germline_payload.get("birth_expression", {})).items()
            },
            inherited_marks={
                str(name): _restore_mark(mark)
                for name, mark in dict(germline_payload.get("inherited_marks", {})).items()
            },
            acquired_marks={
                str(name): _restore_mark(mark)
                for name, mark in dict(germline_payload.get("acquired_marks", {})).items()
            },
        )

    phenotype = dict(payload.get("phenotype", {}))
    symbiont = Symbiont(
        str(payload["symbiont_id"]),
        learning_rate=float(phenotype.get("learning_rate", 0.1)),
        exploration_rate=float(phenotype.get("exploration_rate", 0.2)),
        seed=0,
        genome=genome,
        germline=germline,
    )

    continuity = dict(payload.get("continuity", {}))
    if "rng_state" in continuity:
        symbiont._rng.setstate(_tuple_state(continuity["rng_state"]))
    symbiont.total_ticks = int(continuity.get("total_ticks", 0))
    symbiont.last_inputs = {
        str(k): float(v) for k, v in dict(continuity.get("last_inputs", {})).items()
    }
    symbiont.last_activations = {
        str(k): float(v) for k, v in dict(continuity.get("last_activations", {})).items()
    }
    symbiont.current_output_channels = set(
        str(x) for x in continuity.get("current_output_channels", ())
    )
    symbiont.historical_output_channels = set(
        str(x) for x in continuity.get("historical_output_channels", ())
    )

    pp = dict(payload.get("perceptual_structure", {}))
    percept = PerceptualStructure(alpha=float(pp.get("alpha", 0.05)))
    percept._history_ticks = int(pp.get("history_ticks", 0))
    for channel, stat_payload in dict(pp.get("channel_stats", {})).items():
        stat = ChannelStat(
            count=int(stat_payload.get("count", 0)),
            mean=float(stat_payload.get("mean", 0.0)),
            m2=float(stat_payload.get("m2", 0.0)),
            last_value=float(stat_payload.get("last_value", 0.0)),
        )
        percept.channel_stats[str(channel)] = stat
    percept.cross_cov = {
        (str(a), str(b)): float(value)
        for a, b, value in pp.get("cross_cov", ())
    }
    symbiont.perceptual_structure = percept

    sp = dict(payload.get("sensorimotor_model", {}))
    sensorimotor = SensorimotorModel(
        learning_rate=float(sp.get("learning_rate", symbiont.learning_rate))
    )
    sensorimotor.weights = {
        (str(out_ch), str(in_ch)): float(value)
        for out_ch, in_ch, value in sp.get("weights", ())
    }
    sensorimotor.last_predictions = {
        str(k): float(v) for k, v in dict(sp.get("last_predictions", {})).items()
    }
    sensorimotor.last_activations = {
        str(k): float(v) for k, v in dict(sp.get("last_activations", {})).items()
    }
    sensorimotor.prediction_errors = {
        str(k): float(v) for k, v in dict(sp.get("prediction_errors", {})).items()
    }
    sensorimotor.cumulative_error = float(sp.get("cumulative_error", 0.0))
    sensorimotor.prediction_count = int(sp.get("prediction_count", 0))
    symbiont.sensorimotor_model = sensorimotor

    ap = dict(payload.get("agency_model", {}))
    agency = AgencyModel(
        min_trials=int(ap.get("min_trials", 4)),
        min_baselines=int(ap.get("min_baselines", 2)),
    )
    for item in ap.get("contingency", ()):
        agency.contingency[(str(item["out"]), str(item["in"]))] = ChannelInterventionRecord(
            intervention_delta_sum=float(item.get("intervention_delta_sum", 0.0)),
            intervention_count=int(item.get("intervention_count", 0)),
            baseline_delta_sum=float(item.get("baseline_delta_sum", 0.0)),
            baseline_count=int(item.get("baseline_count", 0)),
            consistent_replications=int(item.get("consistent_replications", 0)),
            last_intervention_delta=float(item.get("last_intervention_delta", 0.0)),
        )
    agency.controllability = {
        str(k): float(v) for k, v in dict(ap.get("controllability", {})).items()
    }
    agency.agency_confidence = {
        str(k): float(v) for k, v in dict(ap.get("agency_confidence", {})).items()
    }
    symbiont.agency_model = agency

    bp = dict(payload.get("body_schema", {}))
    schema = InferredBodySchema(
        confidence_threshold=float(bp.get("confidence_threshold", 0.4))
    )
    schema.self_caused_channels = set(str(x) for x in bp.get("self_caused_channels", ()))
    schema.somatic_correlated_channels = set(
        str(x) for x in bp.get("somatic_correlated_channels", ())
    )
    schema.external_channels = set(str(x) for x in bp.get("external_channels", ()))
    schema.internal_channels = set(str(x) for x in bp.get("internal_channels", ()))
    schema.regions = [
        InferredBodyRegion(
            region_id=str(item["region_id"]),
            effector_channels=tuple(str(x) for x in item.get("effector_channels", ())),
            correlated_sensor_channels=tuple(
                str(x) for x in item.get("correlated_sensor_channels", ())
            ),
            confidence=float(item.get("confidence", 0.0)),
        )
        for item in bp.get("regions", ())
    ]
    schema.overall_confidence = float(bp.get("overall_confidence", 0.0))
    schema.disruption_detected = bool(bp.get("disruption_detected", False))
    schema.revision_count = int(bp.get("revision_count", 0))
    symbiont.body_schema = schema

    smp = dict(payload.get("self_model", {}))
    self_model = InferredSelfModel(symbiont.symbiont_id)
    self_model.ticks_experienced = int(smp.get("ticks_experienced", 0))
    self_model.historical_stability = float(smp.get("historical_stability", 0.5))
    self_model.integrity_confidence = float(smp.get("integrity_confidence", 0.5))
    symbiont.self_model = self_model

    symbiont.expressed_loci = {
        str(k): float(v) for k, v in dict(phenotype.get("expressed_loci", {})).items()
    } or {
        "learning_rate": symbiont.learning_rate,
        "exploration_rate": symbiont.exploration_rate,
    }
    symbiont.last_epigenetic_capture = tuple(
        str(x) for x in phenotype.get("last_epigenetic_capture", ())
    )
    symbiont.epigenetic_capture_count = int(
        phenotype.get("epigenetic_capture_count", 0)
    )

    regulator_payload = phenotype.get("regulator")
    if regulator_payload is not None:
        specs = genome.specs if genome is not None else {}
        symbiont.phenotypic_regulator = PhenotypicRegulationState(
            birth_expression={
                str(k): float(v)
                for k, v in dict(regulator_payload.get("birth_expression", {})).items()
            },
            specs=specs,
            current_expression={
                str(k): float(v)
                for k, v in dict(regulator_payload.get("current_expression", {})).items()
            },
            prediction_error_ema=float(
                regulator_payload.get("prediction_error_ema", 0.0)
            ),
            error_initialized=bool(regulator_payload.get("error_initialized", False)),
            stable_shift_ticks={
                str(k): int(v)
                for k, v in dict(regulator_payload.get("stable_shift_ticks", {})).items()
            },
            min_capture_delta=float(regulator_payload.get("min_capture_delta", 0.02)),
            persistence_ticks_required=int(
                regulator_payload.get("persistence_ticks_required", 64)
            ),
            error_ema_alpha=float(regulator_payload.get("error_ema_alpha", 0.05)),
            expression_adaptation_rate=float(
                regulator_payload.get("expression_adaptation_rate", 0.08)
            ),
        )
    else:
        symbiont.phenotypic_regulator = None

    symbiont.learning_rate = float(phenotype.get("learning_rate", symbiont.learning_rate))
    symbiont.exploration_rate = float(
        phenotype.get("exploration_rate", symbiont.exploration_rate)
    )
    symbiont.sensorimotor_model.learning_rate = symbiont.learning_rate
    return symbiont


def save_symbiont_file(symbiont: Symbiont, path: str | Path) -> Path:
    """Atomically save one body-independent Symbiont artifact."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = export_symbiont(symbiont)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return target


def load_symbiont_file(path: str | Path) -> Symbiont:
    target = Path(path).expanduser()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SymbiontFileError(f"cannot load Symbiont file: {target}") from exc
    if not isinstance(payload, dict):
        raise SymbiontFileError("portable Symbiont root must be an object")
    return restore_symbiont(payload)


__all__ = [
    "SYMBIONT_FILE_SCHEMA_VERSION",
    "SymbiontFileError",
    "export_symbiont",
    "restore_symbiont",
    "save_symbiont_file",
    "load_symbiont_file",
]

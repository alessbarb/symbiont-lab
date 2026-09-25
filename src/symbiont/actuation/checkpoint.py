from __future__ import annotations

from typing import Any

from .candidate import ActuatorCandidateState
from .constitution import ActuatorConstitution
from .evidence_model import ActuatorEvidenceModel


def export_actuation_state(evidence_model: ActuatorEvidenceModel) -> dict[str, Any]:
    """Serialize established motor-discovery state (spec §11).

    Every candidate's full state round-trips unconditionally — this is the
    organism's own internal checkpoint, not a filtered report to an
    external observer (spec §16.6 rev5). No raw activation/percept
    HISTORY crosses this boundary (PairAccumulator stores bounded Welford
    aggregates, never a sample log), but nothing is withheld by sample
    count.
    """
    return {
        "candidates": {state.actuator_id: state.to_payload() for state in evidence_model.states},
    }


def restore_actuation_state(
    payload: dict[str, Any],
    constitution: ActuatorConstitution,
    *,
    organism_id: str,
    effect_threshold: float = 0.5,
) -> ActuatorEvidenceModel:
    """Rebuild an ActuatorEvidenceModel from a checkpoint payload.

    ``payload["candidates"]`` must contain EXACTLY one entry per
    ``constitution.actuator_ids`` — no more, no fewer (spec §15/P0.2).
    ``export_actuation_state`` always exports every candidate, so a payload
    missing one, or one that carries an unknown actuator_id, is a corrupted
    or foreign checkpoint. Silently accepting a partial candidate set would
    let a truncated checkpoint masquerade as "this organism never explored
    some of its actuators" — a plausible-looking but false developmental
    history. Each candidate's own ``actuator_id`` field must also match the
    dict key it is stored under, so a payload cannot smuggle candidate B's
    state in under key A (both being otherwise-known ids).

    ``effect_threshold`` is evidence_model *configuration*, not discovered state,
    and is not part of this payload — the caller supplies construct-
    equivalent config out of band (e.g. from ActuatorConstitution/genome-
    derived defaults). Only discovered candidate state round-trips via the
    payload itself.

    An ``active`` candidate's own recorded evidence must contain a valid
    historical promotion proof (spec §15 — corruption must raise, never
    silently accept an internally-impossible state): promotion is
    exclusively the canonical natural-evidence path (L6.2 — the scheduled
    probing-window promotion route was removed from the organism).
    """
    if "candidates" not in payload:
        raise ValueError("checkpoint payload missing required key 'candidates'")

    known_ids = set(constitution.actuator_ids)
    raw_candidates = payload["candidates"]
    if not isinstance(raw_candidates, dict):
        raise ValueError("candidates must be an object")

    payload_ids = set(raw_candidates)
    if payload_ids != known_ids:
        missing = known_ids - payload_ids
        unknown = payload_ids - known_ids
        raise ValueError(
            "checkpoint candidates do not match this organism's ActuatorConstitution — "
            f"missing={sorted(missing)} unknown={sorted(unknown)}"
        )

    evidence_model = ActuatorEvidenceModel(
        constitution,
        organism_id=organism_id,
        effect_threshold=effect_threshold,
    )
    for actuator_id, raw_state in raw_candidates.items():
        state = ActuatorCandidateState.from_payload(raw_state)
        if state.actuator_id != actuator_id:
            raise ValueError(
                f"checkpoint candidate stored under key {actuator_id!r} but its own "
                f"actuator_id field is {state.actuator_id!r} — key/field mismatch"
            )
        if state.probing_state == "active":
            # NOTE(promotion): Promotion is a historical event. Current cumulative correlation
            # may legitimately weaken after promotion as the organism gathers
            # more experience, so restore must validate the evidence that
            # promotion happened, not require today's effect_strength to still
            # clear the old threshold.
            strongest_relation_count = max(
                (relation.count for relation in state.effect_relations.values()),
                default=0,
            )
            # NOTE: New checkpoints persist natural_promotion_samples only at the
            # exact moment consider_natural_evidence() legitimately promotes
            # the candidate. That marker is therefore historical promotion
            # evidence in its own right; later correlation decay must not
            # invalidate it.
            if state.natural_promotion_samples > 0:
                natural_min_samples = state.natural_promotion_samples
                natural_promoted = strongest_relation_count >= natural_min_samples
            else:
                # NOTE(legacy): Legacy checkpoints predate the explicit promotion marker,
                # or predate L6.2's removal of scheduled-probing promotion.
                # Neither can prove natural promotion under the current
                # contract, so this candidate must re-earn it.
                natural_min_samples = 12
                natural_promoted = (
                    strongest_relation_count >= natural_min_samples
                    and state.effect_strength >= effect_threshold
                )

            if not natural_promoted:
                raise ValueError(
                    f"checkpoint candidate {actuator_id!r} claims probing_state='active' but its "
                    "own evidence does not satisfy natural promotion "
                    f"(strongest_relation_count={strongest_relation_count}, "
                    f"natural_min_samples={natural_min_samples}, "
                    f"effect_strength={state.effect_strength}, "
                    f"effect_threshold={effect_threshold})"
                )
        evidence_model._states[actuator_id] = state  # noqa: SLF001

    return evidence_model

"""Experimenter-authored ON/OFF actuator probing calendar — Lab apparatus only.

Relocated from ``symbiont.actuation`` (L6.1/L6.2): a scheduled ON/OFF
intervention calendar is organism-side scientific protocol, not constitutive
capacity — an organism must not carry a built-in experimental method. This
survives as an explicit Lab tool for matched intervention/control actuator
studies (docs/design symbiont-actuation-v1 §6-7, §16.D
"actuator-lesion-adaptation"), run from *outside* the subject.
"""

from __future__ import annotations

import random

from symbiont.actuation.types import ActuatorId
from symbiont.environment.rng import derive_seed


def probing_calendar(
    *, organism_id: str, actuator_id: ActuatorId, window_index: int, window_ticks: int
) -> tuple[bool, ...]:
    """A balanced, non-periodic ON/OFF schedule for one probing window.

    True means "activate the candidate this tick", False means "hold it at
    zero as a control". Deliberately not tick-parity-based: a fixed
    even/odd rule would alias with any period-2 environmental regularity
    and could be mistaken for actuator causality. The schedule is instead a
    balanced shuffle seeded independently of any percept, namespaced by
    organism, actuator and window so distinct windows use distinct orders.
    """
    if window_ticks < 1:
        raise ValueError("window_ticks must be at least 1")

    on_count = window_ticks // 2
    off_count = window_ticks - on_count
    schedule = [True] * on_count + [False] * off_count

    # derive_seed's own sha256 payload already encodes the full namespace
    # string; the base seed here is a fixed constant, not a Python hash()
    # of the namespace — str hash() is randomized per-process by default
    # (PYTHONHASHSEED) and would make this non-deterministic across runs.
    namespace = f"actuation:{organism_id}:{actuator_id}:{window_index}"
    seed = derive_seed(0, namespace)
    random.Random(seed).shuffle(schedule)
    return tuple(schedule)


__all__ = ["probing_calendar"]

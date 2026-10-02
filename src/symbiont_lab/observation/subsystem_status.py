"""Lifecycle status of cognitive subsystems, read from organism facts.

An empty panel must not be read as "nothing exists". The observer therefore
publishes, next to a subsystem's snapshot, *why* that snapshot is or is not
there. The status is derived read-only from public organism state; it never
infers anything from telemetry and never writes to the organism.
"""

from __future__ import annotations

from typing import Any

ABSENT = "absent"
DISABLED = "disabled"
NOT_READY = "not_ready"
IDLE = "idle"
ACTIVE = "active"
LIFECYCLES = (ABSENT, DISABLED, NOT_READY, IDLE, ACTIVE)


def generative_status(organism: Any) -> dict[str, Any]:
    """Where generative cognition stands for this organism at this tick."""
    subsystem = getattr(organism, "generative_cognition", None)
    if subsystem is None:
        return {"lifecycle": ABSENT, "reason": "runtime_has_no_generative_cognition"}

    budget = subsystem.budget
    status: dict[str, Any] = {
        "generative_tick": int(subsystem.generative_tick),
        "last_symbiont_tick": int(subsystem.last_symbiont_tick),
        "model_count": len(subsystem.registry.model_ids),
        "hypothesis_count": len(subsystem.hypotheses),
    }
    if min(budget.max_states, budget.max_transitions, budget.max_model_queries) == 0:
        return {**status, "lifecycle": DISABLED, "reason": "zero_budget"}
    if status["model_count"] == 0:
        return {**status, "lifecycle": NOT_READY, "reason": "no_generative_model"}
    workspace = subsystem.last_workspace
    if workspace is None:
        return {**status, "lifecycle": NOT_READY, "reason": "no_pass_yet"}
    if status["last_symbiont_tick"] < int(getattr(organism, "tick_count", 0)):
        return {**status, "lifecycle": IDLE, "reason": "no_pass_this_tick"}
    if not workspace.transitions and not workspace.model_queries:
        return {**status, "lifecycle": IDLE, "reason": "pass_without_work"}
    return {**status, "lifecycle": ACTIVE, "reason": "pass_with_work"}


__all__ = ["ABSENT", "ACTIVE", "DISABLED", "IDLE", "LIFECYCLES", "NOT_READY", "generative_status"]

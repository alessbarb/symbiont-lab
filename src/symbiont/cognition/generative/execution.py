"""Synchronous coordination of bounded generative opportunities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .agenda import AgendaCandidate, AgendaProgress, GenerativeAgenda
from .scheduler import GenerativeScheduler, ScheduleDecision
from .types import GenerativeMode
from .workspace import GenerativeWorkspace


@dataclass(frozen=True, slots=True)
class GenerativeExecutionResult:
    """Observable result of one coordinator pass."""

    decision: ScheduleDecision
    target_id: str | None
    progress: AgendaProgress | None


class GenerativeExecutionCoordinator:
    """Connect agenda selection and scheduling without granting action authority.

    The callback is intentionally supplied by the caller.  It receives only an
    opaque agenda candidate and mode, and must return agenda progress; the
    coordinator never invokes a world, motor, or factual-memory operation.
    """

    def __init__(self, *, agenda: GenerativeAgenda, scheduler: GenerativeScheduler) -> None:
        self.agenda = agenda
        self.scheduler = scheduler

    def run(
        self,
        *,
        mode: GenerativeMode,
        tick: int,
        workspace: GenerativeWorkspace,
        run_target: Callable[[AgendaCandidate, GenerativeMode], AgendaProgress],
    ) -> GenerativeExecutionResult:
        selected = self.agenda.select(tick=tick, limit=1)
        candidate = selected[0] if selected else None
        remaining_queries = max(0, workspace.budget.max_model_queries - workspace.model_queries)
        decision = self.scheduler.schedule(
            mode=mode,
            tick=tick,
            has_target=candidate is not None,
            workspace_open=workspace.is_open,
            model_queries_remaining=remaining_queries,
        )
        if candidate is None or not decision.allowed:
            return GenerativeExecutionResult(decision, None, None)

        progress = run_target(candidate, mode)
        if not isinstance(progress, AgendaProgress):
            raise ValueError("run_target must return AgendaProgress")
        self.agenda.record_progress(candidate.target.target_id, tick=tick, progress=progress)
        return GenerativeExecutionResult(decision, candidate.target.target_id, progress)


__all__ = ["GenerativeExecutionCoordinator", "GenerativeExecutionResult"]

"""Timing gate kept separate from agenda selection and workspace execution."""

from __future__ import annotations

from dataclasses import dataclass

from .types import GenerativeMode


@dataclass(frozen=True, slots=True)
class ScheduleDecision:
    allowed: bool
    mode: GenerativeMode
    tick: int
    reason: str


class GenerativeScheduler:
    """Decides whether an opportunity exists; it does not choose a target."""

    def __init__(
        self, *, online_quota: int = 1, idle_quota: int = 2, offline_quota: int = 4
    ) -> None:
        for name, value in (
            ("online_quota", online_quota),
            ("idle_quota", idle_quota),
            ("offline_quota", offline_quota),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        self._quotas = {
            GenerativeMode.ONLINE: online_quota,
            GenerativeMode.IDLE: idle_quota,
            GenerativeMode.OFFLINE: offline_quota,
        }
        self._used: dict[tuple[int, GenerativeMode], int] = {}

    def schedule(
        self,
        *,
        mode: GenerativeMode,
        tick: int,
        has_target: bool,
        workspace_open: bool,
        model_queries_remaining: int,
    ) -> ScheduleDecision:
        if not isinstance(mode, GenerativeMode):
            raise ValueError("mode must be a GenerativeMode")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("tick must be a non-negative integer")
        if (
            isinstance(model_queries_remaining, bool)
            or not isinstance(model_queries_remaining, int)
            or model_queries_remaining < 0
        ):
            raise ValueError("model_queries_remaining must be a non-negative integer")
        reason = "available"
        allowed = True
        if not has_target:
            allowed, reason = False, "no_target"
        elif not workspace_open:
            allowed, reason = False, "workspace_closed"
        elif model_queries_remaining == 0:
            allowed, reason = False, "model_budget_exhausted"
        elif self._used.get((tick, mode), 0) >= self._quotas[mode]:
            allowed, reason = False, "mode_quota_exhausted"
        if allowed:
            self._used[(tick, mode)] = self._used.get((tick, mode), 0) + 1
        return ScheduleDecision(allowed, mode, tick, reason)


__all__ = ["GenerativeScheduler", "ScheduleDecision"]

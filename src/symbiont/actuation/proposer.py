from __future__ import annotations

from .calendar import probing_calendar
from .candidate import ActuatorCandidateState
from .constitution import ActuatorConstitution
from .types import ActuatorId


class ActuatorProposer:
    """Bounded exploration of an organism's fixed motor body (spec §4).

    Only ``constitution.actuator_ids`` are ever considered — this never
    invents an actuator_id that isn't already part of the body.
    """

    def __init__(
        self,
        constitution: ActuatorConstitution,
        *,
        organism_id: str,
        min_probing_windows: int = 2,
        effect_threshold: float = 0.5,
        window_ticks: int = 8,
        probe_limit: int = 1,
    ) -> None:
        if min_probing_windows < 1:
            raise ValueError("min_probing_windows must be at least 1")
        if not 0.0 <= effect_threshold <= 1.0:
            raise ValueError("effect_threshold must be within [0.0, 1.0]")
        if window_ticks < 1:
            raise ValueError("window_ticks must be at least 1")
        if probe_limit < 1:
            raise ValueError("probe_limit must be at least 1")

        self._constitution = constitution
        self._organism_id = organism_id
        self._min_probing_windows = min_probing_windows
        self._effect_threshold = effect_threshold
        self._window_ticks = window_ticks
        self._probe_limit = probe_limit
        self._states: dict[ActuatorId, ActuatorCandidateState] = {
            actuator_id: ActuatorCandidateState(actuator_id=actuator_id)
            for actuator_id in constitution.actuator_ids
        }
        self._probe_cursor = 0

    @property
    def states(self) -> tuple[ActuatorCandidateState, ...]:
        return tuple(sorted(self._states.values(), key=lambda state: state.actuator_id))

    @property
    def active_repertoire(self) -> tuple[ActuatorId, ...]:
        return tuple(
            state.actuator_id for state in self.states if state.probing_state == "active"
        )

    def _candidates_for_probing(self) -> list[ActuatorId]:
        return [
            actuator_id
            for actuator_id, state in self._states.items()
            if state.probing_state in ("dormant", "probing")
        ]

    def probing_plan(self, *, tick: int) -> dict[ActuatorId, bool]:
        """Called once per real simulation tick.

        ``tick`` only drives the bounded rotation of *which* candidates get
        probed this tick (mirrors ``sampling_plan``'s cursor in
        host/adaptive.py); each actuator's ON/OFF value comes from its own
        per-actuator position within its own current window, tracked in
        that actuator's ``ActuatorCandidateState.tick_in_window`` — never
        from ``tick`` directly, so two actuators probed on different ticks
        still each see a complete, internally-consistent ``window_ticks``-
        long calendar. This phase is persisted (spec §11/P0.1): a checkpoint
        restore resumes mid-window rather than silently restarting it.
        """
        pool = sorted(self._candidates_for_probing())
        if not pool:
            return {}
        start = self._probe_cursor % len(pool)
        count = min(self._probe_limit, len(pool))
        selected = [pool[(start + offset) % len(pool)] for offset in range(count)]
        self._probe_cursor += count

        plan: dict[ActuatorId, bool] = {}
        for actuator_id in selected:
            state = self._states[actuator_id]
            if state.probing_state == "dormant":
                state.probing_state = "probing"
            calendar = probing_calendar(
                organism_id=self._organism_id,
                actuator_id=actuator_id,
                window_index=state.windows_completed,
                window_ticks=self._window_ticks,
            )
            position = state.tick_in_window
            plan[actuator_id] = calendar[position]
        return plan

    def record_effect(
        self, actuator_id: ActuatorId, percept_id: str, *, activation: float, delta_percept: float, tick: int
    ) -> None:
        state = self._states[actuator_id]
        state.observe_effect(percept_id, activation=activation, delta_percept=delta_percept)
        state.last_seen_tick = tick

    def consider_natural_evidence(self, actuator_id: ActuatorId, *, min_samples: int = 12) -> bool:
        """Promote an actuator from passive, naturally occurring covariance.

        Unlike probing_plan this method never schedules or requests an
        actuation. It only evaluates evidence produced by motor activity that
        happened for some other endogenous reason. This is the canonical clean
        World's P1 path: causal competence may be learned, but exploration is
        not supplied as an experimenter-authored ON/OFF protocol.
        """
        if min_samples < 3:
            raise ValueError("min_samples must be at least 3")
        state = self._states[actuator_id]
        strongest_count = max(
            (relation.count for relation in state.effect_relations.values()),
            default=0,
        )
        if strongest_count < min_samples or state.effect_strength < self._effect_threshold:
            return False
        state.probing_state = "active"
        state.natural_promotion_samples = int(min_samples)
        return True

    def advance_tick(self, actuator_id: ActuatorId) -> None:
        """Call once per tick for every actuator present in that tick's plan.

        The window phase (``state.tick_in_window``) is persisted via
        ``ActuatorCandidateState`` (spec §11/P0.1) — a checkpoint restore
        resumes at the same position in the same window's calendar rather
        than silently discarding partial-window progress.

        Promotion requires BOTH ``windows_completed >= min_probing_windows``
        (enough windows have elapsed) AND ``windows_with_effect >=
        min_probing_windows`` (the effect was independently detected in
        that many separate windows, not just accumulated into one high
        cumulative correlation by a single strong window — spec §6
        revisión 3) AND the all-time cumulative ``effect_strength`` clears
        ``effect_threshold``.
        """
        state = self._states[actuator_id]
        state.tick_in_window += 1
        if state.tick_in_window < self._window_ticks:
            return
        state.tick_in_window = 0
        state.windows_completed += 1
        state.complete_window(self._effect_threshold)
        if (
            state.windows_completed >= self._min_probing_windows
            and state.windows_with_effect >= self._min_probing_windows
            and state.effect_strength >= self._effect_threshold
        ):
            state.probing_state = "active"

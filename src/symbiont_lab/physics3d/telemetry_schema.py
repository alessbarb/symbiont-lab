"""Declarative temporal layout for Physics3D telemetry v4.1."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class TemporalClass(str, Enum):
    DENSE = "dense"
    STRUCTURAL = "structural"
    EVENT_EPHEMERAL = "event_ephemeral"
    EVENT_CUMULATIVE = "event_cumulative"
    STATIC = "static"


@dataclass(frozen=True, slots=True)
class LayoutRule:
    channel: str
    path: tuple[str, ...]
    temporal_class: TemporalClass


EVENT_RULES: tuple[LayoutRule, ...] = (
    LayoutRule(
        "runtime.knowledge_events",
        ("runtime", "knowledge_events"),
        TemporalClass.EVENT_EPHEMERAL,
    ),
    LayoutRule(
        "runtime.runtime_events",
        ("runtime", "runtime_events"),
        TemporalClass.EVENT_EPHEMERAL,
    ),
    LayoutRule(
        "runtime.experience_records_created",
        ("runtime", "experience_records_created"),
        TemporalClass.EVENT_EPHEMERAL,
    ),
    LayoutRule(
        "cognition.mutations",
        ("cognition", "mutations"),
        TemporalClass.EVENT_EPHEMERAL,
    ),
    LayoutRule(
        "cognition.recycling_events",
        ("cognition", "recycling_events"),
        TemporalClass.EVENT_EPHEMERAL,
    ),
    LayoutRule(
        "sensorimotor.episodes",
        ("sensorimotor", "episodes"),
        TemporalClass.EVENT_CUMULATIVE,
    ),
)

STATIC_RULES: tuple[LayoutRule, ...] = (
    LayoutRule(
        "observer_semantics",
        ("observer_semantics",),
        TemporalClass.STATIC,
    ),
)

LEGACY_V41_STRUCTURAL_RULES: tuple[LayoutRule, ...] = (
    LayoutRule(
        "cognitive_topology",
        ("cognitive_topology",),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "body_schema",
        ("body_schema",),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "runtime.signal_knowledge",
        ("runtime", "signal_knowledge"),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "runtime.sensory_phenotype",
        ("runtime", "sensory_phenotype"),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "self_model",
        ("self_model",),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "sensorimotor",
        ("sensorimotor",),
        TemporalClass.STRUCTURAL,
    ),
)

STRUCTURAL_RULES: tuple[LayoutRule, ...] = (
    LayoutRule(
        "cognitive_topology",
        ("cognitive_topology",),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "body_schema",
        ("body_schema",),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "runtime.signal_knowledge",
        ("runtime", "signal_knowledge"),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "runtime.sensory_phenotype",
        ("runtime", "sensory_phenotype"),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "runtime.narrative",
        ("runtime", "narrative"),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "runtime.signal_references",
        ("runtime", "signal_references"),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "self_model",
        ("self_model",),
        TemporalClass.STRUCTURAL,
    ),
    LayoutRule(
        "sensorimotor",
        ("sensorimotor",),
        TemporalClass.STRUCTURAL,
    ),
)

LEGACY_V41_DENSE_RULES: tuple[LayoutRule, ...] = (
    LayoutRule("pre", ("pre",), TemporalClass.DENSE),
    LayoutRule("post", ("post",), TemporalClass.DENSE),
    LayoutRule("runtime", ("runtime",), TemporalClass.DENSE),
    LayoutRule("cognition", ("cognition",), TemporalClass.DENSE),
    LayoutRule("action", ("action",), TemporalClass.DENSE),
    LayoutRule("physics", ("physics",), TemporalClass.DENSE),
    LayoutRule("outcome", ("outcome",), TemporalClass.DENSE),
    LayoutRule("timing_ms", ("timing_ms",), TemporalClass.DENSE),
    LayoutRule("slm", ("slm",), TemporalClass.DENSE),
    LayoutRule("episodic_memory", ("episodic_memory",), TemporalClass.DENSE),
)

DENSE_RULES: tuple[LayoutRule, ...] = (
    LayoutRule(
        "pre.physical",
        ("pre", "physical"),
        TemporalClass.DENSE,
    ),
    LayoutRule(
        "post.physical",
        ("post", "physical"),
        TemporalClass.DENSE,
    ),
    LayoutRule(
        "physics.raw_substeps",
        ("physics", "raw_substeps"),
        TemporalClass.DENSE,
    ),
    LayoutRule("pre", ("pre",), TemporalClass.DENSE),
    LayoutRule("post", ("post",), TemporalClass.DENSE),
    LayoutRule("runtime", ("runtime",), TemporalClass.DENSE),
    LayoutRule("cognition", ("cognition",), TemporalClass.DENSE),
    LayoutRule("action", ("action",), TemporalClass.DENSE),
    LayoutRule("physics", ("physics",), TemporalClass.DENSE),
    LayoutRule("outcome", ("outcome",), TemporalClass.DENSE),
    LayoutRule("timing_ms", ("timing_ms",), TemporalClass.DENSE),
    LayoutRule("slm", ("slm",), TemporalClass.DENSE),
    LayoutRule("episodic_memory", ("episodic_memory",), TemporalClass.DENSE),
)

ALL_RULES: tuple[LayoutRule, ...] = (
    *EVENT_RULES,
    *STATIC_RULES,
    *STRUCTURAL_RULES,
    *DENSE_RULES,
)


_MISSING = object()


def get_path(root: Mapping[str, Any], path: Iterable[str], default: Any = _MISSING) -> Any:
    current: Any = root
    for segment in path:
        if not isinstance(current, Mapping) or segment not in current:
            if default is _MISSING:
                raise KeyError("/" + "/".join(path))
            return default
        current = current[segment]
    return current


def pop_path(root: dict[str, Any], path: tuple[str, ...]) -> Any:
    if not path:
        raise ValueError("cannot pop root path")
    current: Any = root
    parents: list[tuple[dict[str, Any], str]] = []
    for segment in path[:-1]:
        if not isinstance(current, dict) or segment not in current:
            return _MISSING
        parents.append((current, segment))
        current = current[segment]
    if not isinstance(current, dict) or path[-1] not in current:
        return _MISSING
    value = current.pop(path[-1])
    # Prune containers created solely to reach an extracted nested value.
    for parent, segment in reversed(parents):
        child = parent.get(segment)
        if isinstance(child, dict) and not child:
            parent.pop(segment, None)
        else:
            break
    return value


def set_path(root: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    if not path:
        if not isinstance(value, Mapping):
            raise ValueError("root telemetry state must remain a mapping")
        root.clear()
        root.update(deepcopy(dict(value)))
        return
    current = root
    for segment in path[:-1]:
        child = current.get(segment)
        if not isinstance(child, dict):
            child = {}
            current[segment] = child
        current = child
    current[path[-1]] = deepcopy(value)


@dataclass(slots=True)
class PartitionedState:
    dense: dict[str, Any]
    structural: dict[str, Any]
    events: dict[str, Any]
    static: dict[str, Any]
    fallback: dict[str, Any]


def partition_state(
    state: Mapping[str, Any],
    *,
    layout_revision: int = 2,
) -> PartitionedState:
    """Split one logical state according to the v4.1 temporal contract.

    Nested event/structural paths are extracted before their parents. Anything
    not covered by the declared layout remains in exact fallback storage.
    """
    if int(layout_revision) <= 1:
        structural_rules = LEGACY_V41_STRUCTURAL_RULES
        dense_rules = LEGACY_V41_DENSE_RULES
    else:
        structural_rules = STRUCTURAL_RULES
        dense_rules = DENSE_RULES

    residual = deepcopy(dict(state))
    events: dict[str, Any] = {}
    static: dict[str, Any] = {}
    structural: dict[str, Any] = {}
    dense: dict[str, Any] = {}

    for rule in EVENT_RULES:
        value = pop_path(residual, rule.path)
        if value is not _MISSING:
            events[rule.channel] = value

    for rule in STATIC_RULES:
        value = pop_path(residual, rule.path)
        if value is not _MISSING:
            static[rule.channel] = value

    for rule in structural_rules:
        value = pop_path(residual, rule.path)
        if value is not _MISSING:
            structural[rule.channel] = value

    for rule in dense_rules:
        value = pop_path(residual, rule.path)
        if value is not _MISSING:
            dense[rule.channel] = value

    return PartitionedState(
        dense=dense,
        structural=structural,
        events=events,
        static=static,
        fallback=residual,
    )


_RULE_BY_CHANNEL = {rule.channel: rule for rule in ALL_RULES}


def rule_for_channel(channel: str) -> LayoutRule:
    try:
        return _RULE_BY_CHANNEL[channel]
    except KeyError as exc:
        raise KeyError(f"unknown telemetry channel: {channel}") from exc


def reassemble_state(
    *,
    dense: Mapping[str, Any],
    structural: Mapping[str, Any],
    events: Mapping[str, Any],
    static: Mapping[str, Any],
    fallback: Mapping[str, Any],
) -> dict[str, Any]:
    state = deepcopy(dict(fallback))
    classified: list[tuple[int, int, str, Any]] = []
    source_priority = {
        "static": 0,
        "dense": 1,
        "structural": 2,
        "events": 3,
    }
    for source_name, source in (
        ("static", static),
        ("dense", dense),
        ("structural", structural),
        ("events", events),
    ):
        for channel, value in source.items():
            rule = rule_for_channel(channel)
            classified.append(
                (
                    len(rule.path),
                    source_priority[source_name],
                    channel,
                    value,
                )
            )

    # Parent paths must be materialized before extracted children. Otherwise a
    # later parent assignment would erase already reconstructed nested state.
    for _depth, _priority, channel, value in sorted(
        classified,
        key=lambda item: (item[0], item[1], item[2]),
    ):
        set_path(state, rule_for_channel(channel).path, value)
    return state


def event_mode(channel: str) -> TemporalClass:
    rule = rule_for_channel(channel)
    if rule.temporal_class not in (
        TemporalClass.EVENT_EPHEMERAL,
        TemporalClass.EVENT_CUMULATIVE,
    ):
        raise ValueError(f"channel is not an event stream: {channel}")
    return rule.temporal_class


__all__ = [
    "ALL_RULES",
    "DENSE_RULES",
    "EVENT_RULES",
    "LEGACY_V41_DENSE_RULES",
    "LEGACY_V41_STRUCTURAL_RULES",
    "LayoutRule",
    "PartitionedState",
    "STATIC_RULES",
    "STRUCTURAL_RULES",
    "TemporalClass",
    "event_mode",
    "get_path",
    "partition_state",
    "pop_path",
    "reassemble_state",
    "rule_for_channel",
    "set_path",
]

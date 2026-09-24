from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import math
import secrets
from typing import Any

from ..cognition.self_model import MAX_COGNITIVE_CHANNELS_PER_TICK
from ..foundation.epistemic import DEFAULT_EPISTEMIC_CONVENTIONS, RecencyClass
from ..foundation.limits import OrganismLimits

_DEFAULT_LIMITS = OrganismLimits()
LEGACY_BODY_SCHEMA_VERSION = 1
BODY_SCHEMA_VERSION = 2
MAX_SENSORY_PARTS = _DEFAULT_LIMITS.max_sensory_parts
MAX_COGNITIVE_REGIONS = _DEFAULT_LIMITS.max_cognitive_regions
MAX_BODY_PARTS = _DEFAULT_LIMITS.max_body_parts
MAX_BODY_DEPENDENCIES = _DEFAULT_LIMITS.max_body_dependencies
MAX_DEPENDENCY_EVIDENCE = _DEFAULT_LIMITS.max_dependency_evidence
MAX_COGNITIVE_CHANNEL_CANDIDATES = _DEFAULT_LIMITS.max_cognitive_channel_candidates
MAX_COGNITIVE_REGION_MEMBERS = MAX_COGNITIVE_CHANNEL_CANDIDATES
MAX_COACTIVITY_CANDIDATES = _DEFAULT_LIMITS.max_coactivity_candidates

_HEALTH_CLASSES = DEFAULT_EPISTEMIC_CONVENTIONS.health_classes
_CONFIDENCE_CLASSES = DEFAULT_EPISTEMIC_CONVENTIONS.confidence_classes
_COST_CLASSES = DEFAULT_EPISTEMIC_CONVENTIONS.cost_classes
_MATURITY_CLASSES = DEFAULT_EPISTEMIC_CONVENTIONS.maturity_classes
_ACTIVITY_CLASSES = DEFAULT_EPISTEMIC_CONVENTIONS.activity_classes
_REGION_CHANNEL_SUPPORT_MIN = 4
_REGION_PAIR_SUPPORT_MIN = 3
_REGION_PAIR_DENSITY_MIN = 0.60
_REGION_MEMBER_COVERAGE_MIN = 0.60
_REGION_SUPPORT_CAP = 32
_REGION_EVIDENCE_CAP = 255
_REGION_RESTRUCTURE_INTERVAL = 4
_DEPENDENCY_SUPPORT_MIN = 6
_DEPENDENCY_CONFIDENCE_MIN_CLASS = 8
_DEPENDENCY_COUNTER_CAP = 255

_RECENCY_REPRESENTATIVE_IDLE_TICKS = DEFAULT_EPISTEMIC_CONVENTIONS.recency_representative_map()
_RECENCY_THRESHOLDS = tuple(
    (threshold, recency)
    for threshold, recency in zip(
        DEFAULT_EPISTEMIC_CONVENTIONS.recency_thresholds,
        (RecencyClass.CURRENT, RecencyClass.SHORT_IDLE, RecencyClass.IDLE, RecencyClass.LONG_IDLE),
    )
)


class DependencyKind(StrEnum):
    CO_ACTS_WITH = "co_acts_with"
    PRECEDES = "precedes"


def _is_lower_hex(value: str, *, length: int) -> bool:
    return len(value) == length and all(char in "0123456789abcdef" for char in value)


def _sense_part_id(id_salt: str, sense_id: str) -> str:
    digest = sha256(f"symbiont-body:{id_salt}:sense:{sense_id}".encode("utf-8")).hexdigest()[:32]
    return f"part.sense.{digest}"


def _region_part_id(id_salt: str, anchor_channel: str) -> str:
    digest = sha256(f"symbiont-body:{id_salt}:region:{anchor_channel}".encode("utf-8")).hexdigest()[:32]
    return f"part.region.{digest}"


def _valid_channel_id(value: str) -> bool:
    prefix = "channel.cognition."
    return value.startswith(prefix) and _is_lower_hex(value.removeprefix(prefix), length=32)


def _recency_class(idle_ticks: int) -> RecencyClass:
    for threshold, recency in _RECENCY_THRESHOLDS:
        if idle_ticks < threshold:
            return recency
    return RecencyClass.DORMANT


def _require_class(value: Any, count: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an int")
    if not 0 <= value < count:
        raise ValueError(f"{field_name} out of range [0, {count})")
    return value


def _existence_confidence_class(maturity_class: int) -> int:
    return round((maturity_class / (_MATURITY_CLASSES - 1)) * (_CONFIDENCE_CLASSES - 1))


def _maturity_from_evidence(evidence_count: int) -> int:
    thresholds = (2, 4, 8, 16, 32, 64, 128)
    maturity = 0
    for threshold in thresholds:
        if evidence_count >= threshold:
            maturity += 1
    return min(_MATURITY_CLASSES - 1, maturity)


def _ratio_class(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return max(0, min(_CONFIDENCE_CLASSES - 1, round((numerator / denominator) * 15)))


def _support_class(support_count: int) -> int:
    return max(0, min(15, support_count))


@dataclass(slots=True)
class _SensoryPartState:
    part_id: str
    health_class: int
    confidence_class: int
    cost_class: int
    maturity_class: int
    last_evidence_tick: int

    @property
    def existence_confidence_class(self) -> int:
        return _existence_confidence_class(self.maturity_class)


@dataclass(slots=True)
class _CognitiveRegionState:
    part_id: str
    members: tuple[str, ...]
    evidence_count: int
    confidence_class: int
    activity_class: int
    last_evidence_tick: int

    @property
    def maturity_class(self) -> int:
        return _maturity_from_evidence(self.evidence_count)

    @property
    def existence_confidence_class(self) -> int:
        return _existence_confidence_class(self.maturity_class)


@dataclass(slots=True)
class _DependencyEvidence:
    source_id: str
    target_id: str
    relation: DependencyKind
    support_count: int = 0
    opportunity_count: int = 0
    last_support_tick: int = 0

    @property
    def support_class(self) -> int:
        return _support_class(self.support_count)

    @property
    def confidence_class(self) -> int:
        return _ratio_class(self.support_count, self.opportunity_count)

    @property
    def exportable(self) -> bool:
        return (
            self.support_count >= _DEPENDENCY_SUPPORT_MIN
            and self.confidence_class >= _DEPENDENCY_CONFIDENCE_MIN_CLASS
        )


class BodySchemaEngine:
    """Bounded learned representation of the organism's functional body.

    Sensory parts are learned from SelfModel evidence. Cognitive regions are
    learned only from bounded opaque dynamic observations. The engine never
    receives CognitiveGraph nodes, edges, topology revisions or raw host
    capability identity.
    """

    def __init__(self, *, id_salt: str | None = None) -> None:
        if id_salt is None:
            id_salt = secrets.token_hex(16)
        if not isinstance(id_salt, str) or not _is_lower_hex(id_salt, length=32):
            raise ValueError("body_schema id_salt must be 32 lowercase hex characters")
        self._id_salt = id_salt
        self._parts: dict[str, _SensoryPartState] = {}
        self._regions: dict[str, _CognitiveRegionState] = {}
        self._channel_support: dict[str, int] = {}
        self._coactivity_support: dict[tuple[str, str], int] = {}
        self._dependency_evidence: dict[tuple[str, str, DependencyKind], _DependencyEvidence] = {}
        # This is intentionally ephemeral. Persisting it would let a restart
        # fabricate PRECEDES across a discontinuity in execution.
        self._previous_active_regions: set[str] = set()
        # A restored engine performs one full structural review before switching
        # to threshold-driven incremental maintenance. This flag is deliberately
        # ephemeral and therefore defaults to True on every construction/restore.
        self._full_structural_review_required = True
        self._pending_structural_channels: set[str] = set()

    @property
    def state(self) -> str:
        """Evidence state, never a claim of anatomical completeness."""
        if self.part_count == 0:
            return "undeveloped"
        if self._full_structural_review_required or self._pending_structural_channels:
            return "revising" if self._regions else "developing"

        mature_sensory = sum(
            1
            for part in self._parts.values()
            if part.maturity_class >= 4 and part.confidence_class >= 3
        )
        enough_sensory = (
            self.sensory_part_count > 0
            and mature_sensory >= max(1, self.sensory_part_count // 2)
        )
        stable_regions = sum(
            1
            for region in self._regions.values()
            if region.maturity_class >= 4 and region.confidence_class >= 3
        )
        if enough_sensory and (stable_regions > 0 or self.sensory_part_count >= 4):
            return "established"
        return "developing"

    @property
    def part_count(self) -> int:
        return len(self._parts) + len(self._regions)

    @property
    def sensory_part_count(self) -> int:
        return len(self._parts)

    @property
    def cognitive_region_count(self) -> int:
        return len(self._regions)

    @property
    def dependency_evidence_count(self) -> int:
        return len(self._dependency_evidence)

    def _enforce_sensory_bound(self) -> None:
        if len(self._parts) <= MAX_SENSORY_PARTS:
            return
        retained = sorted(
            self._parts.values(),
            key=lambda part: (
                -part.last_evidence_tick,
                -part.existence_confidence_class,
                -part.confidence_class,
                part.part_id,
            ),
        )[:MAX_SENSORY_PARTS]
        self._parts = {part.part_id: part for part in retained}

    def _remove_region(self, part_id: str) -> None:
        self._regions.pop(part_id, None)
        self._previous_active_regions.discard(part_id)
        self._dependency_evidence = {
            key: evidence
            for key, evidence in self._dependency_evidence.items()
            if evidence.source_id != part_id and evidence.target_id != part_id
        }

    def _enforce_region_bound(self) -> None:
        if len(self._regions) <= MAX_COGNITIVE_REGIONS:
            return
        retained = sorted(
            self._regions.values(),
            key=lambda region: (
                -region.last_evidence_tick,
                -region.existence_confidence_class,
                -region.confidence_class,
                region.part_id,
            ),
        )[:MAX_COGNITIVE_REGIONS]
        keep = {region.part_id for region in retained}
        for part_id in tuple(self._regions):
            if part_id not in keep:
                self._remove_region(part_id)

    def observe_self_model(self, payload: dict[str, Any], *, tick: int) -> None:
        if tick < 0:
            raise ValueError("tick must be non-negative")
        if not isinstance(payload, dict):
            raise ValueError("self-model evidence must be a JSON object")
        if len(payload) > MAX_SENSORY_PARTS:
            raise ValueError(f"self-model evidence exceeds MAX_SENSORY_PARTS ({MAX_SENSORY_PARTS})")

        for sense_id, entry in sorted(payload.items()):
            if not isinstance(sense_id, str) or not sense_id:
                raise ValueError("self-model sense ids must be non-empty strings")
            if not isinstance(entry, dict):
                raise ValueError(f"self-model entry for {sense_id!r} must be a JSON object")
            health_class = _require_class(entry.get("health_class"), _HEALTH_CLASSES, "health_class")
            confidence_class = _require_class(
                entry.get("confidence_class"), _CONFIDENCE_CLASSES, "confidence_class"
            )
            cost_class = _require_class(entry.get("cost_class"), _COST_CLASSES, "cost_class")
            maturity_class = _require_class(entry.get("maturity_class"), _MATURITY_CLASSES, "maturity_class")
            recency_raw = _require_class(entry.get("recency_class"), len(RecencyClass), "recency_class")
            representative_idle = _RECENCY_REPRESENTATIVE_IDLE_TICKS[RecencyClass(recency_raw)]
            part_id = _sense_part_id(self._id_salt, sense_id)
            self._parts[part_id] = _SensoryPartState(
                part_id=part_id,
                health_class=health_class,
                confidence_class=confidence_class,
                cost_class=cost_class,
                maturity_class=maturity_class,
                last_evidence_tick=max(0, tick - representative_idle),
            )
        self._enforce_sensory_bound()

    def observe_sensory_phenotype(self, payload: dict[str, Any], *, tick: int) -> None:
        """Learn sensory body parts from organism-owned sensors.

        This path is used by the adaptive sensory architecture. It receives
        only the bounded public phenotype, never provider/capability metadata
        or raw readings. Legacy observe_self_model remains available for
        historical identity-mode checkpoints and tests.
        """
        if tick < 0:
            raise ValueError("tick must be non-negative")
        if not isinstance(payload, dict):
            raise ValueError("sensory phenotype must be a JSON object")
        sensors = payload.get("sensors", [])
        if not isinstance(sensors, list) or len(sensors) > MAX_SENSORY_PARTS:
            raise ValueError("sensory phenotype exceeds MAX_SENSORY_PARTS")

        maturity_map = {
            "nascent": 0,
            "immature": 2,
            "established": 4,
            "specialised": 6,
            "degraded": 3,
        }

        def ratio_class(value: Any, count: int, field: str) -> int:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field} must be numeric")
            number = float(value)
            if not 0.0 <= number <= 1.0:
                raise ValueError(f"{field} must be within [0, 1]")
            return max(0, min(count - 1, round(number * (count - 1))))

        seen: set[str] = set()
        for entry in sensors:
            if not isinstance(entry, dict):
                raise ValueError("sensory phenotype sensor entries must be objects")
            sensor_id = entry.get("sensor_id")
            if not isinstance(sensor_id, str) or not sensor_id or sensor_id in seen:
                raise ValueError("sensory phenotype sensor ids must be unique non-empty strings")
            seen.add(sensor_id)
            maturity = entry.get("maturity")
            if maturity not in maturity_map:
                raise ValueError("unknown sensor maturity")
            raw_cost = entry.get("cost", 0.0)
            if isinstance(raw_cost, bool) or not isinstance(raw_cost, (int, float)):
                raise ValueError("sensor cost must be numeric")
            cost_ratio = max(0.0, min(1.0, float(raw_cost)))
            part_id = _sense_part_id(self._id_salt, sensor_id)
            self._parts[part_id] = _SensoryPartState(
                part_id=part_id,
                health_class=ratio_class(entry.get("health", 0.0), _HEALTH_CLASSES, "health"),
                confidence_class=ratio_class(entry.get("confidence", 0.0), _CONFIDENCE_CLASSES, "confidence"),
                cost_class=ratio_class(cost_ratio, _COST_CLASSES, "cost"),
                maturity_class=min(_MATURITY_CLASSES - 1, maturity_map[maturity]),
                last_evidence_tick=tick,
            )
        keep = {_sense_part_id(self._id_salt, sensor_id) for sensor_id in seen}
        self._parts = {part_id: part for part_id, part in self._parts.items() if part_id in keep}
        self._enforce_sensory_bound()

    @staticmethod
    def _decay_support(
        mapping: dict[Any, int],
        observed: set[Any],
    ) -> dict[Any, tuple[int, int]]:
        changed: dict[Any, tuple[int, int]] = {}
        for key in tuple(mapping):
            if key in observed:
                continue
            previous = mapping[key]
            remaining = previous - 1
            changed[key] = (previous, max(0, remaining))
            if remaining <= 0:
                mapping.pop(key, None)
            else:
                mapping[key] = remaining
        return changed

    def _update_channel_support(
        self,
        activity_by_channel: dict[str, int],
    ) -> set[str]:
        """Update bounded sufficient statistics and return affected channels."""
        observed_channels = set(activity_by_channel)
        dirty_channels: set[str] = set()

        channel_decay = self._decay_support(
            self._channel_support,
            observed_channels,
        )
        for channel, (before, after) in channel_decay.items():
            if (
                before >= _REGION_CHANNEL_SUPPORT_MIN
            ) != (
                after >= _REGION_CHANNEL_SUPPORT_MIN
            ):
                dirty_channels.add(str(channel))

        for channel in observed_channels:
            before = self._channel_support.get(channel, 0)
            after = min(_REGION_SUPPORT_CAP, before + 1)
            self._channel_support[channel] = after
            if (
                before >= _REGION_CHANNEL_SUPPORT_MIN
            ) != (
                after >= _REGION_CHANNEL_SUPPORT_MIN
            ):
                dirty_channels.add(channel)

        observed_pairs: set[tuple[str, str]] = set()
        ordered = sorted(observed_channels)
        for index, source in enumerate(ordered):
            for target in ordered[index + 1 :]:
                pair = (source, target)
                observed_pairs.add(pair)
                before = self._coactivity_support.get(pair, 0)
                after = min(_REGION_SUPPORT_CAP, before + 1)
                self._coactivity_support[pair] = after
                if (
                    before >= _REGION_PAIR_SUPPORT_MIN
                ) != (
                    after >= _REGION_PAIR_SUPPORT_MIN
                ):
                    dirty_channels.add(source)
                    dirty_channels.add(target)

        changed_pairs = self._decay_support(
            self._coactivity_support,
            observed_pairs,
        )
        for (source, target), (before, after) in changed_pairs.items():
            if (
                before >= _REGION_PAIR_SUPPORT_MIN
            ) != (
                after >= _REGION_PAIR_SUPPORT_MIN
            ):
                dirty_channels.add(source)
                dirty_channels.add(target)

        if len(self._channel_support) > MAX_COGNITIVE_CHANNEL_CANDIDATES:
            retained = sorted(
                self._channel_support.items(),
                key=lambda item: (-item[1], item[0]),
            )[:MAX_COGNITIVE_CHANNEL_CANDIDATES]
            keep = {channel for channel, _ in retained}
            self._channel_support = dict(retained)
            self._coactivity_support = {
                pair: support
                for pair, support in self._coactivity_support.items()
                if pair[0] in keep and pair[1] in keep
            }
        if len(self._coactivity_support) > MAX_COACTIVITY_CANDIDATES:
            retained_pairs = sorted(
                self._coactivity_support.items(),
                key=lambda item: (-item[1], item[0]),
            )[:MAX_COACTIVITY_CANDIDATES]
            retained_keys = {pair for pair, _ in retained_pairs}
            removed_pairs = set(self._coactivity_support) - retained_keys
            for source, target in removed_pairs:
                if self._coactivity_support[(source, target)] >= _REGION_PAIR_SUPPORT_MIN:
                    dirty_channels.add(source)
                    dirty_channels.add(target)
            self._coactivity_support = dict(retained_pairs)

        return dirty_channels

    def _pair_support(self, source: str, target: str) -> int:
        if source == target:
            return _REGION_SUPPORT_CAP
        pair = (source, target) if source <= target else (target, source)
        return self._coactivity_support.get(pair, 0)

    def _members_are_cohesive(self, members: tuple[str, ...]) -> bool:
        """Require dense direct support without demanding a complete clique."""
        if len(members) <= 1:
            return True
        if len(members) == 2:
            return self._pair_support(members[0], members[1]) >= _REGION_PAIR_SUPPORT_MIN

        neighbor_counts = {member: 0 for member in members}
        strong_pairs = 0
        total_pairs = len(members) * (len(members) - 1) // 2
        for index, source in enumerate(members):
            for target in members[index + 1 :]:
                if self._pair_support(source, target) >= _REGION_PAIR_SUPPORT_MIN:
                    strong_pairs += 1
                    neighbor_counts[source] += 1
                    neighbor_counts[target] += 1

        density = strong_pairs / total_pairs
        required_neighbors = math.ceil(
            _REGION_MEMBER_COVERAGE_MIN * (len(members) - 1)
        )
        return (
            density >= _REGION_PAIR_DENSITY_MIN
            and all(count >= required_neighbors for count in neighbor_counts.values())
        )

    def _cohesive_clusters(self, channels: set[str] | tuple[str, ...]) -> list[tuple[str, ...]]:
        """Deterministic complete-link clustering over opaque cognitive channels.

        A-B and B-C no longer imply A-B-C when A-C lacks evidence. This prevents
        a single bridge channel from collapsing most cognition into one giant
        low-confidence region.
        """
        ordered = sorted(
            set(channels),
            key=lambda channel: (-self._channel_support.get(channel, 0), channel),
        )
        clusters: list[list[str]] = []
        for channel in ordered:
            candidates: list[tuple[int, int, int]] = []
            for index, cluster in enumerate(clusters):
                members = tuple(sorted((*cluster, channel)))
                if not self._members_are_cohesive(members):
                    continue
                supports = [self._pair_support(channel, member) for member in cluster]
                strong_links = sum(
                    support >= _REGION_PAIR_SUPPORT_MIN for support in supports
                )
                candidates.append((strong_links, sum(supports), index))
            if not candidates:
                clusters.append([channel])
                continue
            # Prefer broad support, then total support; stable index breaks ties.
            candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
            clusters[candidates[0][2]].append(channel)

        result = [tuple(sorted(cluster)) for cluster in clusters]
        result.sort(key=lambda cluster: (-len(cluster), cluster))
        return result

    def _eligible_unassigned_components(self) -> list[tuple[str, ...]]:
        assigned = {channel for region in self._regions.values() for channel in region.members}
        eligible = {
            channel
            for channel, support in self._channel_support.items()
            if support >= _REGION_CHANNEL_SUPPORT_MIN and channel not in assigned
        }
        return self._cohesive_clusters(eligible)

    def _split_incohesive_regions(
        self,
        activity_by_channel: dict[str, int],
        *,
        tick: int,
        affected_channels: set[str] | None = None,
    ) -> None:
        """Revise only regions whose cohesion evidence may have changed."""
        for old_part_id, region in tuple(self._regions.items()):
            if (
                affected_channels is not None
                and not affected_channels.intersection(region.members)
            ):
                continue
            if self._members_are_cohesive(region.members):
                continue
            clusters = self._cohesive_clusters(region.members)
            if len(clusters) <= 1:
                continue

            self._remove_region(old_part_id)
            for members in clusters:
                anchor = members[0]
                part_id = _region_part_id(self._id_salt, anchor)
                support_floor = min(
                    (self._channel_support.get(member, 0) for member in members),
                    default=0,
                )
                evidence_count = min(
                    region.evidence_count,
                    max(1, support_floor),
                    _REGION_EVIDENCE_CAP,
                )
                activity = self._region_activity(members, activity_by_channel)
                self._regions[part_id] = _CognitiveRegionState(
                    part_id=part_id,
                    members=members,
                    evidence_count=evidence_count,
                    confidence_class=self._region_confidence(members),
                    activity_class=(
                        activity if activity is not None else region.activity_class
                    ),
                    last_evidence_tick=(
                        tick if activity is not None else region.last_evidence_tick
                    ),
                )
        self._enforce_region_bound()

    def _region_confidence(self, members: tuple[str, ...]) -> int:
        if len(members) == 1:
            support = self._channel_support.get(members[0], 0)
            return _ratio_class(support, _REGION_SUPPORT_CAP)
        pair_support = []
        for index, source in enumerate(members):
            for target in members[index + 1 :]:
                pair_support.append(self._coactivity_support.get((source, target), 0))
        if not pair_support:
            return 0
        average = round(sum(pair_support) / len(pair_support))
        return _ratio_class(average, _REGION_SUPPORT_CAP)

    @staticmethod
    def _region_activity(members: tuple[str, ...], activity_by_channel: dict[str, int]) -> int | None:
        values = [activity_by_channel[channel] for channel in members if channel in activity_by_channel]
        if not values:
            return None
        return max(0, min(_ACTIVITY_CLASSES - 1, round(sum(values) / len(values))))

    def _merge_cohesive_regions(
        self,
        activity_by_channel: dict[str, int],
        *,
        tick: int,
        affected_channels: set[str] | None = None,
    ) -> None:
        """Consolidate only region pairs whose evidence/topology may have changed."""
        while True:
            candidates: list[tuple[int, int, str, str, tuple[str, ...]]] = []
            region_items = sorted(self._regions.items())
            for index, (left_id, left) in enumerate(region_items):
                left_affected = (
                    affected_channels is None
                    or bool(affected_channels.intersection(left.members))
                )
                for right_id, right in region_items[index + 1 :]:
                    if affected_channels is not None and not (
                        left_affected
                        or affected_channels.intersection(right.members)
                    ):
                        continue
                    members = tuple(sorted(set((*left.members, *right.members))))
                    if len(members) > MAX_COGNITIVE_REGION_MEMBERS:
                        continue
                    if not self._members_are_cohesive(members):
                        continue
                    cross_supports = [
                        self._pair_support(source, target)
                        for source in left.members
                        for target in right.members
                    ]
                    strong_links = sum(
                        support >= _REGION_PAIR_SUPPORT_MIN
                        for support in cross_supports
                    )
                    candidates.append(
                        (
                            strong_links,
                            sum(cross_supports),
                            left_id,
                            right_id,
                            members,
                        )
                    )
            if not candidates:
                break

            candidates.sort(
                key=lambda item: (-item[0], -item[1], item[2], item[3])
            )
            _, _, left_id, right_id, members = candidates[0]
            left = self._regions[left_id]
            right = self._regions[right_id]
            evidence_count = min(
                _REGION_EVIDENCE_CAP,
                max(left.evidence_count, right.evidence_count),
            )
            activity = self._region_activity(members, activity_by_channel)
            last_tick = max(left.last_evidence_tick, right.last_evidence_tick)
            if activity is not None:
                last_tick = tick

            self._remove_region(left_id)
            self._remove_region(right_id)
            part_id = _region_part_id(self._id_salt, members[0])
            self._regions[part_id] = _CognitiveRegionState(
                part_id=part_id,
                members=members,
                evidence_count=evidence_count,
                confidence_class=self._region_confidence(members),
                activity_class=(
                    activity
                    if activity is not None
                    else max(left.activity_class, right.activity_class)
                ),
                last_evidence_tick=last_tick,
            )
        self._enforce_region_bound()

    def _expand_existing_regions(self, activity_by_channel: dict[str, int]) -> None:
        assigned = {channel for region in self._regions.values() for channel in region.members}
        candidates = [
            channel
            for channel, support in self._channel_support.items()
            if support >= _REGION_CHANNEL_SUPPORT_MIN and channel not in assigned
        ]
        for channel in sorted(candidates):
            scored: list[tuple[int, int, str]] = []
            for part_id, region in self._regions.items():
                if len(region.members) >= MAX_COGNITIVE_REGION_MEMBERS:
                    continue
                supports = [
                    self._pair_support(channel, member)
                    for member in region.members
                ]
                members = tuple(sorted((*region.members, channel)))
                if supports and self._members_are_cohesive(members):
                    strong_links = sum(
                        support >= _REGION_PAIR_SUPPORT_MIN for support in supports
                    )
                    scored.append((strong_links, sum(supports), part_id))
            if not scored:
                continue
            scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
            part_id = scored[0][2]
            region = self._regions[part_id]
            members = tuple(sorted((*region.members, channel)))
            self._regions[part_id] = _CognitiveRegionState(
                part_id=region.part_id,
                members=members,
                evidence_count=region.evidence_count,
                confidence_class=self._region_confidence(members),
                activity_class=region.activity_class,
                last_evidence_tick=region.last_evidence_tick,
            )
            assigned.add(channel)

    def _create_new_regions(self, activity_by_channel: dict[str, int], *, tick: int) -> None:
        for component in self._eligible_unassigned_components():
            if not any(channel in activity_by_channel for channel in component):
                continue
            for offset in range(0, len(component), MAX_COGNITIVE_REGION_MEMBERS):
                members = component[offset : offset + MAX_COGNITIVE_REGION_MEMBERS]
                anchor = members[0]
                part_id = _region_part_id(self._id_salt, anchor)
                if part_id in self._regions:
                    continue
                activity_class = self._region_activity(members, activity_by_channel)
                self._regions[part_id] = _CognitiveRegionState(
                    part_id=part_id,
                    members=members,
                    evidence_count=min(
                        _REGION_EVIDENCE_CAP,
                        max(self._channel_support.get(channel, 0) for channel in members),
                    ),
                    confidence_class=self._region_confidence(members),
                    activity_class=activity_class if activity_class is not None else 0,
                    last_evidence_tick=tick,
                )
        self._enforce_region_bound()

    def _active_region_ids(self, activity_by_channel: dict[str, int], *, tick: int) -> set[str]:
        active_channels = set(activity_by_channel)
        active_regions: set[str] = set()
        for part_id, region in tuple(self._regions.items()):
            if not active_channels.intersection(region.members):
                continue
            active_regions.add(part_id)
            activity_class = self._region_activity(region.members, activity_by_channel)
            self._regions[part_id] = _CognitiveRegionState(
                part_id=region.part_id,
                members=region.members,
                evidence_count=min(_REGION_EVIDENCE_CAP, region.evidence_count + 1),
                confidence_class=self._region_confidence(region.members),
                activity_class=activity_class if activity_class is not None else region.activity_class,
                last_evidence_tick=tick,
            )
        return active_regions

    def _dependency(self, source_id: str, target_id: str, relation: DependencyKind) -> _DependencyEvidence:
        if relation is DependencyKind.CO_ACTS_WITH and target_id < source_id:
            source_id, target_id = target_id, source_id
        key = (source_id, target_id, relation)
        evidence = self._dependency_evidence.get(key)
        if evidence is None:
            evidence = _DependencyEvidence(source_id=source_id, target_id=target_id, relation=relation)
            self._dependency_evidence[key] = evidence
        return evidence

    @staticmethod
    def _record_dependency_opportunity(
        evidence: _DependencyEvidence,
        *,
        supported: bool,
        tick: int,
    ) -> None:
        # Saturation must not make a learned relation irreversible. Rescale the
        # bounded sufficient statistics before admitting another opportunity,
        # preserving approximately the same ratio while restoring headroom.
        if evidence.opportunity_count >= _DEPENDENCY_COUNTER_CAP:
            evidence.support_count //= 2
            evidence.opportunity_count //= 2
        evidence.opportunity_count += 1
        if supported:
            evidence.support_count = min(_DEPENDENCY_COUNTER_CAP, evidence.support_count + 1)
            evidence.last_support_tick = tick

    def _update_dependencies(self, active_regions: set[str], *, tick: int) -> None:
        region_ids = sorted(self._regions)
        region_id_set = set(region_ids)
        self._dependency_evidence = {
            key: evidence
            for key, evidence in self._dependency_evidence.items()
            if evidence.source_id in region_id_set and evidence.target_id in region_id_set
        }

        for index, source_id in enumerate(region_ids):
            for target_id in region_ids[index + 1 :]:
                if source_id not in active_regions and target_id not in active_regions:
                    continue
                evidence = self._dependency(source_id, target_id, DependencyKind.CO_ACTS_WITH)
                self._record_dependency_opportunity(
                    evidence,
                    supported=source_id in active_regions and target_id in active_regions,
                    tick=tick,
                )

        previous = self._previous_active_regions & region_id_set
        for source_id in sorted(previous):
            for target_id in region_ids:
                if source_id == target_id:
                    continue
                evidence = self._dependency(source_id, target_id, DependencyKind.PRECEDES)
                self._record_dependency_opportunity(
                    evidence,
                    supported=target_id in active_regions,
                    tick=tick,
                )

        if len(self._dependency_evidence) > MAX_DEPENDENCY_EVIDENCE:
            retained = sorted(
                self._dependency_evidence.values(),
                key=lambda evidence: (
                    -evidence.support_count,
                    -evidence.confidence_class,
                    -evidence.last_support_tick,
                    evidence.relation.value,
                    evidence.source_id,
                    evidence.target_id,
                ),
            )[:MAX_DEPENDENCY_EVIDENCE]
            self._dependency_evidence = {
                (e.source_id, e.target_id, e.relation): e for e in retained
            }
        self._previous_active_regions = set(active_regions)

    def observe_cognition(self, payload: dict[str, Any], *, tick: int) -> None:
        """Learn coarse internal regions from opaque dynamic evidence only."""
        if tick < 0:
            raise ValueError("tick must be non-negative")
        if not isinstance(payload, dict) or set(payload) != {"schema_version", "channels"}:
            raise ValueError("cognitive self observation must contain schema_version and channels")
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported cognitive self observation schema_version")
        channels = payload.get("channels")
        if not isinstance(channels, list):
            raise ValueError("cognitive self observation channels must be an array")
        if len(channels) > MAX_COGNITIVE_CHANNELS_PER_TICK:
            raise ValueError("cognitive self observation exceeds per-tick channel bound")

        activity_by_channel: dict[str, int] = {}
        for entry in channels:
            if not isinstance(entry, dict) or set(entry) != {"channel_id", "activity_class"}:
                raise ValueError("cognitive channel entries must contain channel_id and activity_class")
            channel_id = entry.get("channel_id")
            if not isinstance(channel_id, str) or not _valid_channel_id(channel_id):
                raise ValueError("cognitive channel_id must be opaque channel.cognition.<32-hex>")
            if channel_id in activity_by_channel:
                raise ValueError(f"duplicate cognitive channel_id: {channel_id}")
            activity_by_channel[channel_id] = _require_class(
                entry.get("activity_class"), _ACTIVITY_CLASSES, "activity_class"
            )
            if activity_by_channel[channel_id] == 0:
                raise ValueError("cognitive self observation contains only active channels")

        # PRECEDES requires genuinely adjacent trusted observations. A bridge
        # failure, reacclimation interval or alternate result with no activation
        # mapping means observe_cognition() is skipped for that tick. Detect that
        # gap from the previous regions' last trusted evidence and drop only the
        # ephemeral adjacency context; absence of evidence is not negative evidence.
        if self._previous_active_regions and any(
            part_id not in self._regions
            or self._regions[part_id].last_evidence_tick != tick - 1
            for part_id in self._previous_active_regions
        ):
            self._previous_active_regions.clear()

        dirty_channels = self._update_channel_support(activity_by_channel)
        self._pending_structural_channels.update(dirty_channels)

        # Evidence is updated every trusted tick, but structural regrouping is
        # intentionally amortized. Re-running split/merge clustering on every
        # observation is computationally redundant and can dominate the
        # organism clock once dozens of regions exist.
        should_restructure = (
            tick % _REGION_RESTRUCTURE_INTERVAL == 0
            or not self._regions
        )
        has_structural_change = bool(self._pending_structural_channels)
        if should_restructure and (
            self._full_structural_review_required or has_structural_change
        ):
            affected = (
                None
                if self._full_structural_review_required
                else set(self._pending_structural_channels)
            )
            self._split_incohesive_regions(
                activity_by_channel,
                tick=tick,
                affected_channels=affected,
            )
            self._merge_cohesive_regions(
                activity_by_channel,
                tick=tick,
                affected_channels=affected,
            )
            self._expand_existing_regions(activity_by_channel)
            self._create_new_regions(activity_by_channel, tick=tick)
            self._full_structural_review_required = False
            self._pending_structural_channels.clear()

        active_regions = self._active_region_ids(activity_by_channel, tick=tick)
        self._update_dependencies(active_regions, tick=tick)

    def _sensory_public_part(self, part: _SensoryPartState, *, current_tick: int) -> dict[str, Any]:
        idle_ticks = max(0, current_tick - part.last_evidence_tick)
        return {
            "part_id": part.part_id,
            "kind": "sense",
            "existence_confidence_class": part.existence_confidence_class,
            "health_class": part.health_class,
            "confidence_class": part.confidence_class,
            "cost_class": part.cost_class,
            "maturity_class": part.maturity_class,
            "recency_class": _recency_class(idle_ticks).value,
        }

    def _region_public_part(self, region: _CognitiveRegionState, *, current_tick: int) -> dict[str, Any]:
        idle_ticks = max(0, current_tick - region.last_evidence_tick)
        return {
            "part_id": region.part_id,
            "kind": "cognitive_region",
            "existence_confidence_class": region.existence_confidence_class,
            "confidence_class": region.confidence_class,
            "activity_class": region.activity_class,
            "maturity_class": region.maturity_class,
            "recency_class": _recency_class(idle_ticks).value,
        }

    def _export_dependencies(self) -> list[dict[str, Any]]:
        eligible = [evidence for evidence in self._dependency_evidence.values() if evidence.exportable]
        eligible.sort(
            key=lambda evidence: (
                -evidence.confidence_class,
                -evidence.support_class,
                evidence.relation.value,
                evidence.source_id,
                evidence.target_id,
            )
        )
        return [
            {
                "source_id": evidence.source_id,
                "target_id": evidence.target_id,
                "relation": evidence.relation.value,
                "confidence_class": evidence.confidence_class,
                "support_class": evidence.support_class,
            }
            for evidence in eligible[:MAX_BODY_DEPENDENCIES]
        ]

    def export_representation(self, *, current_tick: int) -> dict[str, Any]:
        """Return only organism-owned bounded self-knowledge safe for Observatory."""
        if current_tick < 0:
            raise ValueError("current_tick must be non-negative")
        parts = [
            self._sensory_public_part(part, current_tick=current_tick)
            for part in sorted(self._parts.values(), key=lambda item: item.part_id)
        ]
        parts.extend(
            self._region_public_part(region, current_tick=current_tick)
            for region in sorted(self._regions.values(), key=lambda item: item.part_id)
        )
        return {
            "schema_version": BODY_SCHEMA_VERSION,
            "state": self.state,
            "parts": parts,
            "dependencies": self._export_dependencies(),
            "global_state": {},
        }

    def _export_cognitive_learning(self) -> dict[str, Any]:
        return {
            "channel_support": [
                {"channel_id": channel_id, "support": support}
                for channel_id, support in sorted(self._channel_support.items())
            ],
            "coactivity_support": [
                {"source_channel": source, "target_channel": target, "support": support}
                for (source, target), support in sorted(self._coactivity_support.items())
            ],
            "regions": [
                {
                    "part_id": region.part_id,
                    "members": list(region.members),
                    "evidence_count": region.evidence_count,
                    "confidence_class": region.confidence_class,
                    "activity_class": region.activity_class,
                    "last_evidence_tick": region.last_evidence_tick,
                }
                for region in sorted(self._regions.values(), key=lambda item: item.part_id)
            ],
            "dependency_evidence": [
                {
                    "source_id": evidence.source_id,
                    "target_id": evidence.target_id,
                    "relation": evidence.relation.value,
                    "support_count": evidence.support_count,
                    "opportunity_count": evidence.opportunity_count,
                    "last_support_tick": evidence.last_support_tick,
                }
                for evidence in sorted(
                    self._dependency_evidence.values(),
                    key=lambda item: (item.relation.value, item.source_id, item.target_id),
                )
            ],
        }

    def export(self, *, current_tick: int) -> dict[str, Any]:
        return {
            **self.export_representation(current_tick=current_tick),
            "id_salt": self._id_salt,
            "cognitive_learning": self._export_cognitive_learning(),
        }

    @classmethod
    def _restore_sensory_part(cls, model: "BodySchemaEngine", entry: dict[str, Any], *, current_tick: int) -> None:
        part_id = entry.get("part_id")
        if not isinstance(part_id, str) or not part_id.startswith("part.sense.") or len(part_id) != 43:
            raise ValueError("body_schema sensory part_id must be part.sense.<32-hex>")
        suffix = part_id.removeprefix("part.sense.")
        if not _is_lower_hex(suffix, length=32) or part_id in model._parts:
            raise ValueError("body_schema sensory part_id must be unique lowercase hex")
        if entry.get("kind") != "sense":
            raise ValueError("sensory body_schema part must use kind='sense'")
        health_class = _require_class(entry.get("health_class"), _HEALTH_CLASSES, "health_class")
        confidence_class = _require_class(entry.get("confidence_class"), _CONFIDENCE_CLASSES, "confidence_class")
        cost_class = _require_class(entry.get("cost_class"), _COST_CLASSES, "cost_class")
        maturity_class = _require_class(entry.get("maturity_class"), _MATURITY_CLASSES, "maturity_class")
        existence_class = _require_class(
            entry.get("existence_confidence_class"), _CONFIDENCE_CLASSES, "existence_confidence_class"
        )
        if existence_class != _existence_confidence_class(maturity_class):
            raise ValueError("body_schema existence_confidence_class contradicts maturity_class")
        recency_raw = _require_class(entry.get("recency_class"), len(RecencyClass), "recency_class")
        representative_idle = _RECENCY_REPRESENTATIVE_IDLE_TICKS[RecencyClass(recency_raw)]
        model._parts[part_id] = _SensoryPartState(
            part_id=part_id,
            health_class=health_class,
            confidence_class=confidence_class,
            cost_class=cost_class,
            maturity_class=maturity_class,
            last_evidence_tick=max(0, current_tick - representative_idle),
        )

    @classmethod
    def _restore_cognitive_learning(
        cls,
        model: "BodySchemaEngine",
        payload: Any,
        *,
        public_regions: dict[str, dict[str, Any]],
        public_dependencies: list[dict[str, Any]],
        current_tick: int,
    ) -> None:
        if not isinstance(payload, dict):
            raise ValueError("body_schema cognitive_learning must be an object")
        allowed_keys = {
            "channel_support",
            "coactivity_support",
            "regions",
            "dependency_evidence",
        }
        if set(payload) != allowed_keys:
            raise ValueError("body_schema cognitive_learning contains unexpected fields")

        raw_channel_support = payload["channel_support"]
        if not isinstance(raw_channel_support, list) or len(raw_channel_support) > MAX_COGNITIVE_CHANNEL_CANDIDATES:
            raise ValueError("body_schema channel_support is invalid or unbounded")
        for entry in raw_channel_support:
            if not isinstance(entry, dict) or set(entry) != {"channel_id", "support"}:
                raise ValueError("body_schema channel_support entry is invalid")
            channel_id = entry.get("channel_id")
            support = entry.get("support")
            if not isinstance(channel_id, str) or not _valid_channel_id(channel_id) or channel_id in model._channel_support:
                raise ValueError("body_schema channel_support channel_id is invalid")
            model._channel_support[channel_id] = _require_class(support, _REGION_SUPPORT_CAP + 1, "support")

        raw_coactivity = payload["coactivity_support"]
        if not isinstance(raw_coactivity, list) or len(raw_coactivity) > MAX_COACTIVITY_CANDIDATES:
            raise ValueError("body_schema coactivity_support is invalid or unbounded")
        for entry in raw_coactivity:
            if not isinstance(entry, dict) or set(entry) != {"source_channel", "target_channel", "support"}:
                raise ValueError("body_schema coactivity_support entry is invalid")
            source = entry.get("source_channel")
            target = entry.get("target_channel")
            if not isinstance(source, str) or not isinstance(target, str) or not _valid_channel_id(source) or not _valid_channel_id(target):
                raise ValueError("body_schema coactivity channel ids are invalid")
            if source >= target:
                raise ValueError("body_schema coactivity endpoints must be canonical and distinct")
            key = (source, target)
            if key in model._coactivity_support:
                raise ValueError("duplicate body_schema coactivity entry")
            model._coactivity_support[key] = _require_class(entry.get("support"), _REGION_SUPPORT_CAP + 1, "support")

        raw_regions = payload["regions"]
        if not isinstance(raw_regions, list) or len(raw_regions) > MAX_COGNITIVE_REGIONS:
            raise ValueError("body_schema cognitive regions are invalid or unbounded")
        for entry in raw_regions:
            if not isinstance(entry, dict) or set(entry) != {
                "part_id",
                "members",
                "evidence_count",
                "confidence_class",
                "activity_class",
                "last_evidence_tick",
            }:
                raise ValueError("body_schema cognitive region checkpoint entry is invalid")
            part_id = entry.get("part_id")
            if not isinstance(part_id, str) or not part_id.startswith("part.region.") or len(part_id) != 44:
                raise ValueError("body_schema cognitive region id must be part.region.<32-hex>")
            suffix = part_id.removeprefix("part.region.")
            if not _is_lower_hex(suffix, length=32) or part_id in model._regions:
                raise ValueError("body_schema cognitive region id must be unique lowercase hex")
            members = entry.get("members")
            if not isinstance(members, list) or not 1 <= len(members) <= MAX_COGNITIVE_REGION_MEMBERS:
                raise ValueError("body_schema cognitive region members are invalid")
            member_tuple = tuple(str(member) for member in members)
            if tuple(sorted(set(member_tuple))) != member_tuple or not all(_valid_channel_id(member) for member in member_tuple):
                raise ValueError("body_schema cognitive region members must be unique sorted opaque channels")
            evidence_count = entry.get("evidence_count")
            if isinstance(evidence_count, bool) or not isinstance(evidence_count, int) or not 1 <= evidence_count <= _REGION_EVIDENCE_CAP:
                raise ValueError("body_schema cognitive region evidence_count is invalid")
            confidence_class = _require_class(entry.get("confidence_class"), _CONFIDENCE_CLASSES, "confidence_class")
            activity_class = _require_class(entry.get("activity_class"), _ACTIVITY_CLASSES, "activity_class")
            last_tick = entry.get("last_evidence_tick")
            if isinstance(last_tick, bool) or not isinstance(last_tick, int) or not 0 <= last_tick <= current_tick:
                raise ValueError("body_schema cognitive region last_evidence_tick is invalid")
            model._regions[part_id] = _CognitiveRegionState(
                part_id=part_id,
                members=member_tuple,
                evidence_count=evidence_count,
                confidence_class=confidence_class,
                activity_class=activity_class,
                last_evidence_tick=last_tick,
            )

        if set(public_regions) != set(model._regions):
            raise ValueError("body_schema public cognitive regions contradict private learning state")
        for part_id, region in model._regions.items():
            if model._region_public_part(region, current_tick=current_tick) != public_regions[part_id]:
                raise ValueError("body_schema public cognitive region contradicts private learning state")

        raw_dependencies = payload["dependency_evidence"]
        if not isinstance(raw_dependencies, list) or len(raw_dependencies) > MAX_DEPENDENCY_EVIDENCE:
            raise ValueError("body_schema dependency evidence is invalid or unbounded")
        for entry in raw_dependencies:
            if not isinstance(entry, dict) or set(entry) != {
                "source_id",
                "target_id",
                "relation",
                "support_count",
                "opportunity_count",
                "last_support_tick",
            }:
                raise ValueError("body_schema dependency evidence entry is invalid")
            source = entry.get("source_id")
            target = entry.get("target_id")
            if source not in model._regions or target not in model._regions or source == target:
                raise ValueError("body_schema dependency evidence endpoints are invalid")
            try:
                relation = DependencyKind(entry.get("relation"))
            except (TypeError, ValueError) as exc:
                raise ValueError("body_schema dependency relation is invalid") from exc
            if relation is DependencyKind.CO_ACTS_WITH and target < source:
                raise ValueError("co_acts_with dependency endpoints must be canonical")
            support_count = entry.get("support_count")
            opportunity_count = entry.get("opportunity_count")
            last_support_tick = entry.get("last_support_tick")
            for value, field in (
                (support_count, "support_count"),
                (opportunity_count, "opportunity_count"),
                (last_support_tick, "last_support_tick"),
            ):
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"body_schema dependency {field} is invalid")
            if support_count > opportunity_count or support_count > _DEPENDENCY_COUNTER_CAP or opportunity_count > _DEPENDENCY_COUNTER_CAP:
                raise ValueError("body_schema dependency counters are contradictory or unbounded")
            if last_support_tick > current_tick:
                raise ValueError("body_schema dependency last_support_tick is in the future")
            evidence = _DependencyEvidence(
                source_id=source,
                target_id=target,
                relation=relation,
                support_count=support_count,
                opportunity_count=opportunity_count,
                last_support_tick=last_support_tick,
            )
            key = (source, target, relation)
            if key in model._dependency_evidence:
                raise ValueError("duplicate body_schema dependency evidence")
            model._dependency_evidence[key] = evidence

        if model._export_dependencies() != public_dependencies:
            raise ValueError("body_schema public dependencies contradict private learning state")
        # Previous-active state deliberately resets at restore. A restart is
        # not evidence that an old region temporally precedes a new one.
        model._previous_active_regions = set()

    @classmethod
    def restore(cls, payload: dict[str, Any] | None, *, current_tick: int) -> "BodySchemaEngine":
        if payload is None:
            return cls()
        if not isinstance(payload, dict):
            raise ValueError("body_schema payload must be a JSON object")
        version = payload.get("schema_version")
        if version not in (LEGACY_BODY_SCHEMA_VERSION, BODY_SCHEMA_VERSION):
            raise ValueError(f"unsupported body_schema schema_version: {version!r}")
        id_salt = payload.get("id_salt")
        if not isinstance(id_salt, str) or not _is_lower_hex(id_salt, length=32):
            raise ValueError("body_schema checkpoint is missing a valid private id_salt")
        model = cls(id_salt=id_salt)
        state = payload.get("state")
        if state not in ("undeveloped", "partial"):
            raise ValueError("body_schema state must be 'undeveloped' or 'partial'")
        raw_parts = payload.get("parts")
        if not isinstance(raw_parts, list):
            raise ValueError("body_schema parts must be an array")
        max_parts = MAX_SENSORY_PARTS if version == LEGACY_BODY_SCHEMA_VERSION else MAX_BODY_PARTS
        if len(raw_parts) > max_parts:
            raise ValueError(f"body_schema parts exceeds bound ({max_parts})")
        if payload.get("global_state") != {}:
            raise ValueError("body_schema global_state must remain empty before physiology integration")

        public_regions: dict[str, dict[str, Any]] = {}
        for entry in raw_parts:
            if not isinstance(entry, dict):
                raise ValueError("body_schema part entries must be JSON objects")
            kind = entry.get("kind")
            if kind == "sense":
                cls._restore_sensory_part(model, entry, current_tick=current_tick)
            elif version == BODY_SCHEMA_VERSION and kind == "cognitive_region":
                part_id = entry.get("part_id")
                if not isinstance(part_id, str) or part_id in public_regions:
                    raise ValueError("duplicate or invalid public cognitive region")
                public_regions[part_id] = dict(entry)
            else:
                raise ValueError("body_schema contains unsupported part kind")

        raw_dependencies = payload.get("dependencies")
        if not isinstance(raw_dependencies, list):
            raise ValueError("body_schema dependencies must be an array")
        if version == LEGACY_BODY_SCHEMA_VERSION:
            if raw_dependencies:
                raise ValueError("legacy body_schema must not contain dependencies")
            if payload.get("cognitive_learning") is not None:
                raise ValueError("legacy body_schema must not contain cognitive_learning")
        else:
            if len(raw_dependencies) > MAX_BODY_DEPENDENCIES:
                raise ValueError("body_schema dependencies exceed bound")
            cls._restore_cognitive_learning(
                model,
                payload.get("cognitive_learning"),
                public_regions=public_regions,
                public_dependencies=raw_dependencies,
                current_tick=current_tick,
            )

        if state == "undeveloped" and model.part_count:
            raise ValueError("undeveloped body_schema cannot contain parts")
        if state == "partial" and not model.part_count:
            raise ValueError("partial body_schema must contain at least one part")
        return model


__all__ = [
    "BODY_SCHEMA_VERSION",
    "LEGACY_BODY_SCHEMA_VERSION",
    "MAX_BODY_PARTS",
    "MAX_BODY_DEPENDENCIES",
    "MAX_COGNITIVE_REGIONS",
    "MAX_COGNITIVE_REGION_MEMBERS",
    "MAX_SENSORY_PARTS",
    "DependencyKind",
    "BodySchemaEngine",
]

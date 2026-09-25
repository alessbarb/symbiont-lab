"""Bounded, endogenous knowledge about opaque signal behaviour."""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
import math
from collections import deque
from typing import Any, Iterable

from .identity import claim_id
from .knowledge_types import SignalObservationBatch
from .prediction import PredictionTrial, RidgePredictor

from ..foundation.limits import OrganismLimits

_DEFAULT_LIMITS = OrganismLimits()
MAX_PROFILES = _DEFAULT_LIMITS.max_knowledge_profiles
MAX_CLAIMS = _DEFAULT_LIMITS.max_knowledge_claims
MAX_CLAIMS_PER_SIGNAL = _DEFAULT_LIMITS.max_knowledge_claims_per_signal
MAX_PENDING_TRIALS = _DEFAULT_LIMITS.max_pending_trials
MAX_HORIZON, MAX_PAIR_CANDIDATES = 1, 64
MAX_KNOWLEDGE_CHECKPOINT_BYTES = _DEFAULT_LIMITS.max_knowledge_checkpoint_bytes
MIN_VALIDATION_TRIALS = 144
EPOCH_TICKS, MIN_EPOCH_TRIALS = 64, 48
_KINDS = {"stability", "change", "synchronous_association", "lead_prediction", "self_relevance"}
_STATUSES = {"insufficient", "hypothesis", "supported", "contested", "stale"}


def _loss_class(value: float) -> str:
    if not math.isfinite(value) or value < 0:
        return "unknown"
    if value == 0: return "zero"
    if value < 0.01: return "trace"
    if value < 0.1: return "low"
    if value < 0.5: return "medium"
    if value < 2.0: return "high"
    return "extreme"


@dataclass(frozen=True, slots=True)
class EvidenceWindow:
    """Closed, non-overlapping evidence accounting (no raw samples)."""

    start_tick: int
    end_tick: int
    comparable_trials: int = 0
    successful_trials: int = 0
    failed_trials: int = 0
    censored_trials: int = 0

    def __post_init__(self) -> None:
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (self.start_tick, self.end_tick)):
            raise ValueError("evidence ticks must be integers")
        if self.start_tick < 0 or self.end_tick < self.start_tick:
            raise ValueError("invalid evidence window")
        if min(self.comparable_trials, self.successful_trials, self.failed_trials, self.censored_trials) < 0:
            raise ValueError("invalid evidence counters")
        if self.successful_trials + self.failed_trials > self.comparable_trials:
            raise ValueError("inconsistent evidence counters")


@dataclass(slots=True)
class Claim:
    claim_id: str
    subject_id: str
    kind: str
    object_id: str | None = None
    horizon: int | None = None
    direction: str = "unspecified"
    status: str = "insufficient"
    strength_class: str | None = None
    evidence_count: int = 0
    validation_opportunities: int = 0
    improvement_class: str | None = None
    baseline_loss_class: str | None = None
    candidate_loss_class: str | None = None
    reference_loss_classes: dict[str, str] = field(default_factory=dict)
    successful_epochs: int = 0
    failed_epochs: int = 0
    revision: int = 0
    reason_class: str = "insufficient_observations"
    last_tested_tick: int | None = None

    def public(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "kind": self.kind,
            "related_signal_id": self.object_id,
            "horizon": self.horizon,
            "direction": self.direction,
            "status": self.status,
            "strength_class": self.strength_class,
            "evidence_count": self.evidence_count,
            "validation_opportunities": self.validation_opportunities,
            "improvement_class": self.improvement_class,
            "baseline_loss_class": self.baseline_loss_class,
            "candidate_loss_class": self.candidate_loss_class,
            "reference_loss_classes": dict(self.reference_loss_classes),
            "successful_epochs": self.successful_epochs,
            "failed_epochs": self.failed_epochs,
            "revision": self.revision,
            "reason_class": self.reason_class,
        }


@dataclass(slots=True)
class SignalProfile:
    signal_id: str
    observed_opportunities: int = 0
    valid_observations: int = 0
    last_observed_tick: int | None = None
    claims: list[Claim] | None = None

    def __post_init__(self) -> None:
        if self.claims is None:
            self.claims = []

    def public(self, tick: int | None = None) -> dict[str, Any]:
        age = "never" if self.last_observed_tick is None or tick is None else (
            "current" if tick - self.last_observed_tick == 0 else "recent" if tick - self.last_observed_tick < 64 else "aging" if tick - self.last_observed_tick < 192 else "long_absent"
        )
        return {"signal_id": self.signal_id, "observed_opportunities": self.observed_opportunities,
                "valid_observations": self.valid_observations, "last_seen_age_class": age,
                "claims": [c.public() for c in self.claims]}


@dataclass(frozen=True, slots=True)
class KnowledgeEvent:
    claim_id: str | None
    tick: int
    from_status: str | None
    to_status: str | None
    reason_class: str


class SignalKnowledgeEngine:
    def __init__(self, *, max_profiles: int = MAX_PROFILES, max_claims: int = MAX_CLAIMS) -> None:
        if not (1 <= max_profiles <= MAX_PROFILES):
            raise ValueError("max_profiles out of bounds")
        if not (1 <= max_claims <= MAX_CLAIMS):
            raise ValueError("max_claims out of bounds")
        self.max_profiles, self.max_claims = max_profiles, max_claims
        self._profiles: dict[str, SignalProfile] = {}
        self._history: dict[str, deque[tuple[int, float]]] = {}
        self._pair_history: dict[tuple[str, str], deque[tuple[int, float, float]]] = {}
        self._pair_predictors: dict[tuple[str, str], RidgePredictor] = {}
        self._pending_features: dict[tuple[str, str], tuple[int, tuple[float, ...]]] = {}
        self._epoch_stats: dict[str, list[int]] = {}
        self._candidate_pairs: set[tuple[str, str]] = set()
        self._events: deque[KnowledgeEvent] = deque(maxlen=64)
        self._last_tick: int | None = None
        self._event_overflowed = False

    def _emit(self, event: KnowledgeEvent) -> None:
        if len(self._events) < self._events.maxlen:
            self._events.append(event)
        elif not self._event_overflowed:
            self._events.popleft()
            self._events.append(KnowledgeEvent(None, event.tick, None, None, "event_overflow"))
            self._event_overflowed = True

    def _profile(self, signal_id: str) -> SignalProfile | None:
        if signal_id in self._profiles:
            return self._profiles[signal_id]
        if len(self._profiles) >= self.max_profiles:
            # Profiles are a cache, not a permanent manifest allocation.
            # Evict the least recently observed/least useful entry and all of
            # its dependent pair state before admitting new evidence.
            victim = min(self._profiles.values(), key=lambda p: (p.last_observed_tick is not None, p.last_observed_tick or -1, p.signal_id))
            self._drop_profile(victim.signal_id)
        p = SignalProfile(signal_id); self._profiles[signal_id] = p; self._history[signal_id] = deque(maxlen=64); return p

    def _drop_profile(self, signal_id: str) -> None:
        self._profiles.pop(signal_id, None)
        self._history.pop(signal_id, None)
        for pair in tuple(self._pair_history):
            if signal_id in pair:
                self._pair_history.pop(pair, None)
                self._pair_predictors.pop(pair, None)
                self._pending_features.pop(pair, None)
        self._candidate_pairs = {pair for pair in self._candidate_pairs if signal_id not in pair}

    def _claim(self, subject: str, kind: str, tick: int, *, object_id: str | None = None, horizon: int | None = None, direction: str = "unspecified") -> Claim | None:
        p = self._profiles[subject]
        existing = next((c for c in p.claims if c.kind == kind and c.object_id == object_id and c.horizon == horizon), None)
        if existing: return existing
        if len(p.claims) >= MAX_CLAIMS_PER_SIGNAL or sum(len(x.claims) for x in self._profiles.values()) >= self.max_claims:
            if not self._evict_claim(tick, subject, same_profile=len(p.claims) >= MAX_CLAIMS_PER_SIGNAL):
                self._emit(KnowledgeEvent(None, tick, None, None, "budget_rejected"))
                return None
        c = Claim(claim_id(subject, kind, object_id, horizon), subject, kind, object_id, horizon, direction)
        p.claims.append(c); return c

    def _evict_claim(self, tick: int, preferred_subject: str, *, same_profile: bool = False) -> bool:
        candidates = [c for p in self._profiles.values() for c in p.claims
                      if c.status in {"insufficient", "stale", "hypothesis"}]
        if same_profile:
            candidates = [c for c in candidates if c.subject_id == preferred_subject]
        if not candidates:
            return False
        rank = {"insufficient": 0, "stale": 1, "hypothesis": 2}
        victim = min(candidates, key=lambda c: (rank[c.status], c.last_tested_tick if c.last_tested_tick is not None else -1, c.claim_id))
        self._profiles[victim.subject_id].claims.remove(victim)
        self._emit(KnowledgeEvent(victim.claim_id, tick, victim.status, None, "evicted"))
        return True

    def _transition(self, c: Claim, status: str, tick: int, reason: str) -> None:
        if c.status == status: return
        if c.revision >= 2**31 - 1:
            self._emit(KnowledgeEvent(c.claim_id, tick, c.status, c.status, "revision_limit"))
            return
        old = c.status; c.status, c.reason_class, c.revision, c.last_tested_tick = status, reason, c.revision + 1, tick
        self._emit(KnowledgeEvent(c.claim_id, tick, old, status, reason))

    def observe(self, batch: SignalObservationBatch, *, candidate_pairs: Iterable[tuple[str, str]] = (), outcomes: Iterable[Any] = ()) -> None:
        if self._last_tick is not None and batch.tick <= self._last_tick: raise ValueError("ticks must increase strictly")
        outcomes = tuple(outcomes)
        for outcome in outcomes:
            if (not isinstance(outcome, tuple) or len(outcome) != 2
                    or not isinstance(outcome[0], str) or not isinstance(outcome[1], bool)):
                raise ValueError("outcomes must be (opaque signal id, boolean) tuples")
        self._last_tick = batch.tick
        for obs in batch.observations:
            # Non-selected valid manifest entries are not evidence and must
            # not consume the bounded learning cache. Keep selected/invalid
            # observations visible for diagnostics without treating them as
            # usable history.
            if obs.valid and not obs.selected:
                continue
            p = self._profile(obs.signal_id)
            if p is None: continue
            p.observed_opportunities += int(obs.selected)
            if obs.valid:
                p.valid_observations += 1; p.last_observed_tick = batch.tick; self._history[obs.signal_id].append((batch.tick, float(obs.value)))
                c = self._claim(obs.signal_id, "stability", batch.tick)
                if c and p.valid_observations >= 32:
                    c.evidence_count = p.valid_observations; c.validation_opportunities = p.valid_observations; c.strength_class = "moderate"; c.reason_class = "initial_evidence"
                    self._transition(c, "hypothesis", batch.tick, "initial_evidence")
        values = {o.signal_id: float(o.value) for o in batch.observations if o.valid}
        # Change claims are deliberately descriptive: they require a mature
        # stream and report only a discrete strength, never a raw delta.
        for sid, value in values.items():
            history = self._history.get(sid)
            if history is None:
                continue
            if len(history) >= 8:
                recent = [v for _, v in list(history)[-8:]]
                spread = max(recent) - min(recent)
                c = self._claim(sid, "change", batch.tick)
                if c is not None:
                    c.validation_opportunities += 1
                    if spread > 0:
                        c.evidence_count += 1
                    if c.validation_opportunities >= MIN_EPOCH_TRIALS:
                        c.strength_class = "moderate" if c.evidence_count >= 4 else "weak"
                        c.reason_class = "initial_evidence"
                        self._transition(c, "hypothesis", batch.tick, c.reason_class)
        for a, b in list(candidate_pairs)[:MAX_PAIR_CANDIDATES]:
            if a not in self._profiles or a == b: continue
            c = self._claim(a, "lead_prediction", batch.tick, object_id=b, horizon=1, direction="same")
            if c is None: continue
            pair = self._pair_history.setdefault((a, b), deque(maxlen=64))
            predictor = self._pair_predictors.setdefault((a, b), RidgePredictor())
            # Score a prediction issued on the prior tick before learning from
            # the current target. Missing or gapped targets are censored.
            if b in values and pair and pair[-1][0] == batch.tick - 1:
                _, predicted, baseline = pair[-1]
                target = values[b]
                candidate_loss = abs(predicted - target)
                baseline_loss = abs(baseline - target)
                c.validation_opportunities += 1
                c.baseline_loss_class = _loss_class(baseline_loss)
                c.candidate_loss_class = _loss_class(candidate_loss)
                target_history = [v for _, v in list(self._history[b])[:-1]][-64:]
                mean_baseline = sum(target_history) / len(target_history) if target_history else baseline
                references = {"zero": 0.0, "mean": mean_baseline, "persistence": baseline,
                              "conditional": baseline}
                c.reference_loss_classes = {name: _loss_class(abs(pred - target)) for name, pred in references.items()}
                # A trial is favorable only when it clears every available
                # reference by both the relative and absolute margins fixed
                # in the design; no retrospective reference selection.
                favorable = all(
                    candidate_loss <= abs(pred - target) * 0.85
                    and abs(pred - target) - candidate_loss >= 0.01
                    for pred in references.values()
                )
                c.evidence_count += int(favorable)
                stats = self._epoch_stats.setdefault(c.claim_id, [0, 0])
                stats[0] += 1
                # Epoch promotion counts only trials that beat *all* fixed
                # references, not merely persistence. This keeps a noisy
                # candidate from accumulating wins against one weak baseline.
                stats[1] += int(favorable)
                pending = self._pending_features.pop((a, b), None)
                if pending is not None and pending[0] == batch.tick - 1:
                    try:
                        predictor.observe(pending[1], target - self._history[b][-2][1])
                    except (ValueError, OverflowError):
                        pass
            if a in values and b in values:
                previous_b = self._history.get(b)
                # The prediction issued now is evaluated against b(t+1); its
                # persistence reference is the latest observed b(t), not b(t-1).
                baseline = values[b]
                previous_a = self._history.get(a)
                # The first bounded candidate is intentionally simple and
                # deterministic: extrapolate the source's latest delta onto
                # the target, while retaining persistence as the conditional
                # baseline.  It is emitted before the next target exists.
                delta_a = values[a] - previous_a[-2][1] if previous_a and len(previous_a) >= 2 else 0.0
                delta_b = values[b] - baseline
                previous_delta_b = (previous_b[-2][1] - previous_b[-3][1]) if previous_b and len(previous_b) >= 3 else 0.0
                features = (delta_b, previous_delta_b, delta_a)
                learned_delta = predictor.predict(features)
                predicted = values[b] + (learned_delta if learned_delta is not None else delta_a)
                self._pending_features[(a, b)] = (batch.tick, features)
                pair.append((batch.tick, predicted, baseline))
                sync = self._claim(a, "synchronous_association", batch.tick, object_id=b, direction="same")
                if sync is not None:
                    sync.validation_opportunities += 1
                    if len(self._history[a]) >= 2 and len(self._history[b]) >= 2:
                        sync.evidence_count += int((values[a] - self._history[a][-2][1]) * (values[b] - self._history[b][-2][1]) >= 0)
                    if sync.validation_opportunities >= MIN_EPOCH_TRIALS:
                        sync.strength_class = "moderate" if sync.evidence_count * 2 >= sync.validation_opportunities else "weak"
                        sync.reason_class = "initial_evidence"
                        self._transition(sync, "hypothesis", batch.tick, sync.reason_class)
            self._candidate_pairs.add((a, b))
            if len(self._candidate_pairs) > MAX_PAIR_CANDIDATES:
                keep = set(sorted(self._candidate_pairs)[:MAX_PAIR_CANDIDATES])
                for pair in self._candidate_pairs - keep:
                    self._pair_history.pop(pair, None)
                    self._pair_predictors.pop(pair, None)
                    self._pending_features.pop(pair, None)
                self._candidate_pairs = keep
        # A mature claim with no recent observations is explicitly stale; this
        # is not equivalent to a negative result.
        for profile in self._profiles.values():
            if profile.last_observed_tick is None or batch.tick - profile.last_observed_tick < 192:
                continue
            for claim in profile.claims:
                if claim.status in {"supported", "hypothesis"}:
                    self._transition(claim, "stale", batch.tick, "no_recent_trials")
        # Endogenous outcome hooks accept only opaque signal IDs and a boolean
        # outcome.  No host labels or predictor loss are admitted here.
        for outcome in outcomes:
            sid, favorable = outcome
            if sid not in self._profiles:
                continue
            claim = self._claim(sid, "self_relevance", batch.tick)
            if claim is None:
                continue
            claim.validation_opportunities += 1
            claim.evidence_count += int(favorable)
            stats = self._epoch_stats.setdefault(claim.claim_id, [0, 0])
            stats[0] += 1
            stats[1] += int(favorable)
            if claim.validation_opportunities >= MIN_EPOCH_TRIALS:
                claim.strength_class = "moderate" if claim.evidence_count * 2 >= claim.validation_opportunities else "weak"
                claim.reason_class = "initial_evidence"
                self._transition(claim, "hypothesis", batch.tick, claim.reason_class)

        # Close fixed, non-overlapping 64-tick epochs.  Partial epochs never
        # promote a claim and are intentionally retained only as warm-up RAM.
        if batch.tick % EPOCH_TICKS == 0:
            for profile in self._profiles.values():
                for claim in profile.claims:
                    if claim.kind not in {"lead_prediction", "self_relevance"}:
                        continue
                    trials, wins = self._epoch_stats.pop(claim.claim_id, [0, 0])
                    if trials < MIN_EPOCH_TRIALS:
                        continue
                    favorable = wins / trials >= 0.6
                    # Recent failure has priority over historical success.
                    # A supported claim must lose support as soon as its
                    # current evidence window repeatedly fails.
                    if not favorable:
                        claim.failed_epochs += 1
                        claim.improvement_class = "none"
                        claim.reason_class = "no_incremental_advantage"
                    else:
                        claim.successful_epochs += 1
                        claim.improvement_class = "material"
                        claim.strength_class = "moderate"
                        claim.reason_class = "prospective_advantage"
                    if claim.failed_epochs >= 2:
                        self._transition(claim, "contested", batch.tick, claim.reason_class)
                    elif claim.successful_epochs >= 3 and claim.validation_opportunities >= MIN_VALIDATION_TRIALS:
                        self._transition(claim, "supported", batch.tick, claim.reason_class)
                    else:
                        self._transition(claim, "hypothesis", batch.tick, "initial_evidence")

    def view(self) -> tuple[dict[str, Any], ...]:
        return tuple(p.public(self._last_tick) for p in sorted(self._profiles.values(), key=lambda x: x.signal_id))

    def drain_events(self) -> tuple[dict[str, Any], ...]:
        events = tuple(asdict(e) for e in self._events); self._events.clear(); return events

    def checkpoint(self) -> dict[str, Any]:
        profiles = []
        for p in self._profiles.values():
            item = dict(p.public(self._last_tick), last_observed_tick=p.last_observed_tick)
            item["claims"] = [dict(c.public(), last_tested_tick=c.last_tested_tick) for c in p.claims]
            profiles.append(item)
        return {
            "schema_version": 1,
            "last_tick": self._last_tick,
            "profiles": profiles,
            "history": {key: list(values) for key, values in self._history.items()},
            "pair_history": {
                "|".join(pair): [list(row) for row in values]
                for pair, values in self._pair_history.items()
            },
            "pair_predictors": {
                "|".join(pair): predictor.checkpoint()
                for pair, predictor in self._pair_predictors.items()
            },
            "pending_features": {
                "|".join(pair): [tick, list(features)]
                for pair, (tick, features) in self._pending_features.items()
            },
            "epoch_stats": {key: list(values) for key, values in self._epoch_stats.items()},
            "candidate_pairs": [list(pair) for pair in sorted(self._candidate_pairs)],
            "events": [asdict(event) for event in self._events],
            "event_overflowed": self._event_overflowed,
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any], *, max_profiles: int = MAX_PROFILES, max_claims: int = MAX_CLAIMS) -> "SignalKnowledgeEngine":
        if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("profiles"), list): raise ValueError("invalid signal knowledge checkpoint")
        engine = cls(max_profiles=max_profiles, max_claims=max_claims)
        last_tick = payload.get("last_tick")
        if last_tick is not None and (isinstance(last_tick, bool) or not isinstance(last_tick, int) or last_tick < 0):
            raise ValueError("invalid last_tick")
        engine._last_tick = last_tick
        seen_profiles: set[str] = set()
        for raw in payload["profiles"]:
            if not isinstance(raw, dict) or set(raw) - {"signal_id", "observed_opportunities", "valid_observations", "last_seen_age_class", "last_observed_tick", "claims"}: raise ValueError("invalid profile")
            sid = raw.get("signal_id")
            if not isinstance(sid, str) or not sid.startswith("signal.") or len(sid) != 71:
                raise ValueError("invalid signal id")
            if sid in seen_profiles:
                raise ValueError("duplicate signal id")
            seen_profiles.add(sid)
            p = engine._profile(sid)
            if p is None: raise ValueError("profile limit exceeded")
            opportunities, valid = raw.get("observed_opportunities"), raw.get("valid_observations")
            if any(isinstance(v, bool) or not isinstance(v, int) for v in (opportunities, valid)):
                raise ValueError("invalid profile counters")
            p.observed_opportunities, p.valid_observations = opportunities, valid
            if p.observed_opportunities < 0 or p.valid_observations < 0 or p.valid_observations > p.observed_opportunities:
                raise ValueError("invalid profile counters")
            last_seen = raw.get("last_observed_tick")
            if last_seen is not None and (isinstance(last_seen, bool) or not isinstance(last_seen, int) or last_seen < 0):
                raise ValueError("invalid last_observed_tick")
            if last_seen is not None and last_tick is not None and last_seen > last_tick:
                raise ValueError("last_observed_tick exceeds last_tick")
            p.last_observed_tick = last_seen
            for item in raw.get("claims", []):
                if not isinstance(item, dict): raise ValueError("invalid claim")
                allowed_claim_keys = {"claim_id", "kind", "object_id", "related_signal_id", "horizon", "direction", "status", "strength_class", "evidence_count", "validation_opportunities", "improvement_class", "baseline_loss_class", "candidate_loss_class", "reference_loss_classes", "successful_epochs", "failed_epochs", "revision", "reason_class", "last_tested_tick"}
                if set(item) - allowed_claim_keys: raise ValueError("unknown claim fields")
                related = item.get("related_signal_id", item.get("object_id"))
                if related is not None and (not isinstance(related, str) or not related.startswith("signal.") or len(related) != 71):
                    raise ValueError("invalid related signal id")
                c = engine._claim(p.signal_id, item["kind"], 0, object_id=related, horizon=item.get("horizon"), direction=item.get("direction", "unspecified"))
                if c is None: raise ValueError("claim limit exceeded")
                if item.get("claim_id") != c.claim_id: raise ValueError("claim id mismatch")
                for key in ("status", "strength_class", "evidence_count", "validation_opportunities", "improvement_class", "baseline_loss_class", "candidate_loss_class", "reference_loss_classes", "successful_epochs", "failed_epochs", "revision", "reason_class"):
                    if key in item: setattr(c, key, item[key])
                if not isinstance(c.reference_loss_classes, dict) or any(
                    not isinstance(k, str) or not isinstance(v, str) for k, v in c.reference_loss_classes.items()
                ):
                    raise ValueError("invalid reference loss classes")
                tested = item.get("last_tested_tick")
                if tested is not None and (isinstance(tested, bool) or not isinstance(tested, int) or tested < 0):
                    raise ValueError("invalid last_tested_tick")
                c.last_tested_tick = tested
                if c.status not in _STATUSES or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (c.evidence_count, c.validation_opportunities, c.successful_epochs, c.failed_epochs, c.revision)) or c.evidence_count > c.validation_opportunities:
                    raise ValueError("invalid claim state")
        raw_history = payload.get("history", {})
        if not isinstance(raw_history, dict):
            raise ValueError("invalid signal history")
        for signal_id, values in raw_history.items():
            if signal_id not in engine._profiles or not isinstance(values, list):
                raise ValueError("invalid signal history entry")
            engine._history[signal_id].extend(
                (int(tick), float(value)) for tick, value in values
            )
        raw_pairs = payload.get("pair_history", {})
        if not isinstance(raw_pairs, dict):
            raise ValueError("invalid pair history")
        for key, values in raw_pairs.items():
            pair = tuple(key.split("|"))
            if len(pair) != 2 or not isinstance(values, list):
                raise ValueError("invalid pair history entry")
            engine._pair_history[pair] = deque(
                (int(tick), float(a), float(b)) for tick, a, b in values
            )
        raw_predictors = payload.get("pair_predictors", {})
        if not isinstance(raw_predictors, dict):
            raise ValueError("invalid pair predictors")
        for key, value in raw_predictors.items():
            pair = tuple(key.split("|"))
            if len(pair) != 2 or not isinstance(value, dict):
                raise ValueError("invalid pair predictor entry")
            engine._pair_predictors[pair] = RidgePredictor.from_checkpoint(value)
        raw_pending = payload.get("pending_features", {})
        if not isinstance(raw_pending, dict):
            raise ValueError("invalid pending features")
        for key, value in raw_pending.items():
            pair = tuple(key.split("|"))
            if len(pair) != 2 or not isinstance(value, list) or len(value) != 2:
                raise ValueError("invalid pending feature entry")
            engine._pending_features[pair] = (int(value[0]), tuple(float(x) for x in value[1]))
        raw_epochs = payload.get("epoch_stats", {})
        if not isinstance(raw_epochs, dict):
            raise ValueError("invalid epoch stats")
        engine._epoch_stats = {str(key): [int(value) for value in values] for key, values in raw_epochs.items()}
        raw_candidates = payload.get("candidate_pairs", [])
        if not isinstance(raw_candidates, list):
            raise ValueError("invalid candidate pairs")
        engine._candidate_pairs = {tuple(str(value) for value in pair) for pair in raw_candidates}
        raw_events = payload.get("events", [])
        if not isinstance(raw_events, list):
            raise ValueError("invalid knowledge events")
        engine._events.extend(KnowledgeEvent(**event) for event in raw_events)
        engine._event_overflowed = bool(payload.get("event_overflowed", False))
        return engine


__all__ = [
    "SignalKnowledgeEngine", "SignalProfile", "Claim", "EvidenceWindow",
    "PredictionTrial", "KnowledgeEvent", "MAX_PROFILES", "MAX_CLAIMS",
    "MAX_CLAIMS_PER_SIGNAL", "MAX_PENDING_TRIALS", "MAX_HORIZON",
    "MAX_PAIR_CANDIDATES", "MAX_KNOWLEDGE_CHECKPOINT_BYTES",
    "MIN_VALIDATION_TRIALS", "EPOCH_TICKS", "MIN_EPOCH_TRIALS",
]

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...host.acclimation import CapabilityBaseline, HostAcclimation, RunningStats
from ...host.consolidated_baseline import ConsolidatedBaselineSeed, seed_capability_baseline
from .capsule import KnowledgeCapsule, verify_capsule


def _remote_mean(remote_stats: dict[str, Any]) -> float:
    """A remote capsule's acclimation entry uses the same consolidated
    shape as a local checkpoint (center_class/scale_class/maturity_class);
    the legacy exact {mean,...} shape is still accepted from an
    older-schema peer, the same dual-path discipline host/checkpoint.py
    uses."""
    if "center_class" in remote_stats:
        seed = ConsolidatedBaselineSeed(
            center_class=int(remote_stats["center_class"]),
            scale_class=int(remote_stats["scale_class"]),
            maturity_class=int(remote_stats["maturity_class"]),
        )
        return seed_capability_baseline(seed).mean
    return float(remote_stats["mean"])


@dataclass(slots=True, frozen=True)
class _TrustKey:
    signer_public_key: bytes
    pattern_family: str


@dataclass(slots=True, frozen=True)
class TrustSnapshot:
    """Purely descriptive reliability statistics for one (source, pattern
    family) pair — count/mean/variance of an agreement signal, the same
    discipline as :class:`~symbiont.host.acclimation.CapabilityBaseline`.
    Never a trust/distrust verdict: this is a running average of how often
    a source's claims have agreed with this organism's own local beliefs,
    nothing more (``docs/adr/ADR-0003-attention-is-not-classification.md``
    applies here too)."""

    count: int
    mean: float
    variance: float


def agreement_score(local: CapabilityBaseline | None, remote_mean: float) -> float | None:
    """How closely a remote-claimed mean matches this organism's own local
    baseline for the same capability, as a smooth score in ``(0, 1]`` — 1.0
    at a perfect match, asymptotically approaching 0 as the claim diverges.

    Returns ``None`` when there is no local basis to compare against (no
    local baseline yet, or a degenerate zero-stdev one) — silence, not a
    manufactured score, matches the discipline used throughout this system
    for "not enough information yet" (roadmap v0.43).
    """
    if local is None or local.stdev == 0.0:
        return None
    z = abs((remote_mean - local.mean) / local.stdev)
    return 1.0 / (1.0 + z)


class SourceTrustModel:
    """Learn a per (capsule signer, pattern family) reliability score from
    repeated agreement between a capsule's claims and this organism's own
    local beliefs (roadmap v0.43).

    Deliberately local and per-source: this only ever answers "how
    reliable has this specific source been for this specific pattern
    family, according to my own observations" — it never aggregates across
    multiple sources or treats agreement-by-many as truth. That composition
    (without treating a majority as truth) is v0.44's job, kept
    structurally separate here so it cannot be silently reintroduced by
    accident.

    Bounded: tracks at most ``max_contexts`` distinct (source, pattern
    family) pairs; anything beyond that is silently dropped rather than
    growing state without bound, the same discipline as v0.35's
    ``RhythmModel``.
    """

    def __init__(self, *, max_contexts: int = 256, min_samples: int = 1) -> None:
        if max_contexts < 1:
            raise ValueError("max_contexts must be at least 1")
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        self._max_contexts = max_contexts
        self._min_samples = min_samples
        self._stats: dict[_TrustKey, RunningStats] = {}

    def observe(self, *, source: bytes, pattern_family: str, agreement: float) -> None:
        if not 0.0 <= agreement <= 1.0:
            raise ValueError("agreement must be between 0.0 and 1.0")
        key = _TrustKey(source, pattern_family)
        stats = self._stats.get(key)
        if stats is None:
            if len(self._stats) >= self._max_contexts:
                return
            stats = RunningStats()
            self._stats[key] = stats
        stats.update(agreement)

    def is_learned(self, source: bytes, pattern_family: str) -> bool:
        stats = self._stats.get(_TrustKey(source, pattern_family))
        return stats is not None and stats.count >= self._min_samples

    def reliability(self, source: bytes, pattern_family: str) -> TrustSnapshot | None:
        stats = self._stats.get(_TrustKey(source, pattern_family))
        if stats is None or stats.count < self._min_samples:
            return None
        snapshot = stats.snapshot()
        return TrustSnapshot(count=snapshot.count, mean=snapshot.mean, variance=snapshot.variance)

    @property
    def known_sources(self) -> tuple[bytes, ...]:
        return tuple(sorted({key.signer_public_key for key in self._stats}))

    def export_checkpoint(self) -> dict[str, Any]:
        return {
            "max_contexts": self._max_contexts,
            "min_samples": self._min_samples,
            "stats": [
                {
                    "source": key.signer_public_key.hex(),
                    "pattern_family": key.pattern_family,
                    "count": stats.count,
                    "mean": stats.mean,
                    "variance": stats.snapshot().variance,
                }
                for key, stats in self._stats.items()
            ],
        }

    @classmethod
    def from_checkpoint(cls, data: dict[str, Any]) -> "SourceTrustModel":
        model = cls(
            max_contexts=int(data.get("max_contexts", 256)),
            min_samples=int(data.get("min_samples", 1)),
        )
        for entry in data.get("stats", []):
            key = _TrustKey(bytes.fromhex(entry["source"]), entry["pattern_family"])
            count = int(entry["count"])
            variance = float(entry["variance"])
            stats = RunningStats(
                count=count,
                mean=float(entry["mean"]),
                _m2=variance * (count - 1) if count > 1 else 0.0,
            )
            model._stats[key] = stats
        return model


def observe_capsule_trust(
    model: SourceTrustModel,
    *,
    acclimation: HostAcclimation,
    capsule: KnowledgeCapsule,
) -> dict[str, float]:
    """Verify ``capsule`` and, for every capability it and this organism's
    own acclimation both know about, score agreement and feed it into
    ``model`` (roadmap v0.43).

    Verification happens here, not just at the caller: a capsule's claims
    are never trusted into the model without this function itself checking
    the signature, regardless of what the caller already did. Returns the
    per-capability agreement scores actually computed (capabilities with no
    local baseline yet, or absent from the capsule, are simply omitted).
    """
    if not verify_capsule(capsule):
        raise ValueError("capsule failed signature verification")

    remote_acclimation: dict[str, Any] = capsule.payload.get("acclimation", {})
    scores: dict[str, float] = {}
    for capability_id, remote_stats in remote_acclimation.items():
        local_baseline = acclimation.baseline(capability_id)
        score = agreement_score(local_baseline, _remote_mean(remote_stats))
        if score is None:
            continue
        model.observe(source=capsule.signer_public_key, pattern_family=capability_id, agreement=score)
        scores[capability_id] = score
    return scores

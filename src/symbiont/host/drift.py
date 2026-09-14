from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite, sqrt


class DriftKind(StrEnum):
    """A purely statistical category of how a value relates to an aging
    baseline — never a threat, security or classification judgment, the
    same discipline v0.33's ``HostAcclimation`` and v0.35's ``RhythmModel``
    already hold to.
    """

    NONE = "none"
    ISOLATED = "isolated"
    GRADUAL = "gradual"
    REGIME_SHIFT = "regime_shift"


@dataclass(slots=True, frozen=True)
class DriftObservation:
    kind: DriftKind
    z_score: float | None


class DriftAwareBaseline:
    """An aging baseline that separates isolated anomaly from a confirmed
    regime shift, and ages out stale history once a shift is confirmed
    (roadmap v0.36).

    Unlike v0.33's :class:`~symbiont.host.acclimation.HostAcclimation` (a
    single cumulative mean that never forgets), the baseline here re-centers
    on a *confirmed* regime shift rather than drifting continuously — see
    below for why continuous drift was tried and rejected.

    Classification of each new value, before it updates the baseline:

    - ``ISOLATED`` — a single reading far enough from baseline (``z >=
      isolated_z``) to stand out, without (yet) being part of a sustained
      run in the same direction. Also returned for a run still shorter than
      ``regime_run`` (an unconfirmed candidate shift).
    - ``GRADUAL`` — a moderate deviation (``z >= regime_z`` but below
      ``isolated_z``) that has not yet persisted long enough to confirm.
    - ``REGIME_SHIFT`` — a moderate-or-larger deviation in the same
      direction sustained for ``regime_run`` consecutive observations. On
      confirmation the baseline mean/variance are recomputed from just the
      buffered run (not blended with pre-shift history), and the streak
      resets so the *next* run starts clean against the new level.
    - ``NONE`` — within the ordinary range of the baseline, or not enough
      history yet to classify anything.

    Known limitation: this detects a *sustained step* (``regime_run``
    consecutive large deviations), not slow creep — a value drifting one
    small increment per tick never crosses ``regime_z`` on any single
    observation, so it is classified ``NONE`` throughout and never reaches
    ``GRADUAL``/``REGIME_SHIFT``. Catching true gradual creep needs a
    separate mechanism (e.g. a fast-EWMA vs slow-EWMA divergence check) that
    is out of scope for this release; ``GRADUAL`` here only means "an
    in-progress candidate step, not yet confirmed."

    Design note — why the baseline does not continuously EWMA-track every
    value: an earlier version updated the mean at full decay rate on every
    observation, including during an active deviation streak. That has two
    failure modes, both found empirically: (1) if variance is *not* frozen
    during the streak, a genuine shift inflates its own noise floor within
    1-2 ticks, and every later reading in the same shift reads as "normal"
    against that already-corrupted floor, so ``REGIME_SHIFT`` never
    accumulates enough streak to fire; (2) if variance *is* frozen but the
    mean keeps moving every tick, the mean partway-drifts toward an isolated
    spike, so reverting to the pre-spike value afterwards reads as a large
    deviation in the *opposite* direction from the now-shifted mean, and a
    few reverts in a row falsely confirm a ``REGIME_SHIFT`` back to the
    original level. Buffering the deviating run and only committing it to
    the baseline on confirmation (discarding it if the streak breaks first)
    avoids both: an isolated spike or a broken streak never touches the
    baseline at all.
    """

    def __init__(
        self,
        *,
        decay: float = 0.1,
        isolated_z: float = 3.0,
        regime_z: float = 2.0,
        regime_run: int = 3,
        min_samples: int = 5,
    ) -> None:
        if not 0.0 < decay <= 1.0:
            raise ValueError("decay must be between 0 (exclusive) and 1 (inclusive)")
        if isolated_z <= 0.0:
            raise ValueError("isolated_z must be positive")
        if regime_z <= 0.0:
            raise ValueError("regime_z must be positive")
        if isolated_z < regime_z:
            raise ValueError("isolated_z must be at least regime_z")
        if regime_run < 1:
            raise ValueError("regime_run must be at least 1")
        if min_samples < 1:
            raise ValueError("min_samples must be at least 1")

        self._decay = decay
        self._isolated_z = isolated_z
        self._regime_z = regime_z
        self._regime_run = regime_run
        self._min_samples = min_samples

        self._count = 0
        self._mean = 0.0
        self._variance = 0.0
        self._deviation_streak = 0
        self._streak_direction = 0
        self._buffer: list[float] = []

    @property
    def is_established(self) -> bool:
        return self._count >= self._min_samples

    @property
    def count(self) -> int:
        return self._count

    @property
    def mean(self) -> float:
        return self._mean

    @property
    def variance(self) -> float:
        return self._variance

    @property
    def stdev(self) -> float:
        return sqrt(self._variance)

    def restore(self, *, count: int, mean: float, variance: float) -> None:
        """Restore a previously-exported committed baseline (roadmap v0.37
        checkpoints).

        Restores only the committed descriptive baseline — never the
        pending confirmation buffer, which holds raw recent values and is
        therefore not "safe abstract state". A checkpoint always resumes
        with a clean slate for any in-progress candidate shift.

        Validated (roadmap safety finding A07): a checkpoint is untrusted
        external input, and a corrupt count/mean/variance must fail here,
        loudly, rather than silently corrupting this baseline and crashing
        confusingly the next time it is observed or its ``stdev`` is read.
        """
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("count must be an int")
        if count < 0:
            raise ValueError("count must be non-negative")
        if not isfinite(mean):
            raise ValueError("mean must be finite")
        if not isfinite(variance) or variance < 0.0:
            raise ValueError("variance must be finite and non-negative")
        self._count = count
        self._mean = mean
        self._variance = variance
        self._deviation_streak = 0
        self._streak_direction = 0
        self._buffer = []

    def observe(self, value: float) -> DriftObservation:
        if not self.is_established:
            kind = DriftKind.NONE
            z_score = None
            self._apply_direct(value)
            self._count += 1
            return DriftObservation(kind=kind, z_score=z_score)

        z_score = self._z_score(value, self._mean, self.stdev)
        magnitude = abs(z_score)
        large_deviation = magnitude >= self._regime_z
        direction = 1 if z_score > 0 else -1 if z_score < 0 else 0

        if large_deviation and direction == self._streak_direction and self._deviation_streak > 0:
            self._deviation_streak += 1
            self._buffer.append(value)
        elif large_deviation:
            self._deviation_streak = 1
            self._streak_direction = direction
            self._buffer = [value]
        else:
            self._deviation_streak = 0
            self._streak_direction = 0
            self._buffer = []

        if large_deviation and self._deviation_streak >= self._regime_run:
            # Confirmed: the baseline re-centers on just the buffered run,
            # not blended with pre-shift history, so the next observation is
            # judged against the new level rather than a stale one.
            self._recompute_from_buffer()
            kind = DriftKind.REGIME_SHIFT
            self._deviation_streak = 0
            self._streak_direction = 0
            self._buffer = []
        else:
            if not large_deviation:
                self._apply_direct(value)
            # else: value is buffered pending confirmation — the committed
            # baseline is left untouched so a broken streak (isolated spike,
            # or a revert back to normal) never contaminates it.
            if magnitude >= self._isolated_z:
                kind = DriftKind.ISOLATED
            elif large_deviation:
                kind = DriftKind.GRADUAL
            else:
                kind = DriftKind.NONE

        self._count += 1
        return DriftObservation(kind=kind, z_score=z_score)

    @staticmethod
    def _z_score(value: float, mean: float, stdev: float) -> float:
        if stdev == 0.0:
            if value == mean:
                return 0.0
            return float("inf") if value > mean else float("-inf")
        return (value - mean) / stdev

    def _apply_direct(self, value: float) -> None:
        if self._count == 0:
            self._mean = value
            self._variance = 0.0
            return
        delta = value - self._mean
        self._mean += self._decay * delta
        self._variance = (1.0 - self._decay) * (self._variance + self._decay * delta * delta)

    def _recompute_from_buffer(self) -> None:
        n = len(self._buffer)
        mean = sum(self._buffer) / n
        variance = sum((x - mean) ** 2 for x in self._buffer) / n if n > 1 else 0.0
        self._mean = mean
        self._variance = variance

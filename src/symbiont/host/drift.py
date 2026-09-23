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
    CREEP = "creep"
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

    Slow creep — a value drifting a small increment per tick, never
    crossing ``regime_z`` on any single observation — is detected
    separately (roadmap v0.54) by a free-running fast EWMA (``fast_decay``,
    faster than ``decay``) whose sustained divergence from the committed
    mean confirms ``DriftKind.CREEP`` after ``creep_run`` consecutive
    ticks past ``creep_z``. Creep only classifies when the step-detector
    above found ``NONE`` this tick — a value already large enough to be
    ``ISOLATED``/``GRADUAL``/``REGIME_SHIFT`` is not also reported as
    creeping. Unlike a regime shift's hard recompute-from-buffer, creep
    re-centers gently (``mean = fast_mean``) and never freezes variance.

    The divergence is normalized against a *frozen* noise floor
    (``_creep_stdev``, snapshotted at establishment and re-snapshotted on
    every ``REGIME_SHIFT``/``CREEP`` confirmation) rather than the live,
    continuously-updated ``stdev``. Using the live stdev was tried first and
    rejected empirically: since ``_apply_direct`` keeps updating variance
    from the same lagging-behind-the-ramp delta that creep is trying to
    detect, the live stdev inflates in lockstep with the creep divergence
    itself, and their ratio converges to a fixed sub-threshold ceiling no
    matter how much true drift accumulates — the same self-corrupting
    feedback loop the design note below already had to solve for regime
    detection, reappearing in a different form for creep.

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
        fast_decay: float = 0.3,
        creep_z: float = 1.0,
        creep_run: int = 8,
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
        if not 0.0 < fast_decay <= 1.0:
            raise ValueError("fast_decay must be between 0 (exclusive) and 1 (inclusive)")
        if fast_decay <= decay:
            raise ValueError("fast_decay must be faster (greater) than decay")
        if creep_z <= 0.0:
            raise ValueError("creep_z must be positive")
        if creep_run < 1:
            raise ValueError("creep_run must be at least 1")

        self._decay = decay
        self._isolated_z = isolated_z
        self._regime_z = regime_z
        self._regime_run = regime_run
        self._min_samples = min_samples
        self._fast_decay = fast_decay
        self._creep_z = creep_z
        self._creep_run = creep_run

        self._count = 0
        self._mean = 0.0
        self._variance = 0.0
        self._deviation_streak = 0
        self._streak_direction = 0
        self._buffer: list[float] = []
        self._fast_mean = 0.0
        self._creep_streak = 0
        self._creep_direction = 0
        self._creep_stdev = 0.0

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
        self._fast_mean = mean
        self._creep_streak = 0
        self._creep_direction = 0
        self._creep_stdev = sqrt(variance)

    def observe(self, value: float) -> DriftObservation:
        if not self.is_established:
            kind = DriftKind.NONE
            z_score = None
            self._apply_direct(value)
            self._fast_mean = value
            self._count += 1
            if self.is_established:
                # NOTE: Just became established this tick: snapshot today's noise
                # floor once, before any creep has had a chance to inflate
                # the live variance — see the creep-detection note below for
                # why this must not be the continuously-updated self.stdev.
                self._creep_stdev = self.stdev
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
            self._fast_mean = self._mean
            self._creep_streak = 0
            self._creep_direction = 0
            self._creep_stdev = self.stdev
        else:
            if not large_deviation:
                self._apply_direct(value)
            # else: value is buffered pending confirmation — the committed
            # baseline is left untouched so a broken streak (isolated spike,
            # or a revert back to normal) never contaminates it.
            self._fast_mean += self._fast_decay * (value - self._fast_mean)

            if magnitude >= self._isolated_z:
                kind = DriftKind.ISOLATED
                self._creep_streak = 0
                self._creep_direction = 0
            elif large_deviation:
                kind = DriftKind.GRADUAL
                self._creep_streak = 0
                self._creep_direction = 0
            else:
                # NOTE(creep-detection): Normalized against the *frozen* noise floor captured at
                # establishment/last confirmation, never the live self.stdev
                # — the live variance is itself being dragged by the same
                # creep this is trying to detect (the exact self-corrupting
                # feedback loop this class's own docstring already flags
                # for regime-shift; a continuously-updated denominator would
                # make the ratio converge to a fixed sub-threshold ceiling
                # regardless of how much true drift has accumulated).
                creep_z_score = self._z_score(self._fast_mean, self._mean, self._creep_stdev)
                creep_direction = 1 if creep_z_score > 0 else -1 if creep_z_score < 0 else 0
                creeping = abs(creep_z_score) >= self._creep_z
                if creeping and creep_direction == self._creep_direction and self._creep_streak > 0:
                    self._creep_streak += 1
                elif creeping:
                    self._creep_streak = 1
                    self._creep_direction = creep_direction
                else:
                    self._creep_streak = 0
                    self._creep_direction = 0

                if creeping and self._creep_streak >= self._creep_run:
                    self._mean = self._fast_mean
                    kind = DriftKind.CREEP
                    self._creep_streak = 0
                    self._creep_direction = 0
                    self._creep_stdev = self.stdev
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

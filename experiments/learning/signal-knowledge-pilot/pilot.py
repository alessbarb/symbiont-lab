"""Design pilot, not the organism engine. No host access or third-party packages.

Run with Python 3.11+: python experiments/learning/signal-knowledge-pilot/pilot.py
Synthetic truth and environment labels stay in this evaluator only.
"""

from __future__ import annotations

import json
import math
import random
from collections import deque

CONFIG = dict(
    ticks=1152,
    training_window=64,
    epoch_ticks=64,
    minimum_comparable=48,
    improvement=0.15,
    absolute_gain=0.01,
    consecutive_epochs=3,
    seeds=[17, 29, 43],
)


def fit(rows, feature):
    """Ridge least squares with an intercept, fit exclusively on past rows."""
    n = len(feature)
    matrix = [
        [sum(r[i] * r[j] for r, _ in rows) + (1e-6 if i == j else 0) for j in range(n)]
        + [sum(r[i] * y for r, y in rows)]
        for i in range(n)
    ]
    for col in range(n):
        pivot = max(range(col, n), key=lambda i: abs(matrix[i][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        scale = matrix[col][col]
        if abs(scale) < 1e-12:
            return 0.0
        matrix[col] = [v / scale for v in matrix[col]]
        for row in range(n):
            if row != col:
                scale = matrix[row][col]
                matrix[row] = [v - scale * w for v, w in zip(matrix[row], matrix[col])]
    return sum(matrix[i][-1] * feature[i] for i in range(n))


def series(kind, seed, count):
    rng = random.Random(seed)
    a = b = previous_a = 0.0
    for tick in range(count):
        noise_a, noise_b = rng.gauss(0, 1), rng.gauss(0, 1)
        if kind == "constant":
            a, b = 4.0, 9.0
        elif kind in ("positive_ar", "negative_ar"):
            rho = 0.85 if kind == "positive_ar" else -0.85
            a, b = rho * a + noise_a, rho * b + noise_b
        elif kind in ("lead", "gaps", "regime", "scaled_lead"):
            b = previous_a + 0.15 * noise_b if kind != "regime" or tick < count // 2 else noise_b
            a = noise_a
        elif kind == "common":
            a = noise_a
            b = a
        elif kind == "trend":
            a, b = tick * 0.1 + noise_a, tick * 0.2 + noise_b
        else:
            a, b = noise_a, noise_b
        previous_a = a
        if kind == "scaled_lead":
            yield 1000 + a * 20, -500 + b * 0.03
        elif kind == "gaps" and rng.random() < 0.1:
            yield None, None
        else:
            yield a, b


def evaluate(values):
    history = deque(maxlen=64)
    own = deque(maxlen=64)
    candidate = deque(maxlen=64)
    levels = deque(maxlen=64)
    pending = None
    losses = [0.0] * 5
    comparable = streak = epochs_won = trials = censored = 0
    supported = False
    promotions = []
    reversals = []
    failures = 0
    epoch_results = []
    for tick, (a, b) in enumerate(values):
        # Score before adding this tick's target to any training set.
        if pending is not None:
            predictions, scale, own_features, features, old_b = pending
            if a is None or b is None:
                censored += 1
            else:
                if predictions is not None:
                    for i, prediction in enumerate(predictions):
                        residual = min(4.0, abs((b - prediction) / scale))
                        losses[i] += residual * residual
                    comparable += 1
                    trials += 1
                own.append((own_features, b - old_b))
                candidate.append((features, b - old_b))
        pending = None
        if a is None or b is None:
            history.clear()
        else:
            history.append((a, b))
            levels.append(b)
            if len(history) >= 3:
                x0, y0 = history[-1]
                x1, y1 = history[-2]
                _, y2 = history[-3]
                own_features = [1.0, y0 - y1, y1 - y2]
                features = own_features + [x0 - x1]
                if len(own) < 32:
                    # Warm-up targets arrive next tick; never invent labels.
                    pending = (None, 1.0, own_features, features, y0)
                else:
                    mean = sum(levels) / len(levels)
                    scale = max(
                        1e-12, math.sqrt(sum((y - mean) ** 2 for y in levels) / len(levels))
                    )
                    predictions = [
                        y0 + fit(candidate, features),
                        0.0,
                        mean,
                        y0,
                        y0 + fit(own, own_features),
                    ]
                    pending = (predictions, scale, own_features, features, y0)
        if (tick + 1) % CONFIG["epoch_ticks"] == 0:
            win = comparable >= CONFIG["minimum_comparable"] and all(
                loss - losses[0]
                >= max(CONFIG["absolute_gain"] * comparable, CONFIG["improvement"] * loss)
                for loss in losses[1:]
            )
            epoch_results.append(
                dict(
                    tick=tick,
                    comparable=comparable,
                    win=win,
                    losses=[round(x / max(1, comparable), 6) for x in losses],
                )
            )
            streak = streak + 1 if win else 0
            epochs_won += int(win)
            failures = failures + 1 if comparable >= CONFIG["minimum_comparable"] and not win else 0
            if streak >= CONFIG["consecutive_epochs"] and not supported:
                supported = True
                promotions.append(tick)
            if failures >= 2 and supported:
                supported = False
                reversals.append(tick)
            losses, comparable = [0.0] * 5, 0
    return dict(
        trials=trials,
        censored=censored,
        epochs_won=epochs_won,
        promotions=promotions,
        reversals=reversals,
        final_supported=supported,
        epochs=epoch_results,
    )


def main():
    outcomes = []
    for environment in (
        "constant",
        "noise",
        "positive_ar",
        "negative_ar",
        "lead",
        "common",
        "trend",
        "gaps",
        "regime",
        "scaled_lead",
    ):
        for seed in CONFIG["seeds"]:
            outcomes.append(
                dict(
                    environment=environment,
                    seed=seed,
                    **evaluate(series(environment, seed, CONFIG["ticks"])),
                )
            )
    for seed in CONFIG["seeds"]:
        for pair in range(32):
            outcomes.append(
                dict(
                    environment="multiple_noise",
                    seed=seed,
                    pair=pair,
                    **evaluate(series("noise", seed * 1000 + pair, CONFIG["ticks"])),
                )
            )
    print(json.dumps(dict(config=CONFIG, outcomes=outcomes), indent=2))


if __name__ == "__main__":
    main()

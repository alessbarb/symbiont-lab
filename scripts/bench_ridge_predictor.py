#!/usr/bin/env python3
"""Focused benchmark for P9 RidgePredictor row-product precomputation."""

from __future__ import annotations

import argparse
import math
import random
import time

from symbiont.core.signals.prediction import RidgePredictor


def legacy_predict(rows, regularization, features):
    if not rows or len(features) != len(rows[0][0]):
        return None
    x = [1.0, *(float(v) for v in features)]
    if any(not math.isfinite(v) for v in x):
        return None
    width = len(x)
    matrix = [[0.0] * (width + 1) for _ in range(width)]
    for row, target in rows:
        z = [1.0, *row]
        for i in range(width):
            for j in range(width):
                matrix[i][j] += z[i] * z[j]
            matrix[i][-1] += z[i] * target
    for i in range(1, width):
        matrix[i][i] += regularization
    for col in range(width):
        pivot = max(range(col, width), key=lambda r: abs(matrix[r][col]))
        if abs(matrix[pivot][col]) < 1e-12:
            return None
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        divisor = matrix[col][col]
        matrix[col] = [v / divisor for v in matrix[col]]
        for r in range(width):
            if r == col:
                continue
            factor = matrix[r][col]
            matrix[r] = [a - factor * b for a, b in zip(matrix[r], matrix[col])]
    value = sum(matrix[i][-1] * x[i] for i in range(width))
    return value if math.isfinite(value) else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", type=int, default=64)
    parser.add_argument("--queries", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=127)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    predictor = RidgePredictor(history_limit=args.history)
    rows = []
    for _ in range(args.history):
        features = tuple(rng.uniform(-3.0, 3.0) for _ in range(3))
        target = rng.uniform(-2.0, 2.0)
        predictor.observe(features, target)
        rows.append((features, target))

    queries = [tuple(rng.uniform(-4.0, 4.0) for _ in range(3)) for _ in range(args.queries)]

    for query in queries[:100]:
        if predictor.predict(query) != legacy_predict(rows, predictor.regularization, query):
            raise RuntimeError("optimized RidgePredictor diverged from legacy output")

    started = time.perf_counter()
    for query in queries:
        legacy_predict(rows, predictor.regularization, query)
    legacy_s = time.perf_counter() - started

    started = time.perf_counter()
    for query in queries:
        predictor.predict(query)
    optimized_s = time.perf_counter() - started

    print(
        {
            "history": args.history,
            "queries": args.queries,
            "legacy_seconds": round(legacy_s, 6),
            "optimized_seconds": round(optimized_s, 6),
            "speedup": round(legacy_s / optimized_s, 3) if optimized_s else None,
            "equivalent": True,
        }
    )


if __name__ == "__main__":
    main()

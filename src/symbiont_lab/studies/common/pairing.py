from __future__ import annotations

from typing import Sequence


def assert_unique_seeds(seeds: Sequence[int], label: str = "seeds") -> None:
    seen = set()
    for s in seeds:
        if s in seen:
            raise ValueError(f"Duplicate seed found in {label}: {s}")
        seen.add(s)


def assert_disjoint_seeds(seeds_a: Sequence[int], seeds_b: Sequence[int], label_a: str = "set A", label_b: str = "set B") -> None:
    intersection = set(seeds_a).intersection(set(seeds_b))
    if intersection:
        raise ValueError(f"Colliding seeds between {label_a} and {label_b}: {sorted(intersection)}")


def assert_paired_seeds(treatment_seeds: Sequence[int], control_seeds: Sequence[int]) -> None:
    if list(treatment_seeds) != list(control_seeds):
        raise ValueError(
            f"Seed pairing mismatch: treatment seeds {list(treatment_seeds)} != control seeds {list(control_seeds)}"
        )

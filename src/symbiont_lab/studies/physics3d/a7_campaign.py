"""Pure planning primitives for the approved Physics3D A7 protocol.

This module enumerates work only. It deliberately has no run/launch operation;
campaign execution remains unauthorized until the protocol is frozen and
external scientific review is complete.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import permutations, product

CANONICAL_BODIES = (
    "anthropomorphic-v6",
    "anthropomorphic-v6-vision",
    "crawler-v1",
    "asymmetric-v1",
)
SEEDS = (42, 43, 44)
REPEATS = (1, 2)


@dataclass(frozen=True, slots=True)
class A7Run:
    """One body/condition/arm/seed/repeat combination."""

    body: str
    condition: str
    arm: str
    seed: int
    repeat: int
    source_body: str | None = None
    destination_body: str | None = None

    @property
    def key(self) -> str:
        parts = (self.body, self.condition, self.arm, f"seed-{self.seed}", f"repeat-{self.repeat}")
        return "/".join(parts)


def planned_arms() -> tuple[dict[str, str | None], ...]:
    """Return all 52 distinct protocol arms (before seed/repeat expansion)."""
    arms: list[dict[str, str | None]] = []
    for body, condition in product(
        CANONICAL_BODIES, ("idle", "actuation", "collision", "checkpoint-restore")
    ):
        arms.append({"body": body, "condition": condition, "arm": "nominal",
                     "source_body": None, "destination_body": None})
    for source, destination in permutations(CANONICAL_BODIES, 2):
        arms.append({"body": source, "condition": "re-embodiment", "arm": f"{source}-to-{destination}",
                     "source_body": source, "destination_body": destination})
    for body, condition, arm in product(
        CANONICAL_BODIES,
        ("friction", "mass"),
        ("minus-10-percent", "nominal", "plus-10-percent"),
    ):
        arms.append({"body": body, "condition": condition, "arm": arm,
                     "source_body": None, "destination_body": None})
    if len(arms) != 52:
        raise AssertionError(f"A7 protocol matrix changed unexpectedly: {len(arms)} arms")
    if len({(item["body"], item["condition"], item["arm"]) for item in arms}) != len(arms):
        raise AssertionError("A7 protocol matrix contains duplicate arms")
    return tuple(arms)


def planned_runs() -> tuple[A7Run, ...]:
    """Expand arms into the preregistered 312 run identities."""
    runs = tuple(
        A7Run(**{**arm, "seed": seed, "repeat": repeat})
        for arm, seed, repeat in product(planned_arms(), SEEDS, REPEATS)
    )
    if len(runs) != 312 or len({run.key for run in runs}) != len(runs):
        raise AssertionError("A7 run expansion is not the expected unique 312-run matrix")
    return runs


def campaign_index_payload() -> dict[str, object]:
    """Build a deterministic, non-authorizing campaign plan payload."""
    runs = planned_runs()
    return {
        "protocol": "design.embodiment.physics3d-a7-stability-gate-v1",
        "execution_authorized": False,
        "execution_count": len(runs),
        "runs": [asdict(run) | {"key": run.key} for run in runs],
    }

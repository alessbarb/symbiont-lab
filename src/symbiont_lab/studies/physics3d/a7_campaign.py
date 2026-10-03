"""Pure planning primitives for the approved Physics3D A7 protocol.

This module enumerates work only. It deliberately has no run/launch operation;
campaign execution remains unauthorized until the protocol is frozen and
external scientific review is complete.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product

CANONICAL_BODIES = (
    "anthropomorphic-v6",
    "anthropomorphic-v6-vision",
    "crawler-v1",
    "asymmetric-v1",
)
SEEDS = (42, 43, 44)
REPEATS = (1, 2)
# Balanced directed cycle: every canonical body is represented once as source
# and once as destination, yielding four transitions rather than all 12.
REEMBODIMENT_TRANSITIONS = tuple(
    zip(CANONICAL_BODIES, (*CANONICAL_BODIES[1:], CANONICAL_BODIES[0]), strict=True)
)


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
    """Return all 44 distinct protocol arms (before seed/repeat expansion)."""
    arms: list[dict[str, str | None]] = []
    for body, condition in product(
        CANONICAL_BODIES, ("idle", "actuation", "collision", "checkpoint-restore")
    ):
        arms.append(
            {
                "body": body,
                "condition": condition,
                "arm": "nominal",
                "source_body": None,
                "destination_body": None,
            }
        )
    for source, destination in REEMBODIMENT_TRANSITIONS:
        arms.append(
            {
                "body": source,
                "condition": "re-embodiment",
                "arm": f"{source}-to-{destination}",
                "source_body": source,
                "destination_body": destination,
            }
        )
    for body, condition, arm in product(
        CANONICAL_BODIES,
        ("friction", "mass"),
        ("minus-10-percent", "nominal", "plus-10-percent"),
    ):
        arms.append(
            {
                "body": body,
                "condition": condition,
                "arm": arm,
                "source_body": None,
                "destination_body": None,
            }
        )
    if len(arms) != 44:
        raise AssertionError(f"A7 protocol matrix changed unexpectedly: {len(arms)} arms")
    if len({(item["body"], item["condition"], item["arm"]) for item in arms}) != len(arms):
        raise AssertionError("A7 protocol matrix contains duplicate arms")
    return tuple(arms)


def planned_runs() -> tuple[A7Run, ...]:
    """Expand arms into the requested 264-run identities."""
    runs = tuple(
        A7Run(**{**arm, "seed": seed, "repeat": repeat})
        for arm, seed, repeat in product(planned_arms(), SEEDS, REPEATS)
    )
    if len(runs) != 264 or len({run.key for run in runs}) != len(runs):
        raise AssertionError("A7 run expansion is not the expected unique 264-run matrix")
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

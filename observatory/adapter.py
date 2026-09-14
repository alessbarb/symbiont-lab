"""Passive projection from a real Symbiont runtime into Observatory v1."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from symbiont.cognition.genome import Genome
from symbiont.cognition.graph import CognitiveGraph

SCHEMA_VERSION = 1
ENVELOPE_TYPE = "symbiont-observatory-snapshot"
MAX_TICKS = 10_000


def _text(value: Any, limit: int) -> str:
    return str(value).replace("\x00", "")[:limit]


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _quality(value: Any) -> tuple[float, bool]:
    name = _enum_value(value).lower()
    scores = {"nominal": 1.0, "degraded": 0.6, "stale": 0.25, "unavailable": 0.0}
    return scores.get(name, 0.5), name != "unavailable"


_LOSS_CLASS_BOUNDS: tuple[tuple[float, str], ...] = (
    (0.0, "zero"),
    (0.0001, "trace"),
    (0.01, "low"),
    (0.1, "medium"),
    (0.5, "high"),
    (2.0, "extreme"),
)


def loss_class(loss: float) -> str:
    """Independent quantization from weight/eligibility classes: a Huber
    loss has a different distribution/meaning than a weight or an
    eligibility trace, so only the discipline (bounded, discrete, never
    raw) is shared, not the thresholds."""
    if not math.isfinite(loss) or loss < 0:
        return "zero"
    result = "zero"
    for bound, name in _LOSS_CLASS_BOUNDS:
        if loss >= bound:
            result = name
    return result


def _certainty(uncertainty: Any) -> float:
    try:
        number = float(uncertainty)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number) or number < 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 / (1.0 + number)))


def _cognition_state(cognition: Any) -> dict[str, Any]:
    readouts = {key: round(float(value), 6) for key, value in dict(getattr(cognition, "readouts", {})).items()}
    prediction_errors = {
        error.predictor_id: loss_class(error.loss) for error in tuple(getattr(cognition, "prediction_errors", ()))
    }
    mutations = []
    for mutation in tuple(getattr(cognition, "mutations", ())):
        entry: dict[str, Any] = {"kind": _text(getattr(mutation, "kind", ""), 32)}
        payload = dict(getattr(mutation, "payload", {}))
        if "node_id" in payload:
            entry["node_id"] = _text(payload["node_id"], 128)
        elif "source_id" in payload and "target_id" in payload:
            entry["edge_id"] = _text(f"{payload['source_id']}->{payload['target_id']}", 260)
        mutations.append(entry)
    # consecutive_failures is not yet exposed by CognitiveBridgeResult (only
    # .frozen is) -- disclosed gap, pinned to 0 until a follow-up task
    # threads the bridge's live SafetyState.consecutive_failures through.
    safety = {"consecutive_failures": 0, "frozen": bool(getattr(cognition, "frozen", False))}
    return {
        "topology_revision": max(0, int(getattr(cognition, "topology_revision", 0))),
        "readouts": readouts,
        "prediction_errors": prediction_errors,
        "edge_deltas": [],
        "mutations": mutations[:8],
        "safety_state": safety,
    }


def _state(result: Any) -> str:
    if getattr(result, "dissent", None) is not None:
        return "reflecting"
    if getattr(result, "investigated_capability", None):
        return "exploring"
    if getattr(result, "percepts", ()):
        return "observing"
    return "resting"


def project_tick(
    result: Any,
    *,
    acclimation: Any | None = None,
    display_id: str = "local-symbiont",
    ticks_remaining: int | None = None,
    revision_counts: dict[str, int] | None = None,
    genome: Genome | None = None,
) -> dict[str, Any]:
    """Project one RuntimeTickResult without coupling the core to this module.

    ``revision_counts`` is an optional accumulator (capability_id -> count)
    the caller keeps across ticks: each capability's dissent occurrence
    increments its own running total, so ``belief.revision_count`` is a
    real cumulative history rather than a per-tick 0/1 flag. Omitting it
    keeps the old per-tick-only behavior for a caller with no cross-tick
    state to offer.
    """
    narratives = tuple(getattr(result, "narrative", ()))[:128]
    percepts = []
    for percept in tuple(getattr(result, "percepts", ()))[:32]:
        score, available = _quality(getattr(percept, "quality", "unknown"))
        name = _text(getattr(percept, "name", "percept"), 64)
        percepts.append({"id": name, "label": name.replace("_", " "), "quality": score, "available": available})

    beliefs = []
    for entry in narratives:
        capability = _text(getattr(entry, "capability_id", "belief"), 64)
        contested_now = getattr(entry, "dissent", None) is not None
        if revision_counts is not None:
            if contested_now:
                revision_counts[capability] = revision_counts.get(capability, 0) + 1
            revision_count = revision_counts.get(capability, 0)
        else:
            revision_count = 1 if contested_now else 0
        beliefs.append({
            "id": capability,
            "label": _text(getattr(entry, "summary", capability), 120),
            "certainty": _certainty(getattr(entry, "uncertainty", None)),
            "evidence_count": max(0, int(getattr(entry, "evidence_gathered", 0))),
            "revision_count": revision_count,
            "contested": bool(getattr(entry, "contested", False)),
        })

    tick = max(0, int(getattr(result, "tick", 0)))
    events = []
    for percept in percepts[:32]:
        events.append({"id": _text(f"p-{tick}-{percept['id']}", 64), "type": "perception", "label": f"Observed {percept['label']}"})
    for allocation in tuple(getattr(result, "allocations", ()))[:16]:
        name = _text(getattr(allocation, "name", "attention"), 64)
        events.append({"id": _text(f"a-{tick}-{name}", 64), "type": "attention", "label": f"Attended to {name.replace('_', ' ')}"})
    dissent = getattr(result, "dissent", None)
    if dissent is not None:
        capability = _text(getattr(dissent, "capability_id", "belief"), 64)
        events.append({"id": _text(f"d-{tick}-{capability}", 64), "type": "contradiction", "label": f"Preserved contradictory evidence for {capability}", "belief_id": capability, "causal_chain": ["bounded second look", "evidence conflicted with baseline", "dissent preserved"]})

    known = tuple(getattr(acclimation, "known_capabilities", ())) if acclimation is not None else ()
    acclimated = tuple(getattr(acclimation, "acclimated_capabilities", ())) if acclimation is not None else ()
    summaries = [_text(getattr(entry, "summary", ""), 600) for entry in narratives]
    organism: dict[str, Any] = {
        "display_id": _text(display_id, 48) or "local-symbiont",
        "state": _state(result),
        "narrative": _text(" ".join(filter(None, summaries)), 600),
        "acclimation": len(acclimated) / len(known) if known else 0.0,
        "memory": [_text(summary, 200) for summary in summaries[:32]],
        "open_questions": [f"Learn more about {_text(getattr(entry, 'capability_id', 'this capability'), 64)}" for entry in narratives if _certainty(getattr(entry, "uncertainty", None)) < 0.5][:16],
        "investigations": ([f"Second look at {_text(result.investigated_capability, 64)}"] if getattr(result, "investigated_capability", None) else []),
        "regime_changes": [_text(name, 200) for name, observation in dict(getattr(result, "drift_observations", {})).items() if _enum_value(getattr(observation, "kind", "")).lower() == "regime_shift"][:16],
        "percepts": percepts,
        "beliefs": beliefs,
        "events": events[:64],
    }
    if ticks_remaining is not None:
        organism["resource_budget"] = {"ticks_remaining": max(0, int(ticks_remaining))}

    activity = min(1.0, (len(percepts) + len(getattr(result, "allocations", ())) * 2) / 12.0)
    member = {"display_id": organism["display_id"], "ecology": 0, "activity": activity, "knowledge_count": len(beliefs), "contested_count": sum(1 for belief in beliefs if belief["contested"])}

    cognition = getattr(result, "cognition", None)
    schema_version = SCHEMA_VERSION
    if cognition is not None and genome is not None:
        schema_version = 2
        organism["cognition"] = _cognition_state(cognition)
    return {"schema_version": schema_version, "tick": tick, "organism": organism, "population": {"members": [member], "relationships": []}}


def project_topology(graph: CognitiveGraph, *, genome: Genome, kernel_version: str) -> dict[str, Any]:
    """Structural-only projection: never carries weight/eligibility -- those
    are per-tick CognitionState, quantized, in _cognition_state above."""
    return {
        "genome_id": _text(genome.genome_id, 72),
        "kernel_version": _text(kernel_version, 32),
        "topology_revision": 0,  # caller overwrites with the bridge's live counter
        "nodes": [
            {"node_id": _text(node.node_id, 128), "kind": node.kind.value, "bias": node.bias, "tau": node.tau}
            for node in graph.nodes[:128]
        ],
        "edges": [
            {"source_id": _text(edge.source_id, 128), "target_id": _text(edge.target_id, 128), "kind": edge.kind.value}
            for edge in graph.edges[:1024]
        ],
    }


def envelope(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {"type": ENVELOPE_TYPE, "snapshot": snapshot}


def write_replay(path: str | Path, snapshots: Iterable[dict[str, Any]]) -> None:
    """Atomically write a bounded local replay; no data is transmitted."""
    target = Path(path)
    items = list(snapshots)
    if not 1 <= len(items) <= MAX_TICKS:
        raise ValueError(f"replay must contain between 1 and {MAX_TICKS} snapshots")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "snapshots": items}
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record bounded real Symbiont ticks for the passive Observatory")
    parser.add_argument("--ticks", type=int, default=20, help="finite tick budget (1-10000; default 20)")
    parser.add_argument("--output", type=Path, default=Path("symbiont-replay.json"))
    parser.add_argument("--display-id", default="local-symbiont", help="non-identifying display label")
    parser.add_argument("--checkpoint", type=Path, help="optional durable abstract runtime checkpoint")
    parser.add_argument("--stdout", action="store_true", help="also emit one postMessage-compatible JSON envelope per line")
    args = parser.parse_args(argv)
    if not 1 <= args.ticks <= MAX_TICKS:
        parser.error(f"--ticks must be between 1 and {MAX_TICKS}")

    from symbiont.core.governor import GovernedOrganism
    from symbiont.core.runtime import OrganismRuntime

    runtime = OrganismRuntime.load_or_create(args.checkpoint) if args.checkpoint else OrganismRuntime()
    organism = GovernedOrganism(runtime, max_ticks=args.ticks)
    revision_counts: dict[str, int] = {}
    snapshots = []
    for _ in range(args.ticks):
        result = organism.tick()
        snapshot = project_tick(
            result,
            acclimation=runtime.acclimation,
            display_id=args.display_id,
            ticks_remaining=organism.ticks_remaining,
            revision_counts=revision_counts,
        )
        snapshots.append(snapshot)
        if args.stdout:
            print(json.dumps(envelope(snapshot), ensure_ascii=False, separators=(",", ":")), flush=True)
    write_replay(args.output, snapshots)
    if args.checkpoint:
        runtime.save(args.checkpoint)
    return 0


if __name__ == "__main__":
    sys.exit(main())

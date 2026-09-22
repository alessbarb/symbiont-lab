"""Canonical cognition adoption for owner-facing resident restore paths.

A checkpoint written before the cognitive genome/graph existed is still the
same individual: its acclimation, sensory development, self-model and evidence
must survive. Owner-facing resident entry points may opt into this helper to
add only the canonical genome and empty germinal graph when those fields are
absent. Checkpoints that already contain cognition are restored unchanged.
"""

from __future__ import annotations

from typing import Any

from ... import __version__ as _symbiont_version
from ...cognition.birth import load_base_cognition
from ...cognition.checkpoint import export_genome_checkpoint
from ...cognition.limits import KernelLimits
from ...host.checkpoint import normalize_checkpoint
from ..cognition.bridge import CognitiveBridge
from .runtime import OrganismRuntime


def _running_version() -> tuple[int, int, int]:
    parts = (_symbiont_version.split(".") + ["0", "0"])[:3]
    return tuple(int(part) for part in parts)


def restore_resident_with_canonical_cognition(
    payload: dict[str, Any],
    **runtime_kwargs: Any,
) -> OrganismRuntime:
    """Restore one resident, adopting canonical cognition only when absent.

    This is deliberately not the generic ``OrganismRuntime.from_checkpoint``
    policy: laboratory code may need to reproduce a historical genome-less
    individual exactly. The main live CLI and Observatory resident opt in
    because their product contract is now "every resident has cognition".
    """
    normalized = normalize_checkpoint(payload)
    if normalized.get("genome") is not None:
        return OrganismRuntime.from_checkpoint(normalized, **runtime_kwargs)

    kernel_limits = runtime_kwargs.get("kernel_limits") or KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=kernel_limits,
        running_version=_running_version(),
    )
    bridge = CognitiveBridge(
        graph=graph,
        genome=genome,
        kernel_limits=kernel_limits,
    )

    adopted = dict(normalized)
    adopted["genome"] = export_genome_checkpoint(genome)
    adopted["cognitive_bridge"] = bridge.export_checkpoint()

    kwargs = dict(runtime_kwargs)
    kwargs["kernel_limits"] = kernel_limits
    return OrganismRuntime.from_checkpoint(adopted, **kwargs)

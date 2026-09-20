"""Embodiment coupling session and port bindings (v1.0 embodiment architecture).

Under the multidimensional evolutionary inheritance architecture, EmbodimentSession
represents the temporal causal coupling between an autonomous cognitive germen
(Symbiont) and a physical substrate (Body).

Key architectural invariants:
- Symbiont has persistent identity (symbiont_id).
- Body has independent identity (body_id).
- EmbodimentSession has its own identity (embodiment_id).
- Port bindings belong to the apparatus/EmbodimentSession, NEVER to cognition.
- Permutation of bindings (port permutation) alters the causal routing without
  mutating the Symbiont's internal state or the Body's physical structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import uuid
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class PortBinding:
    """Binding between an opaque cognitive channel and a physical body port.

    The binding configuration is owned by the apparatus / EmbodimentSession.
    Cognition only interacts with `channel_id` (e.g. 'in.0', 'out.1').
    Body only interacts with `port_id` (e.g. 'rec.0', 'eff.0').
    """

    channel_id: str
    port_id: str


@dataclass(slots=True)
class EmbodimentSession:
    """A bounded temporal embodiment session coupling a Symbiont to a Body."""

    embodiment_id: str
    symbiont_id: str
    body_id: str
    started_at: int
    ended_at: int | None = None
    input_bindings: dict[str, str] = field(default_factory=dict)   # channel_id -> port_id
    output_bindings: dict[str, str] = field(default_factory=dict)  # channel_id -> port_id
    active: bool = True
    _step_count: int = 0

    @property
    def is_active(self) -> bool:
        return self.active and self.ended_at is None

    @property
    def step_count(self) -> int:
        return self._step_count

    def sever(self, tick: int) -> None:
        """End this embodiment session (e.g. upon body transplant or death)."""
        self.ended_at = tick
        self.active = False

    def permute_outputs(self, new_channel_to_port: Mapping[str, str]) -> None:
        """Remap cognitive output channels to different physical effector ports.

        Used in port permutation perturbation experiments to study causal model revision.
        """
        self.output_bindings = dict(new_channel_to_port)

    def permute_inputs(self, new_channel_to_port: Mapping[str, str]) -> None:
        """Remap sensory input channels to different physical receptor ports."""
        self.input_bindings = dict(new_channel_to_port)

    def transduce_to_symbiont(
        self, physical_readings: Mapping[str, float]
    ) -> dict[str, float]:
        """Convert physical body port readings into opaque Symbiont input channels.

        Only bound channels are routed; port names are completely stripped.
        """
        opaque_inputs: dict[str, float] = {}
        for channel_id, port_id in self.input_bindings.items():
            if port_id in physical_readings:
                opaque_inputs[channel_id] = float(physical_readings[port_id])
            else:
                opaque_inputs[channel_id] = 0.0
        return opaque_inputs

    def route_to_body(
        self, opaque_activations: Mapping[str, float]
    ) -> dict[str, float]:
        """Convert opaque Symbiont output activations into physical body port commands."""
        physical_commands: dict[str, float] = {}
        for channel_id, level in opaque_activations.items():
            port_id = self.output_bindings.get(channel_id)
            if port_id is not None:
                # If multiple channels map to the same port, take max activation
                existing = physical_commands.get(port_id, 0.0)
                physical_commands[port_id] = max(existing, float(level))
        self._step_count += 1
        return physical_commands


def implant(
    symbiont_id: str,
    body_id: str,
    receptor_ids: Sequence[str | Any],
    effector_ids: Sequence[str | Any],
    *,
    started_at: int = 0,
    embodiment_id: str | None = None,
    channel_prefix_in: str = "in.",
    channel_prefix_out: str = "out.",
) -> EmbodimentSession:
    """Establish a fresh embodiment session between a Symbiont and Body.

    Binds receptor ports to opaque input channels (`in.0`, `in.1`, ...) and
    effector ports to opaque output channels (`out.0`, `out.1`, ...).
    Decoupled from human-readable alphabetical names (AUD-030, AUD-043): uses
    physical ordinals if available, otherwise preserves sequence order.
    """
    if embodiment_id is None:
        raw = f"{symbiont_id}:{body_id}:{started_at}:{uuid.uuid4().hex[:8]}"
        embodiment_id = f"emb_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

    # Extract port string ID respecting structural ordinal if available
    def _port_key_and_id(item: str | Any, default_idx: int) -> tuple[int, str]:
        if hasattr(item, "port_id"):
            ordinal = getattr(item, "ordinal", default_idx)
            return (int(ordinal), str(item.port_id))
        return (default_idx, str(item))

    ordered_receptors = [
        port_id for _, port_id in sorted(
            [_port_key_and_id(item, idx) for idx, item in enumerate(receptor_ids)],
            key=lambda t: t[0]
        )
    ]
    ordered_effectors = [
        port_id for _, port_id in sorted(
            [_port_key_and_id(item, idx) for idx, item in enumerate(effector_ids)],
            key=lambda t: t[0]
        )
    ]

    input_bindings: dict[str, str] = {
        f"{channel_prefix_in}{i}": port_id for i, port_id in enumerate(ordered_receptors)
    }
    output_bindings: dict[str, str] = {
        f"{channel_prefix_out}{j}": port_id for j, port_id in enumerate(ordered_effectors)
    }

    return EmbodimentSession(
        embodiment_id=embodiment_id,
        symbiont_id=symbiont_id,
        body_id=body_id,
        started_at=started_at,
        input_bindings=input_bindings,
        output_bindings=output_bindings,
    )


def implant_body(
    symbiont_id: str,
    body: Any,
    *,
    started_at: int = 0,
    embodiment_id: str | None = None,
) -> EmbodimentSession:
    """Convenience helper to implant using a Body's structural ordinals."""
    return implant(
        symbiont_id=symbiont_id,
        body_id=body.body_id,
        receptor_ids=body.ordered_receptors,
        effector_ids=body.ordered_effectors,
        started_at=started_at,
        embodiment_id=embodiment_id,
    )


__all__ = [
    "EmbodimentSession",
    "PortBinding",
    "implant",
    "implant_body",
]

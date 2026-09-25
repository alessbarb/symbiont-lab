from __future__ import annotations

import logging
import secrets
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..host.local_habitat import LocalHabitat
from ..social.capsule import CapsuleKeyPair, create_capsule
from ..social.trust import observe_capsule_trust
from .governor import GovernedOrganism
from .runtime import OrganismRuntime, RuntimeTickResult

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ResidentConfig:
    interval_seconds: float = 15.0
    checkpoint_every_ticks: int = 20
    max_ticks: int | None = None

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if self.checkpoint_every_ticks < 1:
            raise ValueError("checkpoint_every_ticks must be at least 1")
        if self.max_ticks is not None and self.max_ticks < 1:
            raise ValueError("max_ticks must be at least 1 when provided")


class ResidentOrganism:
    """Foreground resident lifecycle with explicit stop and durable memory.

    This class is intentionally transparent: it does not daemonize itself,
    modify startup configuration, elevate privileges or hide. A process
    supervisor such as ``systemd --user`` may keep it alive, while this loop
    remains an ordinary user process with a visible command line and a clean
    shutdown path.
    """

    def __init__(
        self,
        runtime: OrganismRuntime,
        *,
        state_file: str | Path,
        config: ResidentConfig | None = None,
        habitat: LocalHabitat | None = None,
        keypair: CapsuleKeyPair | None = None,
        on_tick: Callable[[RuntimeTickResult], None] | None = None,
        on_checkpoint: Callable[[], None] | None = None,
    ) -> None:
        self.runtime = runtime
        self.state_file = Path(state_file).expanduser()
        self.config = config if config is not None else ResidentConfig()
        self.habitat = habitat
        self.keypair = keypair
        self.on_tick = on_tick
        self.on_checkpoint = on_checkpoint
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def run(self) -> int:
        governed = GovernedOrganism(self.runtime, max_ticks=self.config.max_ticks)
        ticks = 0
        try:
            while not self._stop.is_set():
                result = governed.tick()
                ticks += 1
                if self.on_tick is not None:
                    self.on_tick(result)
                if ticks % self.config.checkpoint_every_ticks == 0:
                    self.runtime.save(self.state_file)
                    self._social_and_reproductive_step(ticks)
                    if self.on_checkpoint is not None:
                        self.on_checkpoint()
                if (
                    getattr(result, "physiology", None) is not None
                    and result.physiology.state.value == "dead"
                ):
                    break
                if self.config.max_ticks is not None and ticks >= self.config.max_ticks:
                    break
                is_dormant = (
                    getattr(result, "physiology", None) is not None
                    and result.physiology.state.value == "dormant"
                )
                interval = self.config.interval_seconds * (4.0 if is_dormant else 1.0)
                self._stop.wait(interval)
        finally:
            self.runtime.save(self.state_file)
            if self.on_checkpoint is not None:
                self.on_checkpoint()
        return ticks

    def _social_and_reproductive_step(self, ticks: int) -> None:
        if self.habitat is None or self.keypair is None:
            return

        # 1. Publish our own knowledge capsule
        try:
            acclimation_data = {}
            for cap_id in self.runtime._acclimation.acclimated_capabilities:
                b = self.runtime._acclimation.baseline(cap_id)
                if b is not None:
                    acclimation_data[cap_id] = {
                        "mean": b.mean,
                        "variance": b.variance,
                        "count": b.count,
                    }
            payload = {
                "organism_id": self.runtime.organism_id,
                "tick": ticks,
                "acclimation": acclimation_data,
            }
            capsule = create_capsule(self.keypair, payload)
            self.habitat.publish_capsule(capsule)
        except Exception:
            logger.exception("resident capsule publication failed")

        # 2. Ingest peer capsules and update trust / evidence
        try:
            peer_capsules = self.habitat.poll_capsules(exclude_signer=self.keypair.public_bytes)
            for cap in peer_capsules:
                # Peer trust/agreement is a social-epistemic signal only: it
                # updates trust bookkeeping via ``observe_capsule_trust`` but
                # must never itself manufacture metabolic reserve.
                # ``LocalHabitat`` has no physical resource-transfer
                # mechanism (see local_habitat.py), so there is no honest
                # exchange to gate here; trust agreement is recorded and
                # nothing more.
                observe_capsule_trust(
                    self.runtime.source_trust,
                    acclimation=self.runtime._acclimation,
                    capsule=cap,
                )
        except Exception:
            logger.exception("resident capsule ingestion failed")

        # 3. Reproductive budding if conditions are met
        try:
            reserve = self.runtime.metabolism.snapshot().reserve.get("maintenance", 0.0)
            if reserve >= 0.75 and ticks >= 20 and self.habitat.count_incubated() < 2:
                # Deduct parental reproduction cost
                self.runtime._metabolism.charge("maintenance", 0.35)
                child_suffix = secrets.token_hex(3)
                child_id = f"{self.runtime.organism_id}-child-{child_suffix}"
                from ...cognition.graph import load_base_graph

                child_runtime = OrganismRuntime(
                    genome=self.runtime._genome,
                    kernel_limits=self.runtime._kernel_limits,
                    cognitive_graph=(
                        load_base_graph(kernel_limits=self.runtime._kernel_limits)
                        if self.runtime._kernel_limits
                        else None
                    ),
                    organism_id=child_id,
                    generation=self.runtime._generation + 1,
                    explicit_metabolism=True,
                )
                embryo_payload = child_runtime.export_checkpoint()
                self.habitat.deposit_embryo(embryo_payload, child_id)
        except Exception:
            logger.exception("resident reproductive step failed")

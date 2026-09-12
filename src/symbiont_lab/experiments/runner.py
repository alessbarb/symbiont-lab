from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from symbiont.simulation import SimulationResult
from .manifest import RunManifest, SoftwareEnvironment, get_git_info
from .registry import get_protocol
from .spec import ExperimentSpec


class ExperimentRunner:
    """Unified runner for declarative experiments across CLI and dashboard.

    Runs protocol, records manifest, writes immutable artifacts to .symbiont/runs/.
    """

    def __init__(self, base_dir: Path | str = ".symbiont") -> None:
        self.base_dir = Path(base_dir)
        self.runs_dir = self.base_dir / "runs"

    def run(self, spec: ExperimentSpec) -> tuple[Any, RunManifest, Path]:
        protocol_fn = get_protocol(spec.protocol)
        started_at = datetime.now(timezone.utc).isoformat()

        sha, dirty = get_git_info()
        short_sha = sha[:7] if sha != "unknown" else "dev"
        short_id = uuid4().hex[:4]
        safe_protocol = spec.protocol.replace(".", "-")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{timestamp}-{safe_protocol}-{short_sha}-{short_id}"

        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        events_seen = []
        def _event_recorder(ev: Any) -> None:
            events_seen.append(ev)

        # Call protocol with appropriate arguments
        if spec.protocol == "simulate":
            result, _ = protocol_fn(
                hosts=spec.hosts,
                steps=spec.steps,
                seed=spec.seed,
                threat_rate=spec.threat_rate,
                poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity,
                drift_step=spec.drift_step,
                drift_fraction=spec.drift_fraction,
                drift_magnitude=spec.drift_magnitude,
                on_event=_event_recorder,
            )
            raw_metrics = asdict(result) if hasattr(result, "as_dict") is False else result.as_dict()
        elif spec.protocol == "attention.causal":
            budget = spec.extra_params.get("attention", {}).get("budget_per_1000", 12.0)
            if isinstance(budget, list):
                budget = budget[0]
            result = protocol_fn(
                hosts=spec.hosts,
                steps=spec.steps,
                seed=spec.seed,
                threat_rate=spec.threat_rate,
                poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity,
                budget_per_1000=float(budget),
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "attention.replicated":
            budgets = spec.extra_params.get("attention", {}).get("budgets_per_1000", [5, 12, 20])
            ref_strategy = spec.extra_params.get("attention", {}).get("reference_strategy", "random")
            result = protocol_fn(
                seeds=spec.seeds,
                budgets_per_1000=budgets,
                hosts=spec.hosts,
                steps=spec.steps,
                threat_rate=spec.threat_rate,
                poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity,
                reference_strategy=ref_strategy,
            )
            raw_metrics = result.as_dict()
        else:
            # General fallback to protocol call with standard params
            try:
                result = protocol_fn(
                    hosts=spec.hosts,
                    steps=spec.steps,
                    seed=spec.seed,
                    threat_rate=spec.threat_rate,
                    poison_fraction=spec.poison_fraction,
                    heterogeneity=spec.heterogeneity,
                )
            except TypeError:
                result = protocol_fn()
            raw_metrics = result.as_dict() if hasattr(result, "as_dict") else {}

        finished_at = datetime.now(timezone.utc).isoformat()

        # Compute world digest if events were observed
        if events_seen:
            h = sha256()
            for ev in events_seen:
                h.update(f"{ev.step}:{ev.host_index}:{ev.truth_label}:{ev.is_threat}\n".encode("utf-8"))
            world_digest = h.hexdigest()
        else:
            world_digest = getattr(result, "world_digest", "na")

        manifest = RunManifest(
            schema_version=spec.schema_version,
            run_id=run_id,
            experiment_id=spec.experiment_id,
            protocol=spec.protocol,
            protocol_version=spec.protocol_version,
            started_at=started_at,
            finished_at=finished_at,
            seed=spec.seed,
            world_digest=world_digest,
            software=SoftwareEnvironment(git_sha=sha, dirty=dirty),
            config=spec.as_dict(),
            metrics={"result": raw_metrics},
        )

        manifest.save(run_dir)
        (run_dir / "metrics.json").write_text(
            json.dumps(raw_metrics, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )

        return result, manifest, run_dir

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from symbiont.simulation import SimulationResult
from symbiont_lab.studies.common.digests import compute_world_digest
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

    def run(
        self,
        spec: ExperimentSpec,
        progress_cb: Callable[[Any], None] | None = None,
    ) -> tuple[Any, RunManifest, Path]:
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
            if progress_cb is not None:
                progress_cb(ev)

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
        elif spec.protocol == "evidence.causal-budget":
            evidence = spec.extra_params.get("evidence", {})
            budgets = evidence.get("budgets_per_1000", [5.0, 12.0, 20.0])
            exploration = evidence.get("exploration_fractions", [0.0, 0.05, 0.10, 0.20])
            sensor_noise = float(evidence.get("sensor_noise", 0.18))
            result = protocol_fn(
                seeds=spec.seeds,
                budgets_per_1000=budgets,
                exploration_fractions=exploration,
                hosts=spec.hosts,
                steps=spec.steps,
                threat_rate=spec.threat_rate,
                poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity,
                drift_step=spec.drift_step,
                drift_fraction=spec.drift_fraction,
                drift_magnitude=spec.drift_magnitude,
                sensor_noise=sensor_noise,
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "heritage.ecological-shift":
            heritage = spec.extra_params.get("heritage", {})
            source_rate = float(heritage.get("source_threat_rate", spec.threat_rate))
            target_rates = heritage.get("target_threat_rates", [0.006, source_rate, 0.054])
            target_offset = int(heritage.get("target_offset", 4001))
            heritage_limit = int(heritage.get("heritage_limit", 24))
            result = protocol_fn(
                source_seeds=spec.seeds,
                source_threat_rate=source_rate,
                target_threat_rates=target_rates,
                target_offset=target_offset,
                hosts=spec.hosts,
                steps=spec.steps,
                poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity,
                heritage_limit=heritage_limit,
            )
            raw_metrics = result.as_dict()
        elif spec.protocol in {
            "learning.predictive-utility",
            "learning.private-model-utility",
            "learning.private-model-controls",
            "learning.temporal-private-model-controls",
            "learning.private-model-regime-symmetric",
            "learning.adaptive-replay-matched-control",
            "learning.replay-pressure-curve",
            "learning.structural-producer-fairness",
            "learning.continuous-temporal-challenge",
            "learning.cognitive-ecology-embodiment",
            "learning.continuous-temporal-controls",
            "learning.cognitive-graph-causal-composition",
        }:
            # These protocols consume the declarative tick budget and seed list;
            # never let matching function defaults masquerade as provenance.
            result = protocol_fn(seeds=spec.seeds, ticks=spec.steps)
            raw_metrics = result.as_dict()
        elif spec.protocol == "learning.embodied-behavioral-ablation":
            ablation = spec.extra_params.get("ablation", {})
            horizon_ticks = int(ablation.get("horizon_ticks", 256))
            result = protocol_fn(
                seeds=spec.seeds,
                ticks=spec.steps,
                horizon_ticks=horizon_ticks,
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "learning.canonical-sensorimotor-agency":
            result = protocol_fn(seeds=spec.seeds, ticks=spec.steps)
            raw_metrics = result.as_dict()
        elif spec.protocol == "learning.canonical-sensorimotor-counterfactual":
            result = protocol_fn(seeds=spec.seeds, warmup_ticks=spec.steps)
            raw_metrics = result.as_dict()
        elif spec.protocol == "learning.canonical-sensorimotor-adaptation":
            adaptation = spec.extra_params.get("adaptation", {})
            result = protocol_fn(
                seeds=spec.seeds,
                warmup_ticks=spec.steps,
                horizon_ticks=int(adaptation.get("horizon_ticks", 96)),
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "attention.retrospective":
            attention = spec.extra_params.get("attention", {})
            budgets = attention.get("curve_budgets_per_1000", (2.0, 5.0, 10.0, 20.0, 40.0))
            result = protocol_fn(
                hosts=spec.hosts, steps=spec.steps, seed=spec.seed,
                threat_rate=spec.threat_rate, poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity, drift_step=spec.drift_step,
                drift_fraction=spec.drift_fraction, drift_magnitude=spec.drift_magnitude,
                curve_budgets_per_1000=budgets,
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "evidence.second-look":
            evidence = spec.extra_params.get("evidence", {})
            result = protocol_fn(
                hosts=spec.hosts, steps=spec.steps, seed=spec.seed,
                threat_rate=spec.threat_rate, poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity, drift_step=spec.drift_step,
                drift_fraction=spec.drift_fraction, drift_magnitude=spec.drift_magnitude,
                budget=evidence.get("budget"),
                sensor_noise=float(evidence.get("sensor_noise", 0.18)),
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "evidence.replicated":
            evidence = spec.extra_params.get("evidence", {})
            result = protocol_fn(
                seeds=spec.seeds, hosts=spec.hosts, steps=spec.steps,
                threat_rate=spec.threat_rate, poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity, drift_step=spec.drift_step,
                drift_fraction=spec.drift_fraction, drift_magnitude=spec.drift_magnitude,
                budget=evidence.get("budget"),
                sensor_noise=float(evidence.get("sensor_noise", 0.18)),
                reference_strategy=evidence.get("reference_strategy", "random"),
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "evidence.noise-sweep":
            evidence = spec.extra_params.get("evidence", {})
            result = protocol_fn(
                seeds=spec.seeds,
                noise_levels=evidence.get("noise_levels", (0.08, 0.18, 0.3, 0.45)),
                budget_per_1000=float(evidence.get("budget_per_1000", 12.0)),
                hosts=spec.hosts, steps=spec.steps, threat_rate=spec.threat_rate,
                poison_fraction=spec.poison_fraction, heterogeneity=spec.heterogeneity,
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "heritage.longitudinal":
            heritage = spec.extra_params.get("heritage", {})
            result = protocol_fn(
                hosts=spec.hosts, steps=spec.steps, seed=spec.seed,
                threat_rate=spec.threat_rate, poison_fraction=spec.poison_fraction,
                heterogeneity=spec.heterogeneity, drift_step=spec.drift_step,
                drift_fraction=spec.drift_fraction, drift_magnitude=spec.drift_magnitude,
                heritage_limit=int(heritage.get("heritage_limit", 24)),
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "heritage.stress":
            heritage = spec.extra_params.get("heritage", {})
            result = protocol_fn(
                source_seed=spec.seed, target_seed=int(heritage.get("target_offset", 1009)) + spec.seed,
                hosts=spec.hosts, steps=spec.steps, threat_rate=spec.threat_rate,
                poison_fraction=spec.poison_fraction, heterogeneity=spec.heterogeneity,
                drift_step=spec.drift_step, drift_fraction=spec.drift_fraction,
                drift_magnitude=spec.drift_magnitude,
                heritage_limit=int(heritage.get("heritage_limit", 24)),
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "heritage.replicated":
            heritage = spec.extra_params.get("heritage", {})
            result = protocol_fn(
                source_seeds=spec.seeds, target_offset=int(heritage.get("target_offset", 1009)),
                hosts=spec.hosts, steps=spec.steps, threat_rate=spec.threat_rate,
                poison_fraction=spec.poison_fraction, heterogeneity=spec.heterogeneity,
                drift_step=spec.drift_step, drift_fraction=spec.drift_fraction,
                drift_magnitude=spec.drift_magnitude,
                heritage_limit=int(heritage.get("heritage_limit", 24)),
            )
            raw_metrics = result.as_dict()
        elif spec.protocol == "continuity.recurrent-restoration":
            if spec.steps != ExperimentSpec().steps:
                raise ValueError(
                    "continuity.recurrent-restoration does not use world.steps; "
                    "declare its level budgets through the study API"
                )
            result = protocol_fn(seeds=spec.seeds)
            raw_metrics = result.as_dict()
        else:
            candidates: dict[str, Any] = {
                "hosts": spec.hosts,
                "steps": spec.steps,
                "seed": spec.seed,
                "seeds": spec.seeds,
                "threat_rate": spec.threat_rate,
                "poison_fraction": spec.poison_fraction,
                "heterogeneity": spec.heterogeneity,
                "drift_step": spec.drift_step,
                "drift_fraction": spec.drift_fraction,
                "drift_magnitude": spec.drift_magnitude,
            }
            accepted = inspect.signature(protocol_fn).parameters
            kwargs = {name: value for name, value in candidates.items() if name in accepted}
            missing_required = [
                name
                for name, param in accepted.items()
                if param.default is inspect.Parameter.empty
                and param.kind in (
                    inspect.Parameter.KEYWORD_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
                and name not in kwargs
            ]
            if missing_required:
                raise ValueError(
                    f"protocol '{spec.protocol}' requires parameters {missing_required} "
                    "that a declarative experiment.toml spec cannot supply yet; "
                    "use `symbiont-lab study run` or call the protocol directly instead"
                )
            res = protocol_fn(**kwargs)
            result = res[0] if isinstance(res, tuple) else res
            raw_metrics = result.as_dict() if hasattr(result, "as_dict") else {}

        # Every embodiment/self-boundary campaign result carries the same
        # architecture/non-interference gate. Scientific hypothesis outcome and
        # apparatus validity are intentionally separate dimensions.
        if spec.protocol.startswith("embodiment."):
            from symbiont_lab.studies.embodiment.integrity_gates import (
                run_embodiment_integrity_gates,
            )
            gates = run_embodiment_integrity_gates(
                organism_id=f"gate:{spec.experiment_id}",
                world_seed=spec.seed,
            )
            if not isinstance(raw_metrics, dict):
                raw_metrics = {"result": raw_metrics}
            raw_metrics = dict(raw_metrics)
            raw_metrics["integrity_gates"] = gates.as_dict()
            raw_metrics["scientifically_valid"] = gates.all_pass

        finished_at = datetime.now(timezone.utc).isoformat()

        if events_seen:
            world_digest = compute_world_digest(events_seen)
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
            config_digest="",
        )

        manifest.save(run_dir)
        (run_dir / "metrics.json").write_text(
            json.dumps(raw_metrics, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        output = spec.extra_params.get("output", {})
        if not isinstance(output, dict):
            raise ValueError("experiment output configuration must be a mapping")
        # Output switches are executable protocol configuration, not passive
        # annotations.  Keep metrics.json as the stable machine-readable
        # artifact used by reproduction, and materialize the optional named
        # artifacts requested by the TOML document.
        if output.get("save_summary", False):
            (run_dir / "summary.json").write_text(
                json.dumps(raw_metrics, indent=2, sort_keys=True, default=str),
                encoding="utf-8",
            )
        if output.get("save_trace", False):
            (run_dir / "trace.json").write_text(
                json.dumps(events_seen, indent=2, sort_keys=True, default=str),
                encoding="utf-8",
            )

        return result, manifest, run_dir

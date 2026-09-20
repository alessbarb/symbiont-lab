"""Background Private SLM training for Physics3D.

Training stays outside the organism process. The canonical runtime owns the
request, corpus and registry; this worker only executes an authorized bounded
training job and stores the resulting artifact.
"""
from __future__ import annotations

from concurrent.futures import Future, ProcessPoolExecutor
import hashlib
import json
import multiprocessing as mp
import os
import signal
import tempfile
from pathlib import Path
from typing import Any

from symbiont.modeling.authority import ArchitectureId, TrainingRequest
from symbiont.modeling.corpus import TrainingCorpus, build_training_corpus
from symbiont.modeling.gateway import PrivateModelBridge
from symbiont.modeling.tokenizer import NativeTokenizer
from symbiont_lab.modeling.artifacts import FileArtifactStore
from symbiont_lab.modeling.gateway import ArtifactInferenceGateway


def _tokenizer_path(models_dir: str | Path, model_id: str) -> Path:
    return Path(models_dir) / f"{model_id}.tokenizer.json"


def _train_job(
    models_dir: str,
    request: TrainingRequest,
    corpus: TrainingCorpus,
    vocabulary: tuple[str, ...],
    device: str,
) -> dict[str, Any]:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    from symbiont_lab.modeling.factory import PrivateModelFactory

    if device == "cpu":
        try:
            os.nice(10)
        except OSError:
            pass
        try:
            import torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
        except (ImportError, RuntimeError):
            pass

    tokenizer = NativeTokenizer(vocabulary=vocabulary)
    store = FileArtifactStore(models_dir)
    factory = PrivateModelFactory(store=store, device=device)
    result = factory.build(
        request=request,
        corpus=corpus,
        tokenizer=tokenizer,
    )
    model_id = result.training.artifact.manifest.model_id
    tokenizer_path = _tokenizer_path(models_dir, model_id)
    encoded_tokenizer = json.dumps(
        {"vocabulary": list(tokenizer.vocabulary)},
        sort_keys=True,
        separators=(",", ":"),
    )
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{tokenizer_path.name}.",
        suffix=".tmp",
        dir=str(tokenizer_path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded_tokenizer)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, tokenizer_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    baseline_losses = {
        "uniform": result.evaluation.uniform.mean_log_loss,
        "frequency": result.evaluation.frequency.mean_log_loss,
        "persistence": result.evaluation.persistence.mean_log_loss,
    }
    best_baseline = min(baseline_losses, key=baseline_losses.get)
    return {
        "model_id": model_id,
        "promote": bool(result.decision.promote),
        "evaluation_summary": list(result.decision.summary_classes()),
        "decision_reason": result.decision.reason,
        "gain_over_trivial": float(result.decision.gain_over_trivial),
        "candidate_loss": float(result.evaluation.candidate.mean_log_loss),
        "best_baseline": best_baseline,
        "best_baseline_loss": float(baseline_losses[best_baseline]),
    }


class Physics3DSlmManager:
    """Non-blocking SLM trainer/attacher for one canonical organism."""

    def __init__(
        self,
        *,
        models_dir: str | Path,
        train_interval: int = 4096,
        min_records: int = 64,
        device: str = "cpu",
    ) -> None:
        if train_interval < 64:
            raise ValueError("train_interval must be >= 64")
        if min_records < 3:
            raise ValueError("min_records must be >= 3")
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.train_interval = int(train_interval)
        self.min_records = int(min_records)
        self.device = str(device)
        self._executor = ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn"))
        self._future: Future | None = None
        self._last_submitted_tick = -self.train_interval
        self._last_error: str | None = None
        self._last_gate_reason: str | None = None
        self._last_gate_gain: float | None = None
        self._last_candidate_loss: float | None = None
        self._last_best_baseline: str | None = None
        self._last_best_baseline_loss: float | None = None

    @property
    def training(self) -> bool:
        return self._future is not None and not self._future.done()

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def last_gate_reason(self) -> str | None:
        return self._last_gate_reason

    @property
    def last_gate_gain(self) -> float | None:
        return self._last_gate_gain

    @property
    def last_candidate_loss(self) -> float | None:
        return self._last_candidate_loss

    @property
    def last_best_baseline(self) -> str | None:
        return self._last_best_baseline

    @property
    def last_best_baseline_loss(self) -> float | None:
        return self._last_best_baseline_loss

    def _attach_model(self, runtime, model_id: str) -> None:
        tokenizer_file = _tokenizer_path(self.models_dir, model_id)
        payload = json.loads(tokenizer_file.read_text(encoding="utf-8"))
        vocabulary = payload.get("vocabulary")
        if not isinstance(vocabulary, list) or not all(
            isinstance(token, str) for token in vocabulary
        ):
            raise ValueError("invalid persisted private-model tokenizer")
        tokenizer = NativeTokenizer(vocabulary=tuple(vocabulary))
        record = runtime.model_registry.get(model_id)
        if record is None:
            raise ValueError("cannot attach tokenizer for unknown private model")
        if record.tokenizer_hash != tokenizer.tokenizer_hash:
            raise ValueError("persisted tokenizer does not match private model")
        gateway = ArtifactInferenceGateway(
            FileArtifactStore(self.models_dir),
            vocab_size=len(tokenizer.vocabulary),
            pad_id=0,
            device=self.device,
        )
        runtime.attach_private_model_bridge(
            PrivateModelBridge(
                registry=runtime.model_registry,
                tokenizer=tokenizer,
                gateway=gateway,
            )
        )

    def attach_existing(self, runtime) -> None:
        active = runtime.model_registry.active
        if active is None:
            return
        path = _tokenizer_path(self.models_dir, active.model_id)
        if not path.is_file():
            self._last_error = (
                "active SLM artifact exists but its tokenizer sidecar is missing"
            )
            return
        try:
            self._attach_model(runtime, active.model_id)
            self._last_error = None
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _make_registry_room(runtime) -> None:
        """Retire old non-active candidates before bounded registry saturation."""
        records = runtime.model_registry.records
        checkpoint = runtime.model_registry.checkpoint()
        capacity = int(checkpoint.get("max_models", 16))
        if len(records) < capacity:
            return

        active = runtime.model_registry.active
        candidates = [
            record
            for record in records
            if (active is None or record.model_id != active.model_id)
            and record.state.value in {"shadow", "degraded"}
        ]
        if not candidates:
            return

        # Retire the oldest replaceable candidate. ModelRegistry will evict a
        # RETIRED record atomically when the new artifact is registered.
        runtime.retire_private_model(candidates[0].model_id)

    @staticmethod
    def _retire_stale_candidates(runtime, *, keep: int = 3) -> None:
        active = runtime.model_registry.active
        replaceable = [
            record
            for record in runtime.model_registry.records
            if (active is None or record.model_id != active.model_id)
            and record.state.value in {"shadow", "degraded"}
        ]
        for record in replaceable[:-keep] if keep > 0 else replaceable:
            runtime.retire_private_model(record.model_id)

    def poll(self, runtime) -> None:
        future = self._future
        if future is None or not future.done():
            return
        self._future = None
        try:
            result = future.result()
            model_id = str(result["model_id"])
            self._last_gate_reason = str(result.get("decision_reason") or "")
            self._last_gate_gain = float(result["gain_over_trivial"])
            self._last_candidate_loss = float(result["candidate_loss"])
            self._last_best_baseline = str(result["best_baseline"])
            self._last_best_baseline_loss = float(result["best_baseline_loss"])
            store = FileArtifactStore(self.models_dir)
            artifact = store.get(model_id)
            summary = tuple(int(x) for x in result.get("evaluation_summary", ()))
            self._make_registry_room(runtime)
            record = runtime.adopt_private_model(
                artifact.manifest,
                evaluation_summary=summary,
            )
            if bool(result.get("promote", False)):
                record = runtime.activate_private_model(
                    record.model_id,
                    promotion_authorized=True,
                    evaluation_summary=summary,
                )
                self._attach_model(runtime, record.model_id)
            else:
                # A rejected SHADOW candidate must never replace the inference
                # bridge of an already ACTIVE model with an incompatible tokenizer.
                active = runtime.model_registry.active
                if active is not None:
                    self._attach_model(runtime, active.model_id)
                else:
                    runtime.attach_private_model_bridge(None)
            self._retire_stale_candidates(runtime)
            self._last_error = None
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"

    def maybe_schedule(self, runtime, *, current_tick: int) -> bool:
        self.poll(runtime)
        if self._future is not None:
            return False
        if current_tick - self._last_submitted_tick < self.train_interval:
            return False

        # Physics3D v2 trains only on true temporal transitions. Historical
        # same-tick life.* records remain in the ledger for audit but cannot
        # contaminate the new causal objective.
        records = tuple(
            record
            for record in runtime.experience_ledger.records
            if record.record_id.startswith("transition.")
        )
        if len(records) < self.min_records:
            return False

        try:
            corpus = build_training_corpus(records)
            tokenizer = NativeTokenizer.from_records(corpus.train)
            request = runtime.request_private_model_training(
                corpus_hash=corpus.manifest.corpus_hash,
                tokenizer_hash=tokenizer.tokenizer_hash,
                architecture_id=ArchitectureId.GRU_V1,
                context_window=96,
                requested_parameters=1_000_000,
                requested_epochs=2,
                requested_steps=12,
                seed=(
                    int.from_bytes(
                        hashlib.sha256(
                            f"{runtime.organism_id}:{current_tick}".encode("utf-8")
                        ).digest()[:8],
                        "big",
                    )
                    & 0x7FFFFFFF
                ),
            )
            self._future = self._executor.submit(
                _train_job,
                str(self.models_dir),
                request,
                corpus,
                tokenizer.vocabulary,
                self.device,
            )
            self._last_submitted_tick = current_tick
            self._last_error = None
            return True
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            self._last_submitted_tick = current_tick
            return False

    def close(self) -> None:
        """Stop background training without leaving non-daemon workers behind."""
        future = self._future
        self._future = None
        if future is not None and not future.done():
            future.cancel()

        # ProcessPoolExecutor cannot cancel a task that has already started.
        # Capture its spawned workers before shutdown and terminate any still
        # running process so interpreter exit never waits on an abandoned SLM
        # training job after the 3D window has been closed.
        processes_map = getattr(self._executor, "_processes", None) or {}
        processes = tuple(processes_map.values())
        manager_thread = getattr(self._executor, "_executor_manager_thread", None)
        self._executor.shutdown(wait=False, cancel_futures=True)

        for process in processes:
            try:
                if process.is_alive():
                    process.terminate()
            except (OSError, ValueError):
                pass
        for process in processes:
            try:
                process.join(timeout=0.75)
                if process.is_alive() and hasattr(process, "kill"):
                    process.kill()
                    process.join(timeout=0.25)
            except (OSError, ValueError):
                pass
        if manager_thread is not None:
            try:
                manager_thread.join(timeout=1.0)
            except RuntimeError:
                pass


__all__ = ["Physics3DSlmManager"]

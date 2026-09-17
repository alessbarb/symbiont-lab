"""Tests for canonical boundaries, epistemic conventions, organism limits,
physiology configs, observatory boundaries, and deterministic fingerprinting.
"""
from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from symbiont.core.epistemic import (
    DEFAULT_EPISTEMIC_CONVENTIONS,
    EpistemicConventions,
    RecencyClass,
)
from symbiont.core.limits import OrganismLimits
from symbiont.core.physiology import (
    DEFAULT_PHYSIOLOGY_CONFIG,
    PhysiologyConfig,
)
from symbiont.core.fingerprint import (
    FINGERPRINT_SCHEMA_VERSION,
    generate_runtime_fingerprint,
)
from symbiont.host.adaptive import (
    AdaptiveSenseModel,
    _ADAPTIVE_HISTORICAL_MIN_SAMPLES,
)
from symbiont.core.runtime_defaults import (
    DEFAULT_CHECKPOINT_TICKS,
    DEFAULT_STATE_FILE,
    DEFAULT_TICK_INTERVAL_SECONDS,
)
from observatory.config import (
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_OBSERVATORY_DIR,
    DEFAULT_SERVER_PORT,
    INGESTION_MAX_BODY_PARTS,
    INGESTION_MAX_COGNITIVE_REGIONS,
    INGESTION_MAX_SENSORY_PARTS,
    STALE_HEARTBEAT_FACTOR,
)


def test_epistemic_conventions_invariants() -> None:
    conv = DEFAULT_EPISTEMIC_CONVENTIONS
    assert conv.established_signal_min_samples == 5
    assert conv.ewma_alpha == 0.06
    assert conv.health_classes == 16
    assert conv.confidence_classes == 16
    assert conv.cost_classes == 16
    assert conv.maturity_classes == 8
    assert conv.activity_classes == 16
    assert conv.recency_thresholds == (10, 40, 120, 400)
    assert conv.maturity_thresholds == (0, 1, 2, 4, 8, 16, 32, 64)

    assert conv.classify_recency(0) is RecencyClass.CURRENT
    assert conv.classify_recency(9) is RecencyClass.CURRENT
    assert conv.classify_recency(10) is RecencyClass.SHORT_IDLE
    assert conv.classify_recency(39) is RecencyClass.SHORT_IDLE
    assert conv.classify_recency(40) is RecencyClass.IDLE
    assert conv.classify_recency(119) is RecencyClass.IDLE
    assert conv.classify_recency(120) is RecencyClass.LONG_IDLE
    assert conv.classify_recency(399) is RecencyClass.LONG_IDLE
    assert conv.classify_recency(400) is RecencyClass.DORMANT
    assert conv.classify_recency(1000) is RecencyClass.DORMANT


def test_organism_limits_invariants() -> None:
    limits = OrganismLimits()
    assert limits.max_host_checkpoint_bytes == 2 * 1024 * 1024
    assert limits.max_knowledge_checkpoint_bytes == 256 * 1024
    assert limits.max_exchange_bytes == 4096
    assert limits.max_sensory_parts == 256
    assert limits.max_cognitive_regions == 32
    assert limits.max_body_parts == 288
    assert limits.max_body_dependencies == 256
    assert limits.max_degradation_items == 256
    assert limits.max_dissent == 256
    assert limits.max_selection_opportunities == 64

    # Crucial architectural assertion: OrganismLimits must NOT contain temporal dynamics
    assert not hasattr(limits, "aging_ticks")
    assert not hasattr(limits, "waste_ticks")
    assert not hasattr(limits, "decay_interval")

    # Invariants on types
    with pytest.raises(ValueError):
        OrganismLimits(max_sensory_parts=-1)


def test_physiology_config_immutability_and_dynamics() -> None:
    config = DEFAULT_PHYSIOLOGY_CONFIG
    assert config.ratio_unrecoverable == 0.0
    assert config.ratio_severe == 0.2
    assert config.ratio_elevated == 0.5
    assert config.max_repair_per_tick == 0.25
    assert config.aging_ticks == 16
    assert config.waste_ticks == 8

    # Strictly immutable (frozen dataclass) to prevent silent runtime mutations
    with pytest.raises(FrozenInstanceError):
        config.max_repair_per_tick = 0.5  # type: ignore[misc]


def test_adaptive_sense_model_historical_divergence_preserved() -> None:
    assert _ADAPTIVE_HISTORICAL_MIN_SAMPLES == 4
    model = AdaptiveSenseModel()
    assert model._min_samples == 4
    assert model._min_samples != DEFAULT_EPISTEMIC_CONVENTIONS.established_signal_min_samples

    # Verify restore without min_samples preserves historical 4
    restored = AdaptiveSenseModel.restore({})
    assert restored._min_samples == 4


def test_observatory_independence_and_limits() -> None:
    # Observatory defines its own ingestion bounds
    assert INGESTION_MAX_SENSORY_PARTS == 256
    assert INGESTION_MAX_COGNITIVE_REGIONS == 32
    assert INGESTION_MAX_BODY_PARTS == 288
    assert STALE_HEARTBEAT_FACTOR == 3

    # Scan all observatory python files to guarantee NO imports of internal symbiont biology
    observatory_dir = Path(__file__).resolve().parents[3] / "observatory"
    forbidden_modules = {
        "symbiont.core.limits",
        "symbiont.core.epistemic",
        "symbiont.core.physiology",
        "symbiont.core.selfmodel",
    }

    for py_file in observatory_dir.rglob("*.py"):
        if "tests" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), f"{py_file} imports forbidden {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_modules:
                    assert not node.module.startswith(forbidden), f"{py_file} imports forbidden {node.module}"


def test_no_symbiont_imports_symbiont_lab() -> None:
    symbiont_dir = Path(__file__).resolve().parents[3] / "src" / "symbiont"
    for py_file in symbiont_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("symbiont_lab"), f"{py_file} imports symbiont_lab"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("symbiont_lab"), f"{py_file} imports symbiont_lab"


def test_runtime_defaults_decoupling() -> None:
    # Organism and Observatory have independent timing defaults
    assert DEFAULT_TICK_INTERVAL_SECONDS == 15.0
    assert DEFAULT_CHECKPOINT_TICKS == 20
    assert DEFAULT_HEARTBEAT_INTERVAL_SECONDS == 15.0

    stale_after = DEFAULT_HEARTBEAT_INTERVAL_SECONDS * STALE_HEARTBEAT_FACTOR
    assert stale_after == 45.0


def test_runtime_fingerprint_determinism() -> None:
    fp1 = generate_runtime_fingerprint(
        software_version="0.60.0",
        genome_id="base-genome",
        subsystem_overrides={"a": 1, "b": 2},
    )
    # Permuting dict key order must produce identical fingerprint
    fp2 = generate_runtime_fingerprint(
        software_version="0.60.0",
        genome_id="base-genome",
        subsystem_overrides={"b": 2, "a": 1},
    )
    assert fp1 == fp2
    assert len(fp1) == 64

    # Altering an epistemic convention changes the fingerprint
    custom_epistemic = EpistemicConventions(established_signal_min_samples=6)
    fp_custom = generate_runtime_fingerprint(
        software_version="0.60.0",
        genome_id="base-genome",
        epistemic_conventions=custom_epistemic,
    )
    assert fp_custom != fp1

    # Altering a physiology config changes the fingerprint
    custom_phys = PhysiologyConfig(max_repair_per_tick=0.30)
    fp_phys = generate_runtime_fingerprint(
        software_version="0.60.0",
        genome_id="base-genome",
        physiology_config=custom_phys,
    )
    assert fp_phys != fp1

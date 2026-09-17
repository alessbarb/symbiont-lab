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


def test_physiology_config_governs_metabolic_pressure() -> None:
    from symbiont.core.metabolism import MetabolicLedger, ResourcePressure

    # Default thresholds: ratio_severe = 0.2, ratio_elevated = 0.5
    default_ledger = MetabolicLedger(capacity={"observation": 1.0, "cognition": 1.0, "persistence": 1.0, "maintenance": 1.0})
    default_ledger.charge("observation", 0.75)  # reserve remaining = 0.25 -> ratio = 0.25
    # Under default config (0.25 >= 0.2 and < 0.5), pressure is ELEVATED
    assert default_ledger.pressure() is ResourcePressure.ELEVATED

    # Custom thresholds: ratio_severe = 0.35
    custom_phys = PhysiologyConfig(ratio_severe=0.35)
    custom_ledger = MetabolicLedger(
        capacity={"observation": 1.0, "cognition": 1.0, "persistence": 1.0, "maintenance": 1.0},
        physiology_config=custom_phys,
    )
    custom_ledger.charge("observation", 0.75)  # ratio = 0.25 < 0.35 -> SEVERE!
    assert custom_ledger.pressure() is ResourcePressure.SEVERE


def test_homeostatic_repair_paths_share_physiology_config() -> None:
    from symbiont.core.homeostasis import HomeostaticController
    from symbiont.core.metabolism import MetabolicLedger

    # Custom repair cap of 0.10 per tick
    custom_phys = PhysiologyConfig(max_repair_per_tick=0.10)
    controller = HomeostaticController(integrity=0.5, config=custom_phys)
    metabolism = MetabolicLedger(
        capacity={"observation": 1.0, "cognition": 1.0, "persistence": 1.0, "maintenance": 1.0},
        physiology_config=custom_phys,
    )

    # 1. Regulate path: requested 0.50 repairable damage, but capped by max_repair_per_tick
    snapshot = controller.regulate(metabolism.pressure(), repairable_damage=0.50)
    assert controller.integrity == pytest.approx(0.60)  # 0.50 + 0.10

    # 2. repair_with_resources path: requested 0.50 repair, must also be capped by 0.10
    repaired = controller.repair_with_resources(metabolism, requested=0.50)
    assert repaired == pytest.approx(0.10)
    assert controller.integrity == pytest.approx(0.70)


def test_organism_runtime_propagates_single_physiology_config() -> None:
    from symbiont.core.runtime import OrganismRuntime

    custom_phys = PhysiologyConfig(
        max_repair_per_tick=0.12,
        aging_ticks=25,
        waste_ticks=12,
        dormant_metabolic_factor=0.20,
    )
    runtime = OrganismRuntime(physiology_config=custom_phys)

    # Single config reached all relevant subsystems
    assert runtime.physiology_config == custom_phys
    assert runtime.homeostasis.config == custom_phys
    assert runtime.metabolism.physiology_config == custom_phys
    assert runtime.degradation_queue.aging_ticks == 25
    assert runtime.degradation_queue.waste_ticks == 12

    # Effective configuration includes physiology
    eff = runtime.effective_configuration()
    assert eff["physiology"]["max_repair_per_tick"] == 0.12
    assert eff["physiology"]["aging_ticks"] == 25
    assert eff["physiology"]["waste_ticks"] == 12
    assert eff["physiology"]["dormant_metabolic_factor"] == 0.20


def test_organism_runtime_rejects_incompatible_subsystems() -> None:
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.core.homeostasis import HomeostaticController
    from symbiont.core.degradation import DegradationQueue
    from symbiont.core.metabolism import MetabolicLedger

    runtime_phys = PhysiologyConfig(max_repair_per_tick=0.10, aging_ticks=16, waste_ticks=8)

    # Incompatible homeostasis config
    with pytest.raises(ValueError, match="incompatible homeostasis config"):
        incompatible_homeostasis = HomeostaticController(config=PhysiologyConfig(max_repair_per_tick=0.20))
        OrganismRuntime(physiology_config=runtime_phys, homeostasis=incompatible_homeostasis)

    # Incompatible degradation queue ticks
    with pytest.raises(ValueError, match="incompatible degradation_queue ticks"):
        incompatible_degradation = DegradationQueue(aging_ticks=30, waste_ticks=8)
        OrganismRuntime(physiology_config=runtime_phys, degradation_queue=incompatible_degradation)

    # Incompatible metabolism config
    with pytest.raises(ValueError, match="incompatible metabolism physiology_config"):
        incompatible_metabolism = MetabolicLedger(physiology_config=PhysiologyConfig(ratio_severe=0.30))
        OrganismRuntime(physiology_config=runtime_phys, metabolism=incompatible_metabolism)


def test_runtime_fingerprint_from_live_runtime() -> None:
    from symbiont.core.runtime import OrganismRuntime

    runtime1 = OrganismRuntime(organism_id="symbiont-alpha", mutation_seed=42)
    runtime2 = OrganismRuntime(organism_id="symbiont-beta", mutation_seed=42)

    # Organism ID does NOT change configuration fingerprint
    fp1 = runtime1.runtime_fingerprint()
    fp2 = runtime2.runtime_fingerprint()
    assert fp1 == fp2

    # Behavior exploration change produces distinct fingerprint
    runtime_exp = OrganismRuntime(organism_id="symbiont-alpha", mutation_seed=42, behavior_exploration=0.75)
    assert runtime_exp.runtime_fingerprint() != fp1

    # Mutation seed change produces distinct fingerprint
    runtime_seed = OrganismRuntime(organism_id="symbiont-alpha", mutation_seed=999)
    assert runtime_seed.runtime_fingerprint() != fp1

    # Physiology config change produces distinct fingerprint
    runtime_phys = OrganismRuntime(
        organism_id="symbiont-alpha",
        mutation_seed=42,
        physiology_config=PhysiologyConfig(max_repair_per_tick=0.15),
    )
    assert runtime_phys.runtime_fingerprint() != fp1


def test_fingerprint_canonicalization_exactness() -> None:
    import hashlib
    import json
    from symbiont.core.fingerprint import _canonical_normalize

    # 1. Dicts with different insertion order yield identical JSON
    d1 = {"z": 1, "a": 2, "m": {"b": 3, "a": 4}}
    d2 = {"a": 2, "m": {"a": 4, "b": 3}, "z": 1}
    assert _canonical_normalize(d1) == _canonical_normalize(d2)

    # 2. Sets with different insertion order yield identical canonical lists
    s1 = {"orange", "apple", "banana"}
    s2 = {"banana", "orange", "apple"}
    assert _canonical_normalize(s1) == _canonical_normalize(s2)

    # 3. Floats that are distinct must never collapse due to arbitrary rounding
    f1 = 1.0
    f2 = 1.0 + 1e-15
    assert f1 != f2
    norm1 = _canonical_normalize(f1)
    norm2 = _canonical_normalize(f2)
    assert norm1 != norm2
    h1 = hashlib.sha256(json.dumps(norm1).encode()).hexdigest()
    h2 = hashlib.sha256(json.dumps(norm2).encode()).hexdigest()
    assert h1 != h2

    # 4. Tuples / lists preserve sequence order (different order -> different hash)
    l1 = [1, 2, 3]
    l2 = [3, 2, 1]
    assert _canonical_normalize(l1) != _canonical_normalize(l2)


def test_epistemic_conventions_semantic_validation() -> None:
    # min_samples < 1
    with pytest.raises(ValueError, match="established_signal_min_samples"):
        EpistemicConventions(established_signal_min_samples=0)

    # bool passed instead of int
    with pytest.raises(ValueError, match="must be an integer, not bool"):
        EpistemicConventions(established_signal_min_samples=True)  # type: ignore[arg-type]

    # ewma_alpha <= 0 or > 1
    with pytest.raises(ValueError, match="ewma_alpha"):
        EpistemicConventions(ewma_alpha=0.0)
    with pytest.raises(ValueError, match="ewma_alpha"):
        EpistemicConventions(ewma_alpha=1.5)

    # class count <= 0
    with pytest.raises(ValueError, match="health_classes"):
        EpistemicConventions(health_classes=0)

    # recency_thresholds not strictly increasing
    with pytest.raises(ValueError, match="recency_thresholds must be strictly increasing"):
        EpistemicConventions(recency_thresholds=(10, 10, 40, 120))

    # maturity_thresholds count mismatch
    with pytest.raises(ValueError, match="maturity_thresholds count"):
        EpistemicConventions(maturity_classes=8, maturity_thresholds=(0, 1, 2))


def test_physiology_config_semantic_validation() -> None:
    # Ratios inverted
    with pytest.raises(ValueError, match="ratio_unrecoverable <= ratio_severe <= ratio_elevated"):
        PhysiologyConfig(ratio_severe=0.6, ratio_elevated=0.5)

    # max_repair_per_tick <= 0
    with pytest.raises(ValueError, match="max_repair_per_tick must be positive"):
        PhysiologyConfig(max_repair_per_tick=0.0)

    # aging_ticks < 1
    with pytest.raises(ValueError, match="aging_ticks must be an integer >= 1"):
        PhysiologyConfig(aging_ticks=0)

    # bool passed as float
    with pytest.raises(ValueError, match="must be numeric, not bool"):
        PhysiologyConfig(max_repair_per_tick=True)  # type: ignore[arg-type]


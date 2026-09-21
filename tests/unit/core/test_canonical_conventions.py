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

    # Default thresholds: ratio_severe = 0.2, ratio_elevated = 0.5.
    # Four 1.0 accounting capacities create a 4.0 physical-energy pool.
    default_ledger = MetabolicLedger(capacity={"observation": 1.0, "cognition": 1.0, "persistence": 1.0, "maintenance": 1.0})
    default_ledger.charge("observation", 3.0)  # physical energy 1.0 / 4.0 -> ratio 0.25
    assert default_ledger.pressure() is ResourcePressure.ELEVATED

    # Custom thresholds: ratio_severe = 0.35.
    custom_phys = PhysiologyConfig(ratio_severe=0.35)
    custom_ledger = MetabolicLedger(
        capacity={"observation": 1.0, "cognition": 1.0, "persistence": 1.0, "maintenance": 1.0},
        physiology_config=custom_phys,
    )
    custom_ledger.charge("observation", 3.0)  # physical ratio 0.25 < 0.35 -> SEVERE
    assert custom_ledger.pressure() is ResourcePressure.SEVERE


def test_constitutive_repair_uses_canonical_physiology_config() -> None:
    from symbiont.core.homeostasis import HomeostaticController
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.physiology import LivingBodyState

    custom_phys = PhysiologyConfig(
        max_repair_per_tick=0.10,
        autonomous_repair_rate=0.10,
    )
    state = LivingBodyState(structural_integrity=0.5)
    controller = HomeostaticController(
        config=custom_phys,
        body_state=state,
    )
    metabolism = MetabolicLedger(
        capacity={
            "observation": 1.0,
            "cognition": 1.0,
            "persistence": 1.0,
            "maintenance": 1.0,
        },
        physiology_config=custom_phys,
        body_state=state,
    )

    repaired = controller.constitutive_step(metabolism)

    assert repaired == pytest.approx(0.10)
    assert controller.integrity == pytest.approx(0.60)
    assert metabolism.snapshot().reserve["maintenance"] == pytest.approx(0.90)


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

    # Config change produces distinct fingerprint
    runtime_exp = OrganismRuntime(organism_id="symbiont-alpha", mutation_seed=42, conflict_z=3.5)
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


def test_runtime_fingerprint_software_version_and_build_identity() -> None:
    from symbiont.core.runtime import OrganismRuntime

    runtime = OrganismRuntime(organism_id="symbiont-v-test", mutation_seed=42)
    fp1 = runtime.runtime_fingerprint(software_version="0.80.16")
    fp2 = runtime.runtime_fingerprint(software_version="0.80.17")
    assert fp1 != fp2

    fp_build1 = runtime.runtime_fingerprint(software_version="0.80.16", build_identity="commit-abc")
    fp_build2 = runtime.runtime_fingerprint(software_version="0.80.16", build_identity="commit-xyz")
    assert fp_build1 != fp_build2
    assert fp_build1 != fp1


def test_runtime_fingerprint_kernel_limits_completeness() -> None:
    from dataclasses import asdict
    from symbiont.cognition.limits import KernelLimits
    from symbiont.core.runtime import OrganismRuntime

    limits_default = KernelLimits()
    runtime = OrganismRuntime(organism_id="symbiont-limits-test", kernel_limits=limits_default)
    config = runtime.effective_configuration()

    assert "kernel_limits" in config
    assert config["kernel_limits"] == asdict(limits_default)

    fp_default = runtime.runtime_fingerprint()

    # Changing consolidation_interval_ticks modifies fingerprint
    limits_consolidation = KernelLimits(consolidation_interval_ticks=limits_default.consolidation_interval_ticks + 50)
    runtime_consolidation = OrganismRuntime(organism_id="symbiont-limits-test", kernel_limits=limits_consolidation)
    assert runtime_consolidation.runtime_fingerprint() != fp_default

    # Changing reacclimation_ticks modifies fingerprint
    limits_reacclimation = KernelLimits(reacclimation_ticks=limits_default.reacclimation_ticks + 10)
    runtime_reacclimation = OrganismRuntime(organism_id="symbiont-limits-test", kernel_limits=limits_reacclimation)
    assert runtime_reacclimation.runtime_fingerprint() != fp_default


def test_runtime_fingerprint_min_samples_and_conflict_z() -> None:
    from symbiont.core.runtime import OrganismRuntime

    runtime_base = OrganismRuntime(organism_id="symbiont-test", min_samples=5, conflict_z=2.0)
    fp_base = runtime_base.runtime_fingerprint()

    # Custom min_samples
    runtime_min = OrganismRuntime(organism_id="symbiont-test", min_samples=8, conflict_z=2.0)
    assert runtime_min.min_samples == 8
    assert runtime_min.effective_configuration()["min_samples"] == 8
    assert runtime_min.runtime_fingerprint() != fp_base

    # Custom conflict_z
    runtime_z = OrganismRuntime(organism_id="symbiont-test", min_samples=5, conflict_z=3.5)
    assert runtime_z.conflict_z == 3.5
    assert runtime_z.effective_configuration()["conflict_z"] == 3.5
    assert runtime_z.runtime_fingerprint() != fp_base


def test_runtime_fingerprint_excludes_learned_trajectory_state() -> None:
    from symbiont.core.runtime import OrganismRuntime

    runtime = OrganismRuntime(organism_id="symbiont-trajectory", mutation_seed=123)
    fp_before = runtime.runtime_fingerprint()

    # Run a tick cycle
    runtime.tick()

    fp_after = runtime.runtime_fingerprint()
    assert fp_after == fp_before


def test_multi_subsystem_physiology_resolution_contradiction() -> None:
    from symbiont.core.homeostasis import HomeostaticController
    from symbiont.core.metabolism import MetabolicLedger
    from symbiont.core.degradation import DegradationQueue
    from symbiont.core.runtime import OrganismRuntime

    phys1 = PhysiologyConfig(ratio_severe=0.25)
    phys2 = PhysiologyConfig(ratio_severe=0.35)

    homeo = HomeostaticController(config=phys1)
    meta = MetabolicLedger(physiology_config=phys2)

    with pytest.raises(ValueError, match="contradictory physiology configs in prebuilt subsystems"):
        OrganismRuntime(homeostasis=homeo, metabolism=meta)

    # Incompatible degradation queue with prebuilt subsystem
    incompat_deg = DegradationQueue(aging_ticks=99, waste_ticks=8)
    with pytest.raises(ValueError, match="incompatible degradation_queue ticks with subsystem physiology config"):
        OrganismRuntime(homeostasis=homeo, degradation_queue=incompat_deg)


def test_checkpoint_physiology_fail_closed_and_migration() -> None:
    from symbiont.host.checkpoint import CheckpointError
    from symbiont.core.runtime import OrganismRuntime

    runtime = OrganismRuntime(organism_id="symbiont-ckpt-test", min_samples=7, conflict_z=2.75)
    ckpt = runtime.checkpoint()

    # 1. Successful checkpoint restore preserving min_samples and conflict_z
    restored = OrganismRuntime.from_checkpoint(ckpt)
    assert restored.min_samples == 7
    assert restored.conflict_z == 2.75
    assert restored.runtime_fingerprint() == runtime.runtime_fingerprint()

    # 2. Corrupted physiology config raises CheckpointError (fail closed)
    corrupted_ckpt = dict(ckpt)
    corrupted_ckpt["effective_config"] = dict(ckpt["effective_config"])
    corrupted_ckpt["effective_config"]["physiology"] = "not-a-valid-dict"
    with pytest.raises(CheckpointError, match="invalid physiology config"):
        OrganismRuntime.from_checkpoint(corrupted_ckpt)

    # Invalid physiology numbers (e.g., negative or inverted ratios)
    invalid_nums_ckpt = dict(ckpt)
    invalid_nums_ckpt["effective_config"] = dict(ckpt["effective_config"])
    invalid_nums_ckpt["effective_config"]["physiology"] = {
        **ckpt["effective_config"]["physiology"],
        "ratio_severe": 0.9,
        "ratio_elevated": 0.1,  # inverted
    }
    with pytest.raises(CheckpointError, match="invalid physiology config"):
        OrganismRuntime.from_checkpoint(invalid_nums_ckpt)

    # 3. Historical checkpoint migration: absent effective_config["physiology"]
    # but valid degradation queue ticks
    historical_ckpt = dict(ckpt)
    historical_ckpt["effective_config"] = dict(ckpt["effective_config"])
    historical_ckpt["effective_config"].pop("physiology", None)
    historical_ckpt["degradation"] = {
        "schema_version": 1,
        "max_items": 64,
        "aging_ticks": 44,
        "waste_ticks": 12,
        "excreted_units": 0,
        "items": [],
    }
    restored_hist = OrganismRuntime.from_checkpoint(historical_ckpt)
    assert restored_hist.physiology_config.aging_ticks == 44
    assert restored_hist.physiology_config.waste_ticks == 12


def test_epistemic_conventions_hardened_bijection() -> None:
    # Recency thresholds count must equal len(RecencyClass) - 1
    with pytest.raises(ValueError, match="recency_thresholds count"):
        EpistemicConventions(recency_thresholds=(10, 30))  # too short

    with pytest.raises(ValueError, match="recency_thresholds count"):
        EpistemicConventions(recency_thresholds=(10, 30, 60, 100, 200))  # too long

    # Duplicate recency class
    duplicate_idle = (
        (RecencyClass.CURRENT, 0),
        (RecencyClass.SHORT_IDLE, 10),
        (RecencyClass.IDLE, 30),
        (RecencyClass.CURRENT, 60),  # duplicate
        (RecencyClass.DORMANT, 120),
    )
    with pytest.raises(ValueError, match="duplicate RecencyClass"):
        EpistemicConventions(recency_representative_idle_ticks=duplicate_idle)

    # Missing recency class
    missing_idle = (
        (RecencyClass.CURRENT, 0),
        (RecencyClass.SHORT_IDLE, 10),
        (RecencyClass.IDLE, 30),
        (RecencyClass.LONG_IDLE, 60),
        # missing DORMANT
    )
    with pytest.raises(ValueError, match="bijection covering all RecencyClass variants"):
        EpistemicConventions(recency_representative_idle_ticks=missing_idle)


def test_canonical_normalize_type_safety() -> None:
    from symbiont.core.fingerprint import _canonical_normalize

    # Unsupported type raises TypeError
    class CustomObject:
        pass

    with pytest.raises(TypeError, match="Cannot canonically normalize object"):
        _canonical_normalize(CustomObject())

    # Non-string dictionary keys raise TypeError
    with pytest.raises(TypeError, match="Dictionary keys in configuration fingerprint must be strings"):
        _canonical_normalize({123: "numeric key"})

    # Exact byte encoding as hex
    assert _canonical_normalize(b"symbiont") == "73796d62696f6e74"


def test_fingerprint_schema_version_is_v5() -> None:
    assert FINGERPRINT_SCHEMA_VERSION == 5


def test_prebuilt_subsystems_min_samples_resolution() -> None:
    from symbiont.host.acclimation import HostAcclimation
    from symbiont.host.rhythms import RhythmModel
    from symbiont.core.runtime import OrganismRuntime

    # 1. acclimation=7 + rhythm=7 -> accepted and fingerprint reflects 7
    acc7 = HostAcclimation(min_samples=7)
    rhythm7 = RhythmModel(min_samples=7)
    runtime7 = OrganismRuntime(organism_id="symbiont-7", acclimation=acc7, rhythm_model=rhythm7)
    assert runtime7.min_samples == 7
    assert runtime7.acclimation._min_samples == 7
    assert runtime7.rhythm_model._min_samples == 7
    assert runtime7.effective_configuration()["min_samples"] == 7

    runtime_def = OrganismRuntime(organism_id="symbiont-7", min_samples=5)
    assert runtime7.runtime_fingerprint() != runtime_def.runtime_fingerprint()

    # 2. acclimation=7 + rhythm=8 -> rejected with ValueError
    acc7 = HostAcclimation(min_samples=7)
    rhythm8 = RhythmModel(min_samples=8)
    with pytest.raises(ValueError, match="contradictory min_samples in prebuilt subsystems"):
        OrganismRuntime(acclimation=acc7, rhythm_model=rhythm8)

    # 3. solo rhythm=7 -> acclimation created by runtime uses 7
    rhythm_only = RhythmModel(min_samples=7)
    runtime_rhythm_only = OrganismRuntime(organism_id="symbiont-rhythm-7", rhythm_model=rhythm_only)
    assert runtime_rhythm_only.min_samples == 7
    assert runtime_rhythm_only.acclimation._min_samples == 7
    assert runtime_rhythm_only.rhythm_model._min_samples == 7
    assert runtime_rhythm_only.effective_configuration()["min_samples"] == 7

    # 4. Checkpoint restore preserves min_samples across subsystems
    ckpt = runtime7.checkpoint()
    restored = OrganismRuntime.from_checkpoint(ckpt)
    assert restored.min_samples == 7
    assert restored.acclimation._min_samples == 7
    assert restored.rhythm_model._min_samples == 7
    assert restored.runtime_fingerprint() == runtime7.runtime_fingerprint()





def test_sensory_capacity_is_constitutional_but_acquired_phenotype_is_not() -> None:
    from symbiont.core.runtime import OrganismRuntime

    legacy = OrganismRuntime(organism_id="sensory-fingerprint")
    adaptive = OrganismRuntime(organism_id="sensory-fingerprint", sensory_plasticity=True)
    assert legacy.runtime_fingerprint() != adaptive.runtime_fingerprint()

    before = adaptive.runtime_fingerprint()
    adaptive.tick()
    assert adaptive.runtime_fingerprint() == before


def test_checkpoint_rejects_contradictory_sensory_constitution() -> None:
    from symbiont.core.runtime import OrganismRuntime
    from symbiont.host.checkpoint import CheckpointError

    runtime = OrganismRuntime(
        organism_id="sensory-constitution-check",
        sensory_plasticity=True,
    )
    checkpoint = runtime.checkpoint()
    checkpoint["effective_config"] = dict(checkpoint["effective_config"])
    checkpoint["effective_config"]["sensory_plasticity"] = False

    with pytest.raises(CheckpointError, match="sensory constitution contradicts"):
        OrganismRuntime.from_checkpoint(checkpoint)

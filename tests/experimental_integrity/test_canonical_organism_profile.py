"""ADR-0062: one organism profile, and no launcher deviates from it silently.

The constructors must produce exactly the canonical profile, the register must
name every governed option, and any non-study module that sets a governed option
explicitly must be declared here. Study arms may deviate, but only as a declared
intervention of their protocol.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from symbiont.core.domains.intention import IntentionPolicy
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.organism_profile import (
    CANONICAL,
    GOVERNED_OPTIONS,
    HISTORICAL_V0,
    PROFILES,
    SYMBOL_SEED_SHARED,
)
from symbiont.modeling.runtime import ModeledOrganismRuntime

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "docs" / "design" / "core" / "canonical-organism-profile-v1.md"

# Modules outside ``studies/`` that set a governed option explicitly. Each entry is
# a divergence still to be removed by convergence on the canonical profile; adding
# one requires a register entry, removing one only requires deleting it here.
DECLARED_DEVIATIONS: dict[str, set[str]] = {
    "src/symbiont_lab/cli/observed_resident.py": {
        "bootstrap_semantic_senses",
        "discover_senses",
        "interoception_enabled",
        "sensory_plasticity",
    },
    "src/symbiont_lab/cli/organism.py": {
        "bootstrap_semantic_senses",
        "discover_senses",
        "interoception_enabled",
        "sensory_plasticity",
    },
    "src/symbiont_lab/experiments/runner.py": {"factorized_effects"},
    "src/symbiont_lab/integration/integrated_habitat.py": {
        "bootstrap_semantic_senses",
        "discover_senses",
        "interoception_mode",
        "symbol_policy_seed",
    },
    "src/symbiont_lab/physics3d/cli.py": {"ancestry_training", "factorized_effects"},
    "src/symbiont_lab/physics3d/equivalence.py": {"factorized_effects"},
    "src/symbiont_lab/physics3d/runtime.py": {
        "auto_promote_predictors",
        "bootstrap_semantic_senses",
        "discover_senses",
        "interoception_mode",
        "sensory_plasticity",
    },
    "src/symbiont_lab/world/adapter.py": {
        "bootstrap_semantic_senses",
        "discover_senses",
        "interoception_mode",
        "sensory_plasticity",
    },
    "src/symbiont_lab/world/cli_view.py": {"interoception_mode"},
    "src/symbiont_lab/world/persistence.py": {"discover_senses", "sensory_plasticity"},
    "src/symbiont_lab/world/population.py": {"discover_senses", "sensory_plasticity"},
    "src/symbiont_lab/world/runtime.py": {"discover_senses", "sensory_plasticity"},
}
# Plumbing that forwards a caller's or a parent's own configuration unchanged.
FORWARDERS = {
    "src/symbiont/core/orchestration/runtime.py",
    "src/symbiont/core/organism_profile.py",
    "src/symbiont_lab/reproduction/runtime.py",
}


def _explicit_options(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            found |= {kw.arg for kw in node.keywords if kw.arg in GOVERNED_OPTIONS}
        # Launchers also assemble keyword dictionaries: {"discover_senses": True}.
        if isinstance(node, ast.Dict):
            found |= {
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and key.value in GOVERNED_OPTIONS
            }
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            key = node.slice
            if isinstance(key, ast.Constant) and key.value in GOVERNED_OPTIONS:
                found.add(key.value)
    return found


def _scan() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in sorted((ROOT / "src").rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        if "/studies/" in relative or relative in FORWARDERS:
            continue
        options = _explicit_options(path)
        if options:
            found[relative] = options
    return found


def test_constructors_produce_the_historical_profile() -> None:
    runtime = inspect.signature(OrganismRuntime.__init__).parameters
    for option in (
        "discover_senses",
        "bootstrap_semantic_senses",
        "sensory_plasticity",
        "auto_promote_predictors",
        "factorized_effects",
    ):
        assert runtime[option].default == getattr(HISTORICAL_V0, option), option
    assert runtime["interoception_enabled"].default is True
    assert runtime["interoception_mode"].default is None
    assert HISTORICAL_V0.interoception_mode == "enabled"
    modeled = inspect.signature(ModeledOrganismRuntime.__init__).parameters
    assert modeled["symbol_policy_seed"].default == 0
    assert HISTORICAL_V0.symbol_seed_policy == SYMBOL_SEED_SHARED
    assert HISTORICAL_V0.intention_policy() == IntentionPolicy()


def test_canonical_profile_is_a_registered_version() -> None:
    assert PROFILES[CANONICAL.version] is CANONICAL
    assert PROFILES[HISTORICAL_V0.version] is HISTORICAL_V0


def test_no_launcher_deviates_without_declaring_it() -> None:
    found = _scan()
    undeclared = {
        path: sorted(options - DECLARED_DEVIATIONS.get(path, set()))
        for path, options in found.items()
        if options - DECLARED_DEVIATIONS.get(path, set())
    }
    assert not undeclared, f"governed options set outside the canonical profile: {undeclared}"
    stale = {
        path: sorted(options - found.get(path, set()))
        for path, options in DECLARED_DEVIATIONS.items()
        if options - found.get(path, set())
    }
    assert not stale, f"declared deviations that no longer exist, delete them: {stale}"


def test_register_names_every_governed_option_and_version() -> None:
    text = REGISTER.read_text(encoding="utf-8")
    for option in sorted(GOVERNED_OPTIONS - {"interoception_enabled", "symbol_policy_seed"}):
        assert f"`{option}`" in text, option
    assert "`symbol_seed_policy`" in text
    for version in PROFILES:
        assert f"`{version}`" in text, version

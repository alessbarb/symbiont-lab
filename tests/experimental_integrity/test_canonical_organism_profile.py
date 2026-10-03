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

from tests.checkpoints import edited
from tests.layout import source_files

from symbiont.core.domains.intention import IntentionPolicy
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.organism_profile import (
    CANONICAL,
    GOVERNED_OPTIONS,
    HISTORICAL_V0,
    PROFILES,
    SYMBOL_SEED_SHARED,
    symbol_seed_for,
)
from symbiont.modeling.runtime import ModeledOrganismRuntime

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "docs" / "design" / "core" / "canonical-organism-profile-v1.md"

# Modules outside ``studies/`` that set a governed option explicitly. Launchers may
# not deviate (ADR-0062); what remains is study-arm plumbing: code that forwards an
# intervention a protocol declares, never a launcher default.
DECLARED_DEVIATIONS: dict[str, set[str]] = {
    # Protocol ablation blocks (experiment.toml) select factorized effects as an arm.
    "lab/src/lab/experiments/runner.py": {"factorized_effects"},
    # Physics3D CLI flags used to run declared arms of the factorized-effects and
    # ancestry protocols; off unless a protocol passes them.
    "lab/src/lab/physics3d/cli.py": {"ancestry_training", "factorized_effects"},
    # The causal-equivalence harness scenario that exercises factorized state.
    "lab/src/lab/physics3d/equivalence.py": {"factorized_effects"},
}
# Plumbing that forwards a caller's or a parent's own configuration unchanged,
# and views that only report a configuration.
FORWARDERS = {
    "symbiont/src/symbiont/core/orchestration/runtime.py",
    "symbiont/src/symbiont/core/organism_profile.py",
    "lab/src/lab/reproduction/runtime.py",
    "lab/src/lab/world/cli_view.py",
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
    for path in source_files():
        relative = path.relative_to(ROOT).as_posix()
        if "/studies/" in relative or relative in FORWARDERS:
            continue
        options = _explicit_options(path)
        if options:
            found[relative] = options
    return found


def test_bare_organisms_are_born_with_the_canonical_profile() -> None:
    runtime = OrganismRuntime()
    assert runtime._profile_version == CANONICAL.version
    assert runtime._discover_senses is CANONICAL.discover_senses
    assert runtime._bootstrap_semantic_senses is CANONICAL.bootstrap_semantic_senses
    assert runtime.sensory_system.plasticity_enabled is CANONICAL.sensory_plasticity
    assert runtime._auto_promote_predictors is CANONICAL.auto_promote_predictors
    assert runtime._interoception_mode == CANONICAL.interoception_mode
    modeled = ModeledOrganismRuntime(organism_id="profile-probe")
    assert modeled._symbol_policy.seed == symbol_seed_for(CANONICAL, "profile-probe")
    # Governed constructor options have no value of their own.
    parameters = inspect.signature(OrganismRuntime.__init__).parameters
    for option in GOVERNED_OPTIONS & set(parameters):
        assert parameters[option].default is None, option


def test_restored_organisms_keep_the_profile_they_were_born_with() -> None:
    historical = OrganismRuntime(profile=HISTORICAL_V0)
    restored = OrganismRuntime.from_checkpoint(historical.checkpoint())
    assert restored._profile_version == HISTORICAL_V0.version
    assert restored._bootstrap_semantic_senses is True
    # A checkpoint written before profiles existed carries no profile_version.
    legacy = historical.checkpoint()
    del legacy["effective_config"]["profile_version"]
    restored_legacy = OrganismRuntime.from_checkpoint(edited(legacy))
    assert restored_legacy._profile_version == HISTORICAL_V0.version


def test_historical_profile_matches_the_old_constructor_defaults() -> None:
    assert HISTORICAL_V0.intention_policy() == IntentionPolicy()
    assert HISTORICAL_V0.symbol_seed_policy == SYMBOL_SEED_SHARED
    assert symbol_seed_for(HISTORICAL_V0, "any") == 0


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

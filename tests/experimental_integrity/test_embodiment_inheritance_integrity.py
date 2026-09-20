"""Epistemological and architectural integrity tests for embodiment and inheritance.

Enforces invariants from docs/design/herencia-evolutiva-multidimensional.md:
- Invariant A (§3, §62): Body morphology and semantic part names never enter cognition.
- Invariant B (§3, §62): Learned cognitive experience (BodySchema, AgencyModel, memory)
  never crosses the germline into offspring.
- Invariant C (§4, §63): Cognitive success or social agreement cannot manufacture physical reserve.
- §62: World and Lab cannot write to BodySchema or AgencyModel.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
import pytest

from symbiont.core.body import Body, create_standard_body
from symbiont.core.embodiment import implant
from symbiont.core.agency import AgencyModel, InferredBodySchema, InferredSelfModel
from symbiont.core.symbiont import Symbiont
from symbiont.core.germline import (
    EpigeneticMark,
    GermlineState,
    InheritancePackage,
    create_offspring_package,
    create_standard_genome,
)
from symbiont.core.individual import create_individual


def test_ast_body_morphology_and_names_never_enter_cognition():
    """Invariant A: Cognition must not contain body part names, morphology, or anatomy."""
    repo_root = Path(__file__).resolve().parents[2]
    cognition_dir = repo_root / "src" / "symbiont" / "cognition"

    forbidden_terms = {
        "pierna", "brazo", "rodilla", "limb", "quadruped", "wheeled",
        "morphology", "body_topology", "effector_kind", "receptor_kind",
    }

    violations: list[str] = []
    for py_file in cognition_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id.lower() in forbidden_terms:
                violations.append(f"{py_file.name} references forbidden anatomical term {node.id}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.lower() in forbidden_terms:
                    violations.append(f"{py_file.name} defines string constant {node.value}")

    assert not violations, "Invariant A violation in cognition:\n" + "\n".join(violations)


def test_symbiont_interface_is_strictly_opaque():
    """Invariant A: Symbiont.step() signature accepts only opaque inputs."""
    sig = inspect.signature(Symbiont.step)
    params = list(sig.parameters.keys())
    assert params == ["self", "opaque_inputs", "active_embodiment_id"]

    forbidden = {"body", "morphology", "receptors", "effectors", "anatomy"}
    for p in params:
        assert p not in forbidden


def test_world_and_lab_cannot_write_body_schema_or_agency_model():
    """Section 62: Neither World nor Lab may write or instantiate internal BodySchema/AgencyModel."""
    repo_root = Path(__file__).resolve().parents[2]
    world_src = repo_root / "src" / "symbiont_world"
    lab_src = repo_root / "src" / "symbiont_lab"

    forbidden_symbols = {"InferredBodySchema", "AgencyModel", "InferredSelfModel"}
    violations: list[str] = []

    for src_dir in (world_src, lab_src):
        for py_file in src_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name in forbidden_symbols:
                            violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
                elif isinstance(node, ast.Name):
                    if node.id in forbidden_symbols:
                        violations.append(f"{py_file.relative_to(repo_root)} references {node.id}")

    assert not violations, "Integrity violation: World/Lab accessing internal schema models:\n" + "\n".join(violations)


def test_learned_cognition_cannot_cross_reproduction():
    """Invariant B: Learned models (BodySchema, AgencyModel, memories) cannot cross into inheritance."""
    genome_a = create_standard_genome("parent_a")
    genome_b = create_standard_genome("parent_b")
    germline_a = GermlineState()

    package = create_offspring_package(
        parent_genome=genome_a,
        parent_germline=germline_a,
        second_parent_genome=genome_b,
        generation=1,
    )

    # Package must only contain genome, epigenetic_marks, parent_ids, generation
    assert hasattr(package, "genome")
    assert hasattr(package, "epigenetic_marks")
    assert not hasattr(package, "body_schema")
    assert not hasattr(package, "agency_model")
    assert not hasattr(package, "sensorimotor_model")
    assert not hasattr(package, "memory")

    # Attempting to construct InheritancePackage with cognitive payload raises error
    with pytest.raises(TypeError):
        InheritancePackage(
            genome=genome_a,
            epigenetic_marks=(),
            parent_ids=("p1",),
            generation=1,
            body_schema=InferredBodySchema(),  # type: ignore[call-arg]
        )


def test_cognitive_success_cannot_create_physical_reserve():
    """Invariant C: Cognitive activity or prediction accuracy alone cannot increase physical reserve."""
    ind = create_individual("sym_test", "body_test", num_receptors=3, num_effectors=2)
    initial_energy = ind.body.physiology.energy_reserve

    # Run for 20 ticks with pure observation and internal learning
    for _ in range(20):
        ind.step(external_stimuli={"rec.0": 0.5, "rec.1": 0.5})
        # Assert energy never increases without physical intake
        assert ind.body.physiology.energy_reserve <= initial_energy

    # Only explicit physical intake can increase reserve
    ind.body.physical_intake(0.3)
    assert ind.body.physiology.energy_reserve > 0.0

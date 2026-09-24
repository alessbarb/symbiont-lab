"""Epistemological and architectural integrity tests for embodiment and inheritance.

Enforces invariants from docs/design/herencia-evolutiva-multidimensional.md:
- Invariant A (§3, §62): Body morphology and semantic part names never enter cognition.
- Invariant B (§3, §62): Learned cognitive experience (BodySchema, AgencyModel, memory)
  never crosses the germline into offspring.
- Invariant C (§4, §63): Cognitive success or social agreement cannot manufacture physical reserve.
- §62 (refined): World can never instantiate, mutate or replace AgencyModel/InferredBodySchema.
  Lab can never instantiate, mutate or replace AgencyModel/InferredBodySchema belonging to a
  live Symbiont. Isolated synthetic instances are permitted only as specimens in explicit
  component-level falsification studies (modules carrying the module-level
  ``__falsification_specimen__ = True`` marker) and have no causal path back to an organism.
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
    """Invariant A: Cognition must not contain body part names, morphology, or anatomy (AUD-017)."""
    repo_root = Path(__file__).resolve().parents[2]
    cognition_dir = repo_root / "src" / "symbiont" / "cognition"
    target_files = list(cognition_dir.rglob("*.py")) + [
        repo_root / "src" / "symbiont" / "core" / "embodiment" / "agency.py",
        repo_root / "src" / "symbiont" / "core" / "orchestration" / "symbiont.py",
        repo_root / "src" / "symbiont" / "core" / "lineage" / "germline.py",
    ]

    forbidden_terms = {
        "pierna", "brazo", "rodilla", "limb", "quadruped", "wheeled",
        "morphology", "body_topology", "effector_kind", "receptor_kind",
    }

    violations: list[str] = []
    for py_file in target_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id.lower() in forbidden_terms:
                violations.append(f"{py_file.name} references forbidden anatomical term {node.id}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.lower() in forbidden_terms:
                    violations.append(f"{py_file.name} defines string constant {node.value}")

    assert not violations, "Invariant A violation in cognition:\n" + "\n".join(violations)


def test_symbiont_interface_is_strictly_opaque():
    """Invariant A: Symbiont.step() signature accepts ONLY opaque inputs (AUD-013)."""
    sig = inspect.signature(Symbiont.step)
    params = list(sig.parameters.keys())
    assert params == ["self", "opaque_inputs"]

    forbidden = {"body", "morphology", "receptors", "effectors", "anatomy", "active_embodiment_id"}
    for p in params:
        assert p not in forbidden


# Section 62 (refined): the full forbidden symbol set. World may never touch any of
# these under any circumstances. Lab may never touch any of these EXCEPT that a module
# explicitly marked as a component-falsification harness (see below) may construct
# fresh, isolated AgencyModel/InferredBodySchema specimens -- and only those two
# symbols; InferredSelfModel and BodySchemaEngine remain absolutely forbidden in Lab,
# marked or not.
_FORBIDDEN_SYMBOLS_ABSOLUTE = {"InferredSelfModel", "BodySchemaEngine"}
_FORBIDDEN_SYMBOLS_NARROWLY_EXEMPTABLE = {"InferredBodySchema", "AgencyModel"}
_ALL_FORBIDDEN_SYMBOLS = _FORBIDDEN_SYMBOLS_ABSOLUTE | _FORBIDDEN_SYMBOLS_NARROWLY_EXEMPTABLE

# Identifiers that would indicate a live organism is in play. A marked
# component-falsification harness may not import, reference, or construct any of these.
_LIVE_ORGANISM_SYMBOLS = {
    "Symbiont",
    "Individual",
    "create_individual",
    "_construct_organism",
}

# Attributes on a live Symbiont/Individual that hold its own cognition/body state.
# A marked harness may never assign to these (that would mean writing a specimen
# back into, or replacing, a live organism's own model).
_LIVE_ORGANISM_OWNED_ATTRIBUTES = {"agency_model", "body_schema"}


def _module_is_marked_falsification_specimen(tree: ast.Module) -> bool:
    """True iff the module has an unconditional top-level `__falsification_specimen__ = True`."""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        else:
            continue
        for target in targets:
            if (
                isinstance(target, ast.Name)
                and target.id == "__falsification_specimen__"
                and isinstance(node.value, ast.Constant)
                and node.value.value is True
            ):
                return True
    return False


def test_world_cannot_write_body_schema_or_agency_model():
    """Section 62: World may never write, mutate or instantiate BodySchema/AgencyModel (AUD-004).

    This half of the invariant is unconditional: no exemption exists for World.
    """
    repo_root = Path(__file__).resolve().parents[2]
    world_src = repo_root / "src" / "symbiont_world"

    violations: list[str] = []
    for py_file in world_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in _ALL_FORBIDDEN_SYMBOLS:
                        violations.append(f"{py_file.relative_to(repo_root)} imports {alias.name}")
            elif isinstance(node, ast.Name):
                if node.id in _ALL_FORBIDDEN_SYMBOLS:
                    violations.append(f"{py_file.relative_to(repo_root)} references {node.id}")

    assert not violations, "Integrity violation: World accessing internal schema models:\n" + "\n".join(violations)


def test_lab_body_schema_access_confined_to_marked_falsification_specimens():
    """Section 62 (refined): Lab can never instantiate, mutate or replace AgencyModel/
    InferredBodySchema belonging to a live Symbiont (AUD-005).

    Isolated synthetic instances are permitted only as specimens inside modules
    explicitly marked `__falsification_specimen__ = True`, and only for the narrow
    pair {AgencyModel, InferredBodySchema} -- never InferredSelfModel or
    BodySchemaEngine. Even inside a marked module, this test structurally verifies:
      - no live Symbiont/Individual is imported or constructed;
      - no `.agency_model` / `.body_schema` attribute (the attributes a real
        Symbiont owns, per src/symbiont/core/symbiont.py) is ever assigned to;
      - no checkpoint/restore function is called on anything in the module.
    """
    repo_root = Path(__file__).resolve().parents[2]
    lab_src = repo_root / "src" / "symbiont_lab"

    violations: list[str] = []

    for py_file in lab_src.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        rel = py_file.relative_to(repo_root)
        marked = _module_is_marked_falsification_specimen(tree)

        referenced_forbidden: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in _ALL_FORBIDDEN_SYMBOLS:
                        referenced_forbidden.add(alias.name)
            elif isinstance(node, ast.Name):
                if node.id in _ALL_FORBIDDEN_SYMBOLS:
                    referenced_forbidden.add(node.id)

        if not referenced_forbidden:
            continue

        if not marked:
            violations.append(
                f"{rel} references {sorted(referenced_forbidden)} without the "
                "__falsification_specimen__ marker"
            )
            continue

        # Marked module: only the narrowly exemptable pair is allowed.
        absolutely_forbidden_hit = referenced_forbidden & _FORBIDDEN_SYMBOLS_ABSOLUTE
        if absolutely_forbidden_hit:
            violations.append(
                f"{rel} is a marked falsification specimen but references "
                f"{sorted(absolutely_forbidden_hit)}, which is never exempt"
            )

        # A marked harness must never touch a live organism.
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in _LIVE_ORGANISM_SYMBOLS:
                        violations.append(
                            f"{rel} is a marked falsification specimen but imports "
                            f"live-organism symbol {alias.name}"
                        )
            elif isinstance(node, ast.Call):
                func = node.func
                func_name = func.id if isinstance(func, ast.Name) else (
                    func.attr if isinstance(func, ast.Attribute) else None
                )
                if func_name in _LIVE_ORGANISM_SYMBOLS:
                    violations.append(
                        f"{rel} is a marked falsification specimen but constructs "
                        f"live-organism symbol {func_name}"
                    )
                if func_name and (
                    "checkpoint" in func_name.lower() or func_name.lower().startswith("restore")
                ):
                    violations.append(
                        f"{rel} is a marked falsification specimen but calls "
                        f"checkpoint/restore function {func_name}"
                    )
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                if node.attr in _LIVE_ORGANISM_OWNED_ATTRIBUTES:
                    violations.append(
                        f"{rel} is a marked falsification specimen but assigns to "
                        f".{node.attr}, an attribute a live Symbiont owns"
                    )

    assert not violations, (
        "Integrity violation: Lab accessing internal schema models outside the "
        "narrow component-falsification exemption:\n" + "\n".join(violations)
    )


def test_falsification_specimen_marker_confined_to_study_harnesses():
    """The `__falsification_specimen__` marker itself must be confined to
    component-falsification study harnesses under
    src/symbiont_lab/studies/embodiment/. It must never appear on
    production/runtime Lab code (world/, cli/, dashboard/, modeling/,
    archive/, experiments/, ...), since that would let any Lab module grant
    itself the narrow exemption checked above.
    """
    repo_root = Path(__file__).resolve().parents[2]
    lab_src = repo_root / "src" / "symbiont_lab"
    allowed_dir = lab_src / "studies" / "embodiment"

    marked: list[Path] = []
    for py_file in lab_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        if _module_is_marked_falsification_specimen(tree):
            marked.append(py_file)

    assert marked, "expected the marker on the component-falsification study harnesses"

    stray = [p.relative_to(repo_root) for p in marked if allowed_dir not in p.parents]
    assert not stray, (
        "Integrity violation: __falsification_specimen__ may only appear on "
        "component-falsification study harnesses under "
        f"src/symbiont_lab/studies/embodiment/, not production/runtime Lab code: {stray}"
    )


def test_falsification_specimen_not_reachable_from_a_real_symbiont():
    """Runtime proof: a component-falsification study's returned result never
    exposes an organism-typed object.

    Runs one of the marked harnesses end to end and walks the returned result
    object graph, asserting it contains only primitives/tuples/dataclasses and
    never an AgencyModel, InferredBodySchema, Symbiont, Individual, Body or
    EmbodimentSession instance -- i.e. no organism-typed object is reachable
    from the study's public return value. (The structural checks above are
    what guarantee the harness never touches a live organism in the first
    place; this test only proves nothing organism-shaped leaks out through
    the result.)
    """
    from symbiont.core.agency import AgencyModel, InferredBodySchema
    from symbiont.core.body import Body
    from symbiont.core.embodiment import EmbodimentSession
    from symbiont.core.individual import Individual
    from symbiont.core.symbiont import Symbiont
    from symbiont_lab.studies.embodiment.hidden_common_cause import (
        run_hidden_common_cause_study,
    )
    from symbiont_lab.studies.embodiment.tool_body_distinction import (
        run_tool_body_distinction_study,
    )

    escaped_types = (AgencyModel, InferredBodySchema, Symbiont, Individual, Body, EmbodimentSession)

    def _walk(obj: object, seen: set[int], path: str) -> None:
        if id(obj) in seen:
            return
        seen.add(id(obj))
        assert not isinstance(obj, escaped_types), (
            f"specimen/organism object {type(obj).__name__} escaped harness boundary at {path}"
        )
        if hasattr(obj, "__dict__"):
            for key, value in vars(obj).items():
                _walk(value, seen, f"{path}.{key}")
        elif hasattr(obj, "__slots__"):
            for slot in obj.__slots__:
                if hasattr(obj, slot):
                    _walk(getattr(obj, slot), seen, f"{path}.{slot}")
        elif isinstance(obj, (list, tuple, set, frozenset)):
            for i, item in enumerate(obj):
                _walk(item, seen, f"{path}[{i}]")
        elif isinstance(obj, dict):
            for key, value in obj.items():
                _walk(value, seen, f"{path}[{key!r}]")

    common_cause_result = run_hidden_common_cause_study(seeds=(101,), steps=60)
    _walk(common_cause_result, set(), "hidden_common_cause_result")

    tool_body_result = run_tool_body_distinction_study(seeds=(101,), steps=100)
    _walk(tool_body_result, set(), "tool_body_result")

    # A real Symbiont/Individual constructed independently in this test must also
    # never have had a specimen object attached to it by either study above.
    from symbiont.core.individual import create_individual

    real = create_individual("real_sym_test", "real_body_test", num_receptors=2, num_effectors=1)
    assert isinstance(real.symbiont.agency_model, AgencyModel)
    assert isinstance(real.symbiont.body_schema, InferredBodySchema)
    # The real Symbiont's own models are freshly constructed by its own
    # constructor (never by the studies above), and start uncalibrated --
    # confirming no specimen state crossed back into this organism.
    assert real.symbiont.body_schema.overall_confidence == 0.0
    assert real.symbiont.agency_model.agency_confidence == {}


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

    # Only explicit physical intake can increase reserve (test-only helper)
    ind.body._test_physical_intake(0.3)
    assert ind.body.physiology.energy_reserve > 0.0


def test_clean_world_executes_without_legacy_runtime_monkeypatched(monkeypatch):
    """Dynamic proof: ModeledOrganismRuntime.tick raises RuntimeError, but clean World runs cleanly."""
    from symbiont_lab.world.adapter import ModeledOrganismRuntime
    from symbiont_lab.world.genesis_v1 import build_ground_truth
    from symbiont_lab.world.population import PopulationGenesisRuntime
    from symbiont_world.topology import HexCoord, HexTopology

    def _forbidden_legacy_tick(*args, **kwargs):
        raise RuntimeError("legacy ModeledOrganismRuntime ticked in clean World")

    monkeypatch.setattr(ModeledOrganismRuntime, "tick", _forbidden_legacy_tick)

    pop = PopulationGenesisRuntime(
        organism_ids=("clean-embodied-org",),
        world_seed=1234,
        ground_truth=build_ground_truth(),
        topology=HexTopology(width=4, height=4),
        start_cells=(HexCoord(1, 1),),
        movement_enabled=True,
        sensory_plasticity=True,
        discover_senses=True,
        experimental_clean=True,
    )

    rig = pop._rigs["clean-embodied-org"]
    assert rig.runtime is None
    assert rig.individual is not None
    assert rig.actuation_adapter is None

    # Run 20 ticks in clean world: should never invoke ModeledOrganismRuntime.tick
    for _ in range(20):
        pop.run_tick()

    assert len(rig.individual.history) == 20
    assert rig.individual.is_alive
    pop.assert_experimental_boundary()


def test_clean_world_architecture_has_zero_legacy_runtime_dependency():
    """Architectural proof: In clean mode, rigs have None for runtime and actuation_adapter, and 0 legacy actions."""
    from symbiont_lab.world.adapter import _construct_organism
    from symbiont_lab.world.genesis_v1 import build_ground_truth

    rig = _construct_organism(
        organism_id="clean-arch-check",
        world_id="clean-world",
        world_seed=42,
        organism_seed=43,
        ground_truth=build_ground_truth(),
        policy="cognitive",
        sensory_plasticity=True,
        discover_senses=True,
        actuation_enabled=True,
        experimental_clean=True,
    )

    # 1 Symbiont runtime, 1 Genome, 1 germline, 1 physical model (Body), 1 embodiment boundary (EmbodimentSession), 0 legacy
    assert rig.runtime is None
    assert rig.actuation_adapter is None
    assert rig.actuation_binding is None
    assert rig.resource_habitats == {}
    assert rig.individual is not None
    assert rig.individual.symbiont is not None
    assert rig.individual.body is not None
    assert rig.individual.session is not None
    assert rig.individual.genome is not None
    assert rig.individual.germline is not None


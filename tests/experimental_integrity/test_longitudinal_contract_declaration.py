"""No study may mix or leave unnamed the rule its subject follows on a Body change.

Two longitudinal contracts exist. Canonical re-embodiment keeps
embodiment-specific inference as knowledge; the clean-embodiment seed restarts
it. A module that builds a subject declares which one it uses, the run manifest
records it, and no module may build subjects under both.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from symbiont.core.orchestration.clean_embodiment_seed import CleanEmbodimentSeed
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.continuity import LongitudinalContract
from symbiont_lab.experiments.manifest import RunManifest
from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.experiments.runner import longitudinal_contract_of, subject_architecture_of

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
REDUCED = {"CleanEmbodimentSeed", "Individual", "create_individual"}
CANONICAL = {"prepare_fresh_embodiment_checkpoint"}
# The package that defines the seed and re-exports it is not a study.
DEFINING = {
    SRC / "symbiont" / "core" / "__init__.py",
    SRC / "symbiont" / "core" / "orchestration" / "individual.py",
    SRC / "symbiont" / "core" / "orchestration" / "clean_embodiment_seed.py",
}


def _imported_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
    return names


def _users() -> list[tuple[Path, LongitudinalContract]]:
    found = []
    for path in sorted(SRC.rglob("*.py")):
        if path in DEFINING:
            continue
        names = _imported_names(path)
        reduced, canonical = bool(names & REDUCED), bool(names & CANONICAL)
        assert not (reduced and canonical), f"{path} builds subjects under both contracts"
        if reduced:
            found.append((path, LongitudinalContract.REDUCED_SEED_TRANSPLANT))
        elif canonical:
            found.append((path, LongitudinalContract.CANONICAL_REEMBODIMENT))
    return found


def _module(path: Path):
    return importlib.import_module(".".join(path.relative_to(SRC).with_suffix("").parts))


def test_the_two_subject_classes_name_different_contracts() -> None:
    assert CleanEmbodimentSeed.LONGITUDINAL_CONTRACT is LongitudinalContract.REDUCED_SEED_TRANSPLANT
    assert OrganismRuntime.LONGITUDINAL_CONTRACT is LongitudinalContract.CANONICAL_REEMBODIMENT
    assert not hasattr(importlib.import_module("symbiont.core"), "Symbiont")


def test_users_of_both_contracts_exist() -> None:
    contracts = {contract for _path, contract in _users()}
    assert contracts == set(LongitudinalContract)


@pytest.mark.parametrize(
    ("path", "contract"), _users(), ids=lambda value: getattr(value, "name", str(value))
)
def test_every_module_that_builds_a_subject_declares_its_contract(
    path: Path, contract: LongitudinalContract
) -> None:
    assert getattr(_module(path), "LONGITUDINAL_CONTRACT", None) is contract, path


@pytest.mark.parametrize(
    ("protocol", "expected"),
    [
        ("embodiment.label-invariance", LongitudinalContract.REDUCED_SEED_TRANSPLANT),
        ("embodiment.causal-revision-sequence", LongitudinalContract.REDUCED_SEED_TRANSPLANT),
        ("embodiment.heredity-leakage-challenge", LongitudinalContract.REDUCED_SEED_TRANSPLANT),
    ],
)
def test_the_run_manifest_records_the_contract_of_the_protocol(
    protocol: str, expected: LongitudinalContract
) -> None:
    assert longitudinal_contract_of(get_protocol(protocol)) == expected.value


def test_a_protocol_without_a_longitudinal_subject_records_none() -> None:
    assert longitudinal_contract_of(get_protocol("embodiment.yoked-external-causation")) is None


def test_subject_declarations_survive_a_manifest_round_trip(tmp_path: Path) -> None:
    manifest = RunManifest(
        run_id="r",
        experiment_id="e",
        protocol="p",
        protocol_version=1,
        started_at="",
        finished_at="",
        seed=1,
        world_digest="na",
        longitudinal_contract=LongitudinalContract.REDUCED_SEED_TRANSPLANT.value,
        subject_architecture="some-architecture",
    )

    loaded = RunManifest.load(manifest.save(tmp_path))

    assert loaded.longitudinal_contract == "reduced-seed-transplant-v1"
    assert loaded.subject_architecture == "some-architecture"


def test_a_protocol_module_can_declare_a_non_canonical_subject_architecture() -> None:
    def protocol() -> None:
        return None

    assert subject_architecture_of(protocol) is None
    module = __import__(__name__, fromlist=["x"])
    module.SUBJECT_ARCHITECTURE = "declared-here"
    try:
        assert subject_architecture_of(protocol) == "declared-here"
    finally:
        del module.SUBJECT_ARCHITECTURE
    protocol.SUBJECT_ARCHITECTURE = "declared-on-the-function"  # type: ignore[attr-defined]
    assert subject_architecture_of(protocol) == "declared-on-the-function"

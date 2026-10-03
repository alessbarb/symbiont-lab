"""Import boundaries of the five-domain architecture.

Symbiont, Embodiment, Modality and Environment are peer, self-contained
libraries: none imports another or the Lab. The Lab is the only composition
root and owns every adapter that knows more than one domain. One ratchet pins
debt inside the organism that predates the layout. See
migration/dependency-audit.md.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from tests.layout import ROOT, SOURCE_ROOTS

_spec = importlib.util.spec_from_file_location(
    "migration_depgraph", ROOT / "migration" / "tools" / "depgraph.py"
)
depgraph = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = depgraph
_spec.loader.exec_module(depgraph)

_, EDGES = depgraph.build(list(SOURCE_ROOTS))
RUNTIME_EDGES = [edge for edge in EDGES if edge["kind"] != "typing"]
HEAVY = ("<pybullet>", "<torch>", "<numpy>", "<PIL>")


def _edges(source: str, target: str) -> list[str]:
    return sorted(
        f"{Path(edge['file']).relative_to(ROOT)}:{edge['line']} {edge['src']} -> {edge['dst']}"
        for edge in RUNTIME_EDGES
        if depgraph.matches(edge["src_unit"], source)
        and (depgraph.matches(edge["dst_unit"], target) or edge["dst_unit"] == target)
    )


PEERS = ("symbiont", "embodiment", "modality", "environment")


@pytest.mark.parametrize(
    ("source", "target"),
    [
        # the four domains are peer libraries: none imports another, none imports the Lab
        *((source, target) for source in PEERS for target in (*PEERS, "lab") if source != target),
        # the organism imports no physics, tensor or imaging backend; the other three
        # libraries may use the external backends they declare
        *(("symbiont", heavy) for heavy in HEAVY),
    ],
)
def test_forbidden_domain_dependency(source: str, target: str) -> None:
    assert _edges(source, target) == []


def test_import_linter_contracts_hold() -> None:
    """The permanent invariants live in [tool.importlinter]; this keeps them in the test run."""
    import subprocess

    result = subprocess.run(
        [str(Path(sys.executable).with_name("lint-imports")), "--no-cache"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_source_roots_hold_exactly_their_domain_packages() -> None:
    packages = {
        root.parent.name: sorted(p.name for p in root.iterdir() if (p / "__init__.py").is_file())
        for root in SOURCE_ROOTS
    }
    assert packages == {
        "symbiont": ["symbiont"],
        "environment": ["environment"],
        "modality": ["modality"],
        "embodiment": ["embodiment"],
        "lab": ["lab"],
    }


def _importers(target_prefixes: tuple[str, ...], *, source: str, exclude: tuple[str, ...] = ()):
    return sorted(
        {
            (edge["src"], edge["dst"])
            for edge in RUNTIME_EDGES
            if depgraph.matches(edge["src_unit"], source)
            and not any(depgraph.matches(edge["src_unit"], unit) for unit in exclude)
            and any(depgraph.matches(edge["dst"], prefix) for prefix in target_prefixes)
        }
    )


def test_organism_core_reaches_concrete_host_modality_only_where_it_already_did() -> None:
    """Ratchet for symbiont -X-> concrete modality implementations (OI-3)."""
    assert _importers(("symbiont.host.providers",), source="symbiont.core") == [
        ("symbiont.core.domains.perception", "symbiont.host.providers.interoception"),
        ("symbiont.core.orchestration.runtime", "symbiont.host.providers.interoception"),
        ("symbiont.core.orchestration.runtime", "symbiont.host.providers.linux_surfaces"),
        ("symbiont.core.orchestration.runtime", "symbiont.host.providers.portable_surfaces"),
        ("symbiont.core.orchestration.runtime", "symbiont.host.providers.stdlib"),
        ("symbiont.core.orchestration.runtime", "symbiont.host.providers.stdlib_readings"),
    ]


def test_domain_distributions_declare_no_first_party_dependency() -> None:
    import tomllib

    names = {*PEERS, "lab"}
    for domain in PEERS:
        project = tomllib.loads((ROOT / domain / "pyproject.toml").read_text(encoding="utf-8"))
        declared = {
            dependency.split("[")[0].split(">")[0].split("=")[0].split("<")[0].strip()
            for dependency in project["project"]["dependencies"]
        }
        assert not declared & names, domain
    lab = tomllib.loads((ROOT / "lab" / "pyproject.toml").read_text(encoding="utf-8"))
    assert set(PEERS) <= set(lab["project"]["dependencies"])


def test_public_api_resolves_and_is_modality_free() -> None:
    from symbiont import api

    assert all(hasattr(api, name) for name in api.__all__)
    assert not {"VisionFrame", "LanguageToken", "HumanoidJoint", "PhysicsObservation"} & set(
        api.__all__
    )


def test_all_domains_match_authoritative_root_version() -> None:
    """The root pyproject.toml defines the authoritative workspace version.

    Every workspace member maintains an exact static PEP 621 copy so it remains
    independently buildable without a parent workspace.
    """
    from scripts.governance.version import check_versions

    mismatches = check_versions(ROOT)
    assert mismatches == [], "Version mismatches detected:\n" + "\n".join(mismatches)

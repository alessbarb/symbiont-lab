"""Import boundaries of the five-domain architecture.

Symbiont (organism) / Embodiment / Modality / Environment / Lab. The hard rules
fail on any violation. The ratchets pin debt that already existed when the
layout was introduced: they fail when it grows, and when it shrinks they ask
for the baseline to be tightened. See migration/dependency-audit.md.
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


@pytest.mark.parametrize(
    ("source", "target"),
    [
        # the organism knows neither the Lab, the Environment nor the observer
        ("symbiont", "lab"),
        ("symbiont", "environment"),
        *(("symbiont", heavy) for heavy in HEAVY),
        # the Environment holds ground truth and knows no organism and no Lab
        ("environment", "symbiont"),
        ("environment", "lab"),
        *(("environment", heavy) for heavy in HEAVY),
        # a Modality is a signal channel: it knows no organism, body, world or Lab
        ("modality", "symbiont"),
        ("modality", "embodiment"),
        ("modality", "environment"),
        ("modality", "lab"),
        # an Embodiment couples; it never depends on the Lab or the observer
        ("embodiment", "lab"),
        # nothing below the Lab reaches the new domains from the organism side
        ("symbiont", "modality"),
        ("symbiont", "embodiment"),
        ("environment", "modality"),
        ("environment", "embodiment"),
    ],
)
def test_forbidden_domain_dependency(source: str, target: str) -> None:
    assert _edges(source, target) == []


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


def test_physics3d_reaches_cognition_internals_only_where_it_already_did() -> None:
    """Ratchet for environment/embodiment -X-> cognition internals (OI-4)."""
    internals = ("symbiont.cognition", "symbiont.core.cognition")
    assert _importers(internals, source="embodiment") + _importers(
        internals, source="lab.physics3d"
    ) == [
        ("embodiment.physics3d.apparatus", "symbiont.cognition.birth"),
        ("embodiment.physics3d.apparatus", "symbiont.cognition.limits"),
        ("lab.physics3d.runtime", "symbiont.cognition.generative"),
        ("lab.physics3d.runtime", "symbiont.cognition.limits"),
        ("lab.physics3d.runtime", "symbiont.cognition.types"),
    ]


def test_public_api_resolves_and_is_modality_free() -> None:
    from symbiont import api

    assert all(hasattr(api, name) for name in api.__all__)
    assert not {"VisionFrame", "LanguageToken", "HumanoidJoint", "PhysicsObservation"} & set(
        api.__all__
    )

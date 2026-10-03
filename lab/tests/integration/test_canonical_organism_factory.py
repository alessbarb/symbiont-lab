"""The Lab factory reproduces what the organism's constructor builds on its own."""

from __future__ import annotations

import pytest

from lab.integration.organism import canonical_host_sense_sources, create_canonical_organism
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.organism_profile import HISTORICAL_V0, V1

CASES = [
    pytest.param({}, id="canonical"),
    pytest.param({"profile": HISTORICAL_V0}, id="historical-v0"),
    pytest.param({"profile": V1}, id="v1"),
    pytest.param({"interoception_mode": "enabled", "discover_senses": True}, id="interoception"),
    pytest.param({"interoception_mode": "sham", "discover_senses": True}, id="sham"),
    pytest.param({"interoception_enabled": False, "discover_senses": True}, id="absent"),
    pytest.param({"discover_senses": False, "bootstrap_semantic_senses": True}, id="bootstrap"),
    pytest.param({"discover_senses": False, "bootstrap_semantic_senses": False}, id="no-senses"),
]


def _shape(runtime: OrganismRuntime) -> dict[str, object]:
    discovery = runtime._lifecycle._discovery
    return {
        "discovery": [type(provider).__name__ for provider in discovery._providers],
        "readings": [type(provider).__name__ for provider in runtime._reading_providers],
        "interoception": type(runtime._interoception_provider).__name__,
        "interoception_mode": runtime._interoception_mode,
        "host_sense_source": runtime._host_sense_source,
        "persist_replay_state": runtime._persist_replay_state,
        "capabilities": sorted(
            capability.capability_id for capability in discovery.discover().capabilities
        ),
    }


@pytest.mark.parametrize("options", CASES)
def test_factory_builds_the_same_organism_as_the_constructor(options) -> None:
    built_in = OrganismRuntime(organism_id="organism-under-test", **options)
    composed = create_canonical_organism(organism_id="organism-under-test", **options)
    assert _shape(composed) == _shape(built_in)
    assert composed.checkpoint(advance_lineage=False) == built_in.checkpoint(advance_lineage=False)


@pytest.mark.parametrize("system", ["Linux", "Darwin", "Windows", "Plan9"])
def test_platform_selection_matches_the_organism_rule(system: str) -> None:
    sources = canonical_host_sense_sources(
        discover_senses=True,
        bootstrap_semantic_senses=False,
        interoception_mode="enabled",
        system=system,
    )
    names = [type(provider).__name__ for provider in sources.discovery_providers]
    if system == "Linux":
        assert names == ["LinuxSurfaceProvider", "InteroceptionProvider"]
    elif system == "Plan9":
        assert names == [] and sources.availability == "unavailable"
    else:
        assert names == ["PortableSurfaceProvider", "InteroceptionProvider"]

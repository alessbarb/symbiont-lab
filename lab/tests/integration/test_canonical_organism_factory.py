"""The Lab composes the organism's sense sources; the organism resolves what it requires.

Each case compares the composed organism with the one the organism builds on its
own, for a fresh creation and for a restore.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from lab.integration.organism import canonical as factory_module
from lab.integration.organism import (
    canonical_host_sense_sources,
    create_canonical_organism,
    load_or_create_canonical_organism,
    restore_canonical_organism,
)
from symbiont.core.orchestration import sense_requirements as requirements_module
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.core.orchestration.sense_requirements import (
    SenseRequirements,
    resolve_restore_sense_requirements,
    resolve_sense_requirements,
)
from symbiont.core.organism_profile import HISTORICAL_V0, V1

# stdlib/discovery combinations, interoception on/sham/off, both profiles
CASES = [
    pytest.param({}, id="canonical"),
    pytest.param({"profile": HISTORICAL_V0}, id="historical-v0"),
    pytest.param({"profile": V1}, id="v1"),
    pytest.param({"interoception_mode": "enabled", "discover_senses": True}, id="interoception"),
    pytest.param({"interoception_mode": "sham", "discover_senses": True}, id="sham"),
    pytest.param({"interoception_enabled": False, "discover_senses": True}, id="absent"),
    pytest.param({"discover_senses": True, "bootstrap_semantic_senses": True}, id="both"),
    pytest.param({"discover_senses": False, "bootstrap_semantic_senses": True}, id="bootstrap"),
    pytest.param({"discover_senses": False, "bootstrap_semantic_senses": False}, id="no-senses"),
]
# what a restore may state differently from what the checkpoint recorded
OVERRIDES = [
    pytest.param({}, id="recorded-controls"),
    pytest.param({"discover_senses": False}, id="override-discovery-off"),
    pytest.param({"discover_senses": True, "interoception_mode": "enabled"}, id="override-on"),
    pytest.param({"bootstrap_semantic_senses": True}, id="override-bootstrap"),
    pytest.param({"interoception_enabled": False}, id="override-interoception-off"),
    pytest.param({"profile": V1}, id="override-profile"),
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


def _same(composed: OrganismRuntime, built_in: OrganismRuntime) -> None:
    assert _shape(composed) == _shape(built_in)
    assert composed.state_hash() == built_in.state_hash()
    assert composed.checkpoint(advance_lineage=False) == built_in.checkpoint(advance_lineage=False)


@pytest.mark.parametrize("options", CASES)
def test_fresh_creation_matches_the_constructor(options) -> None:
    _same(
        create_canonical_organism(organism_id="organism-under-test", **options),
        OrganismRuntime(organism_id="organism-under-test", **options),
    )


@pytest.mark.parametrize("overrides", OVERRIDES)
@pytest.mark.parametrize("options", CASES)
def test_restore_matches_the_organism_restore(options, overrides) -> None:
    payload = OrganismRuntime(organism_id="organism-under-test", **options).checkpoint()
    _same(
        restore_canonical_organism(payload, **overrides),
        OrganismRuntime.from_checkpoint(payload, **overrides),
    )


@pytest.mark.parametrize("options", CASES)
def test_restore_keeps_the_sources_the_organism_was_created_with(options) -> None:
    created = create_canonical_organism(organism_id="organism-under-test", **options)
    restored = restore_canonical_organism(created.checkpoint())
    assert _shape(restored) == _shape(created)


def test_load_or_create_creates_then_restores(tmp_path) -> None:
    path = tmp_path / "organism.json"
    created = load_or_create_canonical_organism(path, organism_id="organism-under-test")
    _same(created, OrganismRuntime(organism_id="organism-under-test"))
    created.save(path)
    _same(load_or_create_canonical_organism(path), OrganismRuntime.load_or_create(path))


@pytest.mark.parametrize("system", ["Linux", "Darwin", "Windows", "Plan9"])
@pytest.mark.parametrize("mode", ["enabled", "sham", "absent"])
def test_platform_and_interoception_selection(system: str, mode: str) -> None:
    sources = canonical_host_sense_sources(
        SenseRequirements(
            discover_senses=True, bootstrap_semantic_senses=True, interoception_mode=mode
        ),
        system=system,
    )
    names = [type(provider).__name__ for provider in sources.discovery_providers]
    host = {"Linux": "LinuxSurfaceProvider", "Plan9": None}.get(system, "PortableSurfaceProvider")
    interoception = {"enabled": "InteroceptionProvider", "sham": "ShamInteroceptionProvider"}.get(
        mode
    )
    expected = ["StandardLibraryProvider"]
    if host is not None:
        expected += [host] + ([interoception] if interoception else [])
    assert names == expected
    assert sources.availability == ("unavailable" if host is None else "available")
    assert type(sources.interoception_provider).__name__ == (
        interoception if host is not None and interoception else "NoneType"
    )


def test_requirements_are_resolved_by_the_organism_alone() -> None:
    """Pure: no provider, platform or Lab is known where requirements are resolved."""
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(inspect.getsource(requirements_module)))
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(ast.parse(inspect.getsource(requirements_module)))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not {name for name in imported if "providers" in name or name in {"platform", "lab"}}
    fresh = resolve_sense_requirements(profile=V1)
    assert fresh == SenseRequirements(True, False, "absent")
    payload = {"effective_config": {"profile_version": "v1", "discover_senses": False}}
    assert resolve_restore_sense_requirements(payload) == SenseRequirements(False, False, "absent")
    assert resolve_restore_sense_requirements(payload, discover_senses=True).discover_senses


def test_the_lab_does_not_interpret_checkpoint_controls() -> None:
    source = inspect.getsource(factory_module)
    assert "effective_config" not in source
    assert "profile_version" not in source
    assert "session_controls" not in source

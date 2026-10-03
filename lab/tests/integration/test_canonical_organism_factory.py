"""The Lab composes the organism's sense sources; the organism resolves what it requires.

Each case compares the composed organism with the one the organism builds on its
own, for a fresh creation and for a restore.
"""

from __future__ import annotations

import ast
import inspect
import platform

import pytest

from lab.integration.organism import canonical as factory_module
from lab.integration.organism import (
    canonical_host_sense_sources,
    create_canonical_organism,
    load_or_create_canonical_organism,
    load_required_canonical_organism,
    restore_canonical_organism,
    restore_canonical_resident,
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


def _name(provider: object) -> str:
    """The channel class, looking through the Lab's adapter."""
    return type(getattr(provider, "source", provider)).__name__


def _shape(runtime: OrganismRuntime) -> dict[str, object]:
    discovery = runtime._lifecycle._discovery
    return {
        "discovery": [_name(provider) for provider in discovery._providers],
        "readings": [_name(provider) for provider in runtime._reading_providers],
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


def _expected_sources(requirements: SenseRequirements) -> list[str]:
    """Provider classes, in order, that this platform's composition must attach."""
    names = ["StandardLibraryProvider"] if requirements.bootstrap_semantic_senses else []
    if requirements.discover_senses:
        names.append(
            "LinuxSurfaceProvider" if platform.system() == "Linux" else "PortableSurfaceProvider"
        )
        if requirements.interoception_mode != "absent":
            names.append(
                "ShamInteroceptionProvider"
                if requirements.interoception_mode == "sham"
                else "InteroceptionProvider"
            )
    return names


def _attached(runtime: OrganismRuntime, expected: list[str]) -> None:
    shape = _shape(runtime)
    assert shape["discovery"] == expected
    # the stdlib source discovers and reads through two classes
    assert shape["readings"] == [
        name.replace("StandardLibraryProvider", "StandardLibraryReadingProvider")
        for name in expected
    ]


# Equality with the organism that used to build its own sources is checked
# against the pre-migration tree by migration/tools/identity_check.py.
@pytest.mark.parametrize("options", CASES)
def test_fresh_creation_attaches_what_the_organism_requires(options) -> None:
    created = create_canonical_organism(organism_id="organism-under-test", **options)
    expected = _expected_sources(resolve_sense_requirements(**options))
    _attached(created, expected)


@pytest.mark.parametrize("options", CASES)
def test_the_organism_alone_attaches_no_host_source(options) -> None:
    alone = OrganismRuntime(organism_id="organism-under-test", **options)
    assert _shape(alone)["discovery"] == _shape(alone)["readings"] == []
    assert alone._interoception_provider is None
    assert alone._host_sense_source in {"unavailable", "not_requested"}


@pytest.mark.parametrize("overrides", OVERRIDES)
@pytest.mark.parametrize("options", CASES)
def test_restore_attaches_what_the_checkpoint_and_overrides_require(options, overrides) -> None:
    payload = create_canonical_organism(organism_id="organism-under-test", **options).checkpoint()
    restored = restore_canonical_organism(payload, **overrides)
    expected = _expected_sources(resolve_restore_sense_requirements(payload, **overrides))
    _attached(restored, expected)


@pytest.mark.parametrize("options", CASES)
def test_restore_keeps_the_sources_the_organism_was_created_with(options) -> None:
    created = create_canonical_organism(organism_id="organism-under-test", **options)
    restored = restore_canonical_organism(created.checkpoint(advance_lineage=False))
    # lineage records the restore; everything else is the same organism
    assert _shape(restored) == _shape(created)
    assert restored.state_hash() == created.state_hash()


def test_load_or_create_creates_then_restores(tmp_path) -> None:
    path = tmp_path / "organism.json"
    created = load_or_create_canonical_organism(path, organism_id="organism-under-test")
    _same(created, create_canonical_organism(organism_id="organism-under-test"))
    created.save(path)
    assert _shape(load_required_canonical_organism(path)) == _shape(created)


def test_required_load_fails_closed_when_checkpoint_is_missing(tmp_path) -> None:
    path = tmp_path / "expected-checkpoint.json"
    with pytest.raises(FileNotFoundError, match="required organism checkpoint"):
        load_required_canonical_organism(path)


@pytest.mark.parametrize("system", ["Linux", "Darwin", "Windows", "Plan9"])
@pytest.mark.parametrize("mode", ["enabled", "sham", "absent"])
def test_platform_and_interoception_selection(system: str, mode: str) -> None:
    sources = canonical_host_sense_sources(
        SenseRequirements(
            discover_senses=True, bootstrap_semantic_senses=True, interoception_mode=mode
        ),
        system=system,
    )
    names = [_name(provider) for provider in sources.discovery_providers]
    host = {"Linux": "LinuxSurfaceProvider", "Plan9": None}.get(system, "PortableSurfaceProvider")
    # interoception is the organism's own: the Lab supplies no provider for it,
    # only the host telemetry published alongside it
    assert names == ["StandardLibraryProvider"] + ([host] if host is not None else [])
    assert sources.availability == ("unavailable" if host is None else "available")
    assert _name(sources.process_telemetry) == (
        "NoneType" if host is None else "HostProcessTelemetry"
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


@pytest.mark.parametrize("overrides", OVERRIDES)
@pytest.mark.parametrize("options", CASES)
def test_resident_restore_with_adopted_cognition_attaches_the_same_sources(
    options, overrides
) -> None:
    # a genome-less checkpoint, so the restore goes down the adoption branch
    payload = create_canonical_organism(**options).checkpoint()
    assert payload["genome"] is None
    resident = restore_canonical_resident(payload, **overrides)
    assert resident.genome is not None
    assert _shape(resident) == _shape(restore_canonical_organism(payload, **overrides))


# The canonical organism senses macOS and Windows hosts too (ADR-0062, rule 8).
@pytest.mark.parametrize("system", ["Darwin", "Windows"])
def test_canonical_organism_senses_macos_and_windows_hosts(monkeypatch, system) -> None:
    monkeypatch.setattr(platform, "system", lambda: system)
    runtime = create_canonical_organism()
    assert runtime.effective_configuration()["host_sense_source"] == "available"
    assert "PortableSurfaceProvider" in _shape(runtime)["readings"]


def test_unknown_host_system_is_declared_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Plan9")
    runtime = create_canonical_organism()
    assert runtime.effective_configuration()["host_sense_source"] == "unavailable"


def test_a_resident_composed_by_the_lab_buds_a_child_with_the_same_composition(tmp_path) -> None:
    import json

    from symbiont.core.host.local_habitat import LocalHabitat
    from symbiont.core.orchestration.resident import ResidentOrganism
    from symbiont.core.social.capsule import CapsuleKeyPair

    def embryo(create_child) -> dict:
        habitat = LocalHabitat(tmp_path / create_child.__name__)
        parent = create_canonical_organism(min_samples=1)
        parent.tick()
        ResidentOrganism(
            parent,
            state_file=tmp_path / "resident.json",
            habitat=habitat,
            keypair=CapsuleKeyPair.generate(),
            create_child=create_child,
        )._social_and_reproductive_step(20)
        (path,) = habitat.incubator_dir.glob("*.json")
        return json.loads(path.read_text())

    composed = embryo(create_canonical_organism)
    assert composed["effective_config"]["host_sense_source"] == "available"
    assert _shape(restore_canonical_organism(composed))["discovery"]
    # the organism on its own buds a minimal child, with no host source
    assert embryo(OrganismRuntime)["effective_config"]["host_sense_source"] == "unavailable"

"""Issue #275: the legacy Agent simulation is isolated and visibly marked.

The stack is legacy-supported apparatus. These tests fix three things: the
canonical organism cannot reach it, a study cannot build both a legacy Agent
population and a canonical organism, and every protocol that runs on it says so.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from symbiont.core.cognition.agent import Agent
from symbiont.core.social.communication import ConsentBoundChannel
from symbiont.core.social.exchange import ExchangeEnvelope
from symbiont.simulation import ARCHITECTURE
from symbiont_lab.experiments.registry import PROTOCOLS

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
LEGACY_MODULES = (
    "symbiont.simulation",
    "symbiont.core.cognition.agent",
    "symbiont.core.cognition.beliefs",
    "symbiont.core.cognition.curiosity",
    "symbiont.core.cognition.metacognition",
    "symbiont.core.cognition.reasoning",
    "symbiont.core.foundation.model",
    "symbiont.core.social.ledger",
    "symbiont.environment.world",
    "symbiont.environment.regimes",
)
CANONICAL_RUNTIMES = {"OrganismRuntime", "ModeledOrganismRuntime", "PrivateModelOrganismRuntime"}
# Packages that form the canonical organism. None of them may reach the legacy stack.
CANONICAL_PACKAGES = (
    "symbiont/core/orchestration",
    "symbiont/core/domains",
    "symbiont/core/embodiment",
    "symbiont/modeling",
    "symbiont/cognition",
    "symbiont/agency",
    "symbiont/actuation",
    "symbiont/genetics",
    "symbiont/host",
)
# Public aggregators and dispatchers that legitimately expose both.
AGGREGATORS = {
    "symbiont/__init__.py",
    "symbiont/core/__init__.py",
    "symbiont_lab/experiments/registry.py",
}


def _module_name(path: Path) -> str:
    parts = path.relative_to(SRC).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imports(path: Path) -> tuple[set[str], set[str]]:
    """Absolute module names imported by a file, and the names imported from them."""
    package = (
        _module_name(path) if path.name == "__init__.py" else _module_name(path).rpartition(".")[0]
    )
    modules: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                base = package.split(".")[: len(package.split(".")) - (node.level - 1)]
                module = ".".join([*base, module] if module else base)
            modules.add(module)
            modules.update(f"{module}.{alias.name}" for alias in node.names)
            names.update(alias.name for alias in node.names)
    return modules, names


def _is_legacy(module: str) -> bool:
    return any(module == legacy or module.startswith(f"{legacy}.") for legacy in LEGACY_MODULES)


def _files(*relative: str) -> list[Path]:
    return sorted(path for item in relative for path in (SRC / item).rglob("*.py"))


@pytest.mark.parametrize(
    "path", _files(*CANONICAL_PACKAGES), ids=lambda path: path.relative_to(SRC).as_posix()
)
def test_the_canonical_organism_does_not_import_the_legacy_stack(path: Path) -> None:
    modules, _names = _imports(path)
    assert not {module for module in modules if _is_legacy(module)}, path


def test_no_module_builds_both_a_legacy_population_and_a_canonical_organism() -> None:
    mixed = []
    for path in _files("symbiont", "symbiont_lab"):
        if path.relative_to(SRC).as_posix() in AGGREGATORS:
            continue
        modules, names = _imports(path)
        legacy = any(module.startswith("symbiont.simulation") for module in modules) or (
            "symbiont.core.cognition.agent" in modules
        )
        if legacy and names & CANONICAL_RUNTIMES:
            mixed.append(path.relative_to(SRC).as_posix())
    assert mixed == []


def _reaches_legacy(module: str, seen: set[str]) -> bool:
    if module.startswith("symbiont.simulation"):
        return True
    if not module.startswith("symbiont_lab") or module in seen:
        return False
    seen.add(module)
    base = SRC.joinpath(*module.split("."))
    path = base.with_suffix(".py") if base.with_suffix(".py").is_file() else base / "__init__.py"
    if not path.is_file() or path.relative_to(SRC).as_posix() in AGGREGATORS:
        return False
    modules, _names = _imports(path)
    return any(_reaches_legacy(item, seen) for item in modules)


def _declared(protocol) -> str | None:
    import sys

    module = sys.modules[protocol.__module__]
    return getattr(protocol, "SUBJECT_ARCHITECTURE", getattr(module, "SUBJECT_ARCHITECTURE", None))


@pytest.mark.parametrize("name", sorted(PROTOCOLS))
def test_a_protocol_declares_the_legacy_architecture_exactly_when_it_runs_on_it(name: str) -> None:
    protocol = PROTOCOLS[name]
    on_legacy = (
        name in {"simulate", "campaign.comparative"}
        if protocol.__module__
        in {"symbiont_lab.experiments.registry", "symbiont.simulation.engine"}
        else _reaches_legacy(protocol.__module__, set())
    )

    assert _declared(protocol) == (ARCHITECTURE if on_legacy else None)


def test_legacy_protocols_exist() -> None:
    assert sum(_declared(protocol) == ARCHITECTURE for protocol in PROTOCOLS.values()) >= 12


def _agent_pair() -> tuple[Agent, ConsentBoundChannel]:
    channel = ConsentBoundChannel("habitat", b"k" * 32)
    agent = Agent(agent_id="receiver")
    agent.communication_channel = channel
    return agent, channel


def test_a_malformed_claim_is_counted_and_the_valid_one_is_still_ingested() -> None:
    agent, channel = _agent_pair()
    channel.authorize("sender", agent.agent_id)
    message = channel.send(
        ExchangeEnvelope(
            sender="sender",
            sequence=1,
            payload={"good": '{"payload": 1}', "not-json": "{", "not-an-object": "[1]"},
        ),
        agent.agent_id,
    )

    agent.receive_communication(message, tick=3)

    assert set(agent.epistemic_ledger.claims) == {"good"}
    assert agent.malformed_claims == 2


def test_a_ledger_failure_is_not_swallowed() -> None:
    agent, channel = _agent_pair()
    channel.authorize("sender", agent.agent_id)
    message = channel.send(
        ExchangeEnvelope(sender="sender", sequence=1, payload={"good": '{"payload": 1}'}),
        agent.agent_id,
    )

    def broken(_claim: object) -> None:
        raise RuntimeError("ledger defect")

    object.__setattr__(
        agent, "epistemic_ledger", type("L", (), {"receive_claim": staticmethod(broken)})()
    )

    with pytest.raises(RuntimeError, match="ledger defect"):
        agent.receive_communication(message, tick=3)


def test_an_agent_broadcasts_under_its_own_identity() -> None:
    # The sender used to be read from ``HostModel.host_id``, which does not
    # exist: any agent with a channel attached failed on its first broadcast.
    from symbiont.core.social.ledger import SocialClaim, SourceEvidenceOutcome

    sender, channel = _agent_pair()
    channel.authorize(sender.agent_id, "peer")
    sender.epistemic_ledger.receive_claim(
        SocialClaim("claim", "origin", frozenset(), frozenset(), 1, received_tick=0, freshness=1.0)
    )
    sender.epistemic_ledger.reconciliations["claim"] = SourceEvidenceOutcome.UNRESOLVED

    messages = sender.broadcast_claims(["peer"])

    assert [message.sender for message in messages] == ["receiver"]
    assert sender.broadcast_claims(["peer"]) == []

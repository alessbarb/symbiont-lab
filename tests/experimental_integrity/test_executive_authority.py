"""Executive authority boundaries of Agency Acquisition v1 (§7, §46, §56, §75, §102)."""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

from lab.studies.learning.agency_acquisition_body import CausalBody, build_subject
from symbiont.actuation.action import (
    ActionEvaluation,
    ActionJustification,
    ActionProposal,
    ActionSource,
)
from symbiont.actuation.arbitration import ActionArbitrator
from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.agency.intention import ActionIntent, IntentStatus
from symbiont.core.domains.action import ActionDomain

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "symbiont" / "src" / "symbiont"


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            values.append(node.module or "")
            values.extend(f"{node.module}.{alias.name}" for alias in node.names)
    return tuple(values)


def _names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


_COGNITION = (
    *sorted((SRC / "cognition").rglob("*.py")),
    *sorted((SRC / "core" / "cognition").rglob("*.py")),
    SRC / "core" / "domains" / "cognition.py",
)
_EXECUTIVE = (
    SRC / "agency" / "intention.py",
    SRC / "agency" / "affordance.py",
    SRC / "agency" / "affordances.py",
    SRC / "agency" / "prospective.py",
    SRC / "core" / "domains" / "intention.py",
)


def test_cognition_cannot_issue_motor_command():
    motor_tokens = {"MotorCommand", "ActuatorSystem", "issue_command", "execute_command"}
    for path in _COGNITION:
        assert not motor_tokens & _names(path), path
        assert not any("actuation.system" in value for value in _imports(path)), path


def test_action_intent_contains_no_actuator_ids():
    fields = {field.name for field in dataclasses.fields(ActionIntent)}
    forbidden = {
        "actuator_id",
        "actuator_ids",
        "channels",
        "trajectory",
        "gains",
        "torque",
        "motor_vector",
        "reward",
        "global_utility",
        "joint",
    }
    assert not fields & forbidden
    surface = derive_actuator_constitution(1, physical_contract="intent-authority")
    with pytest.raises(ValueError):
        ActionIntent(
            intent_id="intent.x",
            competence_id=surface.actuator_ids[0],
            anticipated_effect_id=None,
            context_ref=None,
            embodiment_id=None,
            origin_refs=(),
            prediction_ref=None,
            confidence=0.5,
            epistemic_relevance=0.5,
            homeostatic_relevance=0.0,
            supporting_affordance_id=None,
            created_tick=0,
            activated_tick=None,
            last_progress_tick=0,
            status=IntentStatus.PENDING,
            termination_reason=None,
        )


def test_action_intent_cannot_call_controller_directly():
    forbidden_modules = ("actuation.controller", "actuation.sensorimotor", "actuation.system")
    forbidden_names = {
        "ControllerFrame",
        "SequenceController",
        "CompetenceDevelopmentEngine",
        "motor_intents",
        "activate_primitive",
        "issue_controller_frame",
    }
    for path in _EXECUTIVE:
        assert not any(
            module in value for value in _imports(path) for module in forbidden_modules
        ), path
        assert not forbidden_names & _names(path), path


def _runtime_with_command():
    body = CausalBody(actuator_count=3, seed=5)
    runtime = build_subject(body, organism_id="authority-subject")
    for _ in range(64):
        runtime.tick()
        body.advance(runtime.last_actuations)
        if runtime._action_domain.last_motor_command is not None:
            return runtime
    raise AssertionError("no command issued")


def test_exploration_does_not_require_action_intent():
    runtime = _runtime_with_command()
    domain = runtime._action_domain
    assert runtime.last_action_source == "exploration"
    assert domain.active_commitment is not None
    assert domain.active_commitment.intent_id is None
    assert domain.intention.active is None
    with pytest.raises(ValueError):
        ActionProposal(
            proposal_id="proposal.bad",
            source=ActionSource.EXPLORATION,
            effect_target_id=None,
            competence_id=None,
            justification=ActionJustification(),
            evaluation=ActionEvaluation(epistemic_relevance=1.0),
            intent_id="intent.x",
        )


def test_protection_does_not_require_action_intent():
    protection = ActionProposal(
        proposal_id="proposal.protect",
        source=ActionSource.PROTECTION,
        effect_target_id=None,
        competence_id="competence.safe",
        justification=ActionJustification(competence_id="competence.safe"),
        evaluation=ActionEvaluation(protective_relevance=0.9, homeostatic_relevance=0.9),
    )
    decision = ActionArbitrator().choose(proposals=(protection,), current=None, tick=1)
    assert decision.proposal is protection
    assert protection.intent_id is None


def test_action_arbitrator_remains_single_motor_authority():
    arbitrator_users = [
        path.relative_to(ROOT).as_posix()
        for path in SRC.rglob("*.py")
        if "ActionArbitrator" in _names(path) and path.name != "arbitration.py"
    ]
    assert arbitrator_users == ["symbiont/src/symbiont/core/domains/action.py"]
    commitment_builders = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ActionCommitment"
            ):
                commitment_builders.append(path.relative_to(ROOT).as_posix())
    assert set(commitment_builders) == {"symbiont/src/symbiont/core/domains/action.py"}
    for path in _EXECUTIVE:
        assert "choose" not in {
            node.attr
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "arbitrator"
        }


def test_motor_command_requires_action_commitment():
    surface = derive_actuator_constitution(1, physical_contract="authority-body")
    domain = ActionDomain(organism_id="organism.authority", enabled=True, surface=surface)
    with pytest.raises(RuntimeError, match="active organism-owned commitment"):
        domain.issue_command({surface.actuator_ids[0]: 0.5}, tick=1)


def test_imagination_never_reaches_factual_evidence():
    """§7.10/§75: generative code never writes EffectSpace or the causal ledger."""
    writes = {"observe_passive_window", "learn", "open_attempt", "close_attempt"}
    for path in sorted((SRC / "cognition" / "generative").glob("*.py")):
        names = _names(path)
        assert "EffectSpace" not in names and "CausalEvidenceLedger" not in names, path
        assert not writes & names, path
        assert not any("actuation" in value for value in _imports(path)), path

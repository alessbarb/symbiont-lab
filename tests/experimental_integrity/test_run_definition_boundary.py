"""Gate A: challenge/run metadata never reaches the engine or the organism.

Run kinds, definition ids, situations and observer purposes are Lab apparatus
(ADR-0008). The engine may receive only the environment recipe name, the seed
and the Lab's read-only run guard.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import symbiont
from symbiont_lab.app.physics3d_runs import Physics3DRunStore
from symbiont_lab.experience import RunGuard, run_definition


def _flatten(value) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _flatten(item)]
    return [str(value)]


def test_challenge_metadata_does_not_enter_runner_kwargs(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare(
        {
            "body_kind": "anthropomorphic-v6",
            "organism": {"mode": "new"},
            "body": {"mode": "fresh"},
            "definition_id": "contact-garden-challenge-v1",
        }
    )
    kwargs = launch.runner_kwargs()
    assert kwargs["environment"] == "contact-garden-v1"
    assert not {"run_kind", "definition_id", "definition", "situations"} & set(kwargs)

    definition = run_definition("contact-garden-challenge-v1")
    leaked = {definition.definition_id, definition.kind.value, definition.title}
    for situation in definition.situations:
        leaked.add(situation.situation_id)
        leaked.update(situation.observer_purpose)
    for value in kwargs.values():
        assert not leaked & set(_flatten(value))


def test_run_guard_receives_only_primitives_and_holds_no_organism() -> None:
    parameters = list(inspect.signature(RunGuard.__call__).parameters)
    assert parameters == ["self", "alive", "vital_state"]
    assert set(RunGuard.__slots__) == {"policy", "triggered"}


def test_symbiont_never_imports_lab_experience() -> None:
    root = Path(symbiont.__file__).parent
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            assert not any(name.startswith("symbiont_lab") for name in names), path

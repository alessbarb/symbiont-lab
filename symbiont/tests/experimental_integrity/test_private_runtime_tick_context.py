from __future__ import annotations

import ast
import inspect
import textwrap

from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime


def test_private_runtime_forwards_canonical_tick_context() -> None:
    source = textwrap.dedent(inspect.getsource(PrivateModelOrganismRuntime.tick))
    tree = ast.parse(source)

    super_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "tick"
        and isinstance(node.func.value, ast.Call)
        and isinstance(node.func.value.func, ast.Name)
        and node.func.value.func.id == "super"
    ]
    assert len(super_calls) == 1
    call = super_calls[0]
    context_keywords = [kw for kw in call.keywords if kw.arg == "context"]
    assert len(context_keywords) == 1
    assert (
        isinstance(context_keywords[0].value, ast.Name)
        and context_keywords[0].value.id == "context"
    )

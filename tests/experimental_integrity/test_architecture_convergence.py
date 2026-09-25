from __future__ import annotations

import ast
from pathlib import Path

from symbiont.actuation.commitment import ActionCommitment


def test_legacy_commitment_migration_requires_explicit_surface() -> None:
    payload = {
        "commitment_id": "commitment.legacy",
        "proposal_id": "proposal.legacy",
        "effect_target_id": None,
        "competence_id": None,
        "started_tick": 4,
        "controller_id": "controller.legacy",
        "status": "active",
    }
    restored = ActionCommitment.restore(
        payload,
        fallback_surface_fingerprint="surface.current",
        fallback_embodiment_id="embodiment.current",
    )
    assert restored.surface_fingerprint == "surface.current"
    assert restored.embodiment_id == "embodiment.current"


def test_runtime_and_core_cognition_use_canonical_genome_type() -> None:
    root = Path(__file__).resolve().parents[2]
    paths = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py",
        root / "src" / "symbiont" / "core" / "cognition" / "bridge.py",
        root / "src" / "symbiont" / "core" / "orchestration" / "individual.py",
    )
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ]
        assert not any(module.endswith("cognition.genome") for module in imports)
        assert "SymbiontGenome" not in path.read_text(encoding="utf-8")

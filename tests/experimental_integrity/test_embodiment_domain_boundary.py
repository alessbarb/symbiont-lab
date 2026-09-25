from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_body_schema_observation() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert "self._embodiment_domain.observe(" in runtime
    assert "self._body_schema.observe_sensory_phenotype(" not in runtime
    assert "self._body_schema.observe_cognition(" not in runtime


def test_embodiment_domain_has_no_motor_authority() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont" / "core" / "domains" / "embodiment.py").read_text(
        encoding="utf-8"
    )
    assert "MotorCommand" not in source
    assert "ActionProposal" not in source
    assert "ActuatorSystem" not in source

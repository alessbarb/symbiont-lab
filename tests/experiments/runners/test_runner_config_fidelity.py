from __future__ import annotations

from pathlib import Path

import pytest

from lab.experiments.runner import ExperimentRunner
from lab.experiments.spec import spec_from_payload


def test_protocol_with_unsuppliable_required_params_fails_loudly(tmp_path: Path) -> None:
    """Unsupported declarative required parameters must fail instead of defaulting."""
    spec = spec_from_payload({"id": "test.unsupported", "protocol": "campaign.comparative"})
    runner = ExperimentRunner(base_dir=tmp_path / ".symbiont")

    with pytest.raises(ValueError, match="campaign.comparative"):
        runner.run(spec)


pytestmark = pytest.mark.experiment_contract

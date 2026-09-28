"""One-tick plumbing, not a claim that prospective agency develops."""

from dataclasses import fields
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from symbiont_lab.physics3d.runtime import Tick3D
from symbiont_lab.studies.learning import prospective_agency_embodied as study

pytestmark = pytest.mark.experiment_contract


def test_first_warmup_tick_polls_training_for_the_subject(monkeypatch):
    tick = SimpleNamespace(**{field.name: 0 for field in fields(Tick3D)})
    tick.tick = 1
    tick.alive = True
    tick.prospective_selected = False
    subject = SimpleNamespace(
        model_registry=SimpleNamespace(active=None),
        available_motor_competence_ids=(),
    )
    runtime = MagicMock()
    runtime.__enter__.return_value = runtime
    runtime.organism = subject
    runtime.step.return_value = tick
    training = MagicMock(training=False)
    training.maybe_schedule.return_value = False
    monkeypatch.setattr(study, "PyBulletEmbodimentRuntime", lambda **kwargs: runtime)
    monkeypatch.setattr(study, "PrivateModelTrainingService", lambda **kwargs: training)

    result = study.run_prospective_embodied_trial(1, warmup_ticks=1, horizon_ticks=1)

    training.poll.assert_called_once_with(subject)
    training.maybe_schedule.assert_called_once_with(subject, current_tick=1)
    training.close.assert_called_once_with()
    assert result.final_tick == 1
    assert not result.readiness_found
    assert result.conditions == ()

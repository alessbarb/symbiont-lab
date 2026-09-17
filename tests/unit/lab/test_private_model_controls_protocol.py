from __future__ import annotations

from dataclasses import dataclass

from symbiont_lab.experiments.registry import get_protocol
from symbiont_lab.experiments.runner import ExperimentRunner
from symbiont_lab.experiments.spec import ExperimentSpec
from symbiont_lab.studies.learning.private_model_controls import _history, _normalize_seeds


def test_private_model_controls_accept_declarative_seed_list():
    assert _normalize_seeds([101, 127, 149]) == (101, 127, 149)


def test_private_model_controls_registered():
    assert get_protocol("learning.private-model-controls").__name__ == "run_private_model_controls_study"


def test_specificity_world_keeps_identity_out_of_model_facing_tokens():
    left = _history(organism_id="organism-alpha", seed=101, ticks=64, rule=0)
    right = _history(organism_id="organism-beta", seed=101, ticks=64, rule=1)

    assert len(left) == len(right) == 64
    assert tuple(record.context_tokens for record in left) == tuple(record.context_tokens for record in right)
    assert tuple(record.action_token for record in left) == tuple(record.action_token for record in right)
    assert any(l.outcome_tokens != r.outcome_tokens for l, r in zip(left, right))
    model_tokens = {
        token
        for record in (*left, *right)
        for token in (*record.context_tokens, record.action_token or "", *record.outcome_tokens)
    }
    assert all("organism-alpha" not in token and "organism-beta" not in token for token in model_tokens)


def test_regime_control_changes_contingency_not_observation_vocabulary():
    pre = _history(organism_id="regime", seed=127, ticks=64, rule=0)
    post = _history(organism_id="regime", seed=127, ticks=64, rule=1)

    pre_vocab = {token for record in pre for token in (*record.context_tokens, record.action_token or "", *record.outcome_tokens)}
    post_vocab = {token for record in post for token in (*record.context_tokens, record.action_token or "", *record.outcome_tokens)}
    assert pre_vocab == post_vocab
    assert any(l.outcome_tokens != r.outcome_tokens for l, r in zip(pre, post))


def test_private_model_protocols_bind_world_steps_to_ticks(monkeypatch, tmp_path):
    captured: list[tuple[tuple[int, ...], int]] = []

    @dataclass(frozen=True)
    class Result:
        def as_dict(self):
            return {"ok": True}

    def protocol(*, seeds, ticks):
        captured.append((tuple(seeds), ticks))
        return Result()

    monkeypatch.setattr("symbiont_lab.experiments.runner.get_protocol", lambda _name: protocol)
    monkeypatch.setattr("symbiont_lab.experiments.runner.get_git_info", lambda: ("a" * 40, False))

    for name in ("learning.private-model-utility", "learning.private-model-controls"):
        ExperimentRunner(tmp_path / name).run(ExperimentSpec(
            experiment_id=name,
            protocol=name,
            steps=73,
            seeds=[101, 127, 149],
        ))

    assert captured == [((101, 127, 149), 73), ((101, 127, 149), 73)]

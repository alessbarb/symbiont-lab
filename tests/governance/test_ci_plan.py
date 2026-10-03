from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from governance import ci_plan
from governance.classify import ChangeClass


def _plan(
    monkeypatch,
    classification: ChangeClass,
    paths: list[str],
    *,
    sections: tuple[str, ...],
    lanes: set[str],
):
    calls = iter(["\n".join(paths), "diff"])
    monkeypatch.setattr(ci_plan, "_git", lambda *args: next(calls))
    monkeypatch.setattr(
        ci_plan,
        "assess",
        lambda *args, **kwargs: SimpleNamespace(
            classification=classification,
            reasons=("test",),
        ),
    )
    monkeypatch.setattr(ci_plan, "_selected_matrix_sections", lambda *args: sections)
    monkeypatch.setattr(ci_plan, "_lanes_for_sections", lambda *args: set(lanes))
    return ci_plan.build_plan("base", "head")


def test_ordinary_docs_change_runs_docs_lane_only(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.ORDINARY,
        ["symbiont/docs/explanation/readme.md"],
        sections=("docs",),
        lanes={"docs"},
    )

    assert plan.docs
    assert not plan.software_core
    assert not plan.architecture_integrity
    assert not plan.python_compat
    assert not plan.host_portability
    assert not plan.physics3d
    assert not plan.modeling
    assert not plan.protocol_mechanics


def test_scientific_subject_change_runs_core_and_integrity(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.SCIENTIFIC,
        ["symbiont/src/symbiont/core/example.py"],
        sections=("subject",),
        lanes={"software_core", "architecture_integrity"},
    )

    assert plan.software_core
    assert plan.architecture_integrity
    assert plan.runtime_contracts
    assert plan.python_compat
    assert plan.protocol_mechanics
    assert not plan.host_portability
    assert not plan.physics3d
    assert not plan.modeling


def test_world_change_uses_targeted_world_lane(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.SCIENTIFIC,
        ["lab/src/lab/world/example.py"],
        sections=("world",),
        lanes={"world", "architecture_integrity"},
    )

    assert plan.world
    assert not plan.software_core
    assert plan.architecture_integrity


def test_observatory_change_uses_targeted_observatory_lane(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.ORDINARY,
        ["lab/src/lab/observatory/server.py"],
        sections=("observatory",),
        lanes={"observatory", "architecture_integrity"},
    )

    assert plan.observatory
    assert plan.architecture_integrity
    assert plan.performance
    assert not plan.physics3d
    assert not plan.modeling
    assert not plan.python_compat


def test_experiment_change_runs_experiment_mechanics(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.SCIENTIFIC,
        ["lab/src/lab/studies/example.py"],
        sections=("experiment_protocol",),
        lanes={"experiment_mechanics", "architecture_integrity"},
    )

    assert plan.experiment_mechanics
    assert plan.architecture_integrity
    assert plan.runtime_contracts
    assert plan.protocol_mechanics


def test_physics3d_change_adds_heavy_physics_lane(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.SCIENTIFIC,
        ["lab/src/lab/physics3d/engine.py"],
        sections=("lab",),
        lanes={"software_core", "architecture_integrity"},
    )

    assert plan.physics3d
    assert not plan.modeling
    assert plan.host_portability
    assert plan.performance


def test_modeling_change_adds_heavy_modeling_lane(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.SCIENTIFIC,
        ["lab/src/lab/modeling/trainer.py"],
        sections=("lab",),
        lanes={"software_core", "architecture_integrity"},
    )

    assert plan.modeling
    assert not plan.physics3d
    assert plan.performance


def test_host_change_adds_portability_lanes(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.SCIENTIFIC,
        ["symbiont/src/symbiont/host/providers/example.py"],
        sections=("subject",),
        lanes={"software_core", "architecture_integrity"},
    )

    assert plan.host_portability
    assert plan.alpine
    assert plan.performance
    assert not plan.physics3d
    assert not plan.modeling


def test_constitutional_change_runs_broad_behavioral_sentinels(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.CONSTITUTIONAL,
        [".github/workflows/ci.yml"],
        sections=("governance",),
        lanes={"governance"},
    )

    assert plan.governance
    assert plan.software_core
    assert plan.observatory
    assert plan.architecture_integrity
    assert plan.runtime_contracts
    assert plan.experiment_mechanics
    assert plan.physics3d
    assert plan.modeling
    assert plan.python_compat
    assert plan.host_portability
    assert plan.alpine
    assert plan.protocol_mechanics
    assert plan.performance


def test_observed_launchers_select_the_observatory_lane() -> None:
    import tomllib

    matrix = tomllib.loads(
        (ROOT / "docs" / "governance" / "validation-matrix.toml").read_text(encoding="utf-8")
    )
    launchers = sorted((ROOT / "lab" / "src" / "lab" / "cli").glob("observed_*.py"))

    assert launchers
    for launcher in launchers:
        path = launcher.relative_to(ROOT).as_posix()
        assert any(ci_plan._matches(path, pattern) for pattern in matrix["observatory"]["paths"]), (
            path
        )
    assert "observatory" in matrix["observatory"]["ci_lanes"]


def test_constitutional_markdown_only_change_skips_heavy_lanes(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.CONSTITUTIONAL,
        [".agents/skills/architecture-decision/SKILL.md"],
        sections=("governance",),
        lanes={"governance"},
    )

    assert plan.governance
    assert plan.docs
    assert not plan.software_core
    assert not plan.observatory
    assert not plan.architecture_integrity
    assert not plan.runtime_contracts
    assert not plan.experiment_mechanics
    assert not plan.physics3d
    assert not plan.modeling
    assert not plan.python_compat
    assert not plan.host_portability
    assert not plan.alpine
    assert not plan.protocol_mechanics
    assert not plan.performance


def test_scientific_markdown_only_change_skips_heavy_lanes(monkeypatch) -> None:
    plan = _plan(
        monkeypatch,
        ChangeClass.SCIENTIFIC,
        ["docs/design/core/example.md"],
        sections=("docs", "experiment_protocol"),
        lanes={"docs", "experiment_mechanics", "architecture_integrity"},
    )

    assert plan.docs
    assert not plan.software_core
    assert not plan.architecture_integrity
    assert not plan.runtime_contracts
    assert not plan.experiment_mechanics
    assert not plan.physics3d
    assert not plan.modeling
    assert not plan.python_compat
    assert not plan.protocol_mechanics
    assert not plan.performance

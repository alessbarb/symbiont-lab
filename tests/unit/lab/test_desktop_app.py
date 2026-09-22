from pathlib import Path
from symbiont_lab.app.discovery import discover_experiments
from symbiont_lab.app.models import RunKind, RunStatus

def test_desktop_run_model_is_explicit():
    assert RunKind.EXPERIMENT.value == "experiment"
    assert RunKind.PHYSICS3D.value == "physics3d"
    assert RunStatus.RUNNING.value == "running"

def test_discover_experiments_reads_declarative_catalog(tmp_path: Path):
    exp=tmp_path/"learning"/"demo"; exp.mkdir(parents=True)
    (exp/"experiment.toml").write_text("""schema_version = 1
[experiment]
id = "demo"
title = "Demo experiment"
protocol = "simulate"
protocol_version = 1
hypothesis = "demo hypothesis"
success_criteria = "demo criteria"
[world]
hosts = 4
steps = 12
seed = 7
""",encoding="utf-8")
    entries=discover_experiments(tmp_path)
    assert len(entries)==1
    assert entries[0].category=="learning"
    assert entries[0].experiment_id=="demo"
    assert entries[0].steps==12

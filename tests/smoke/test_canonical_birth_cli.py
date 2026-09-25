from __future__ import annotations

import json
import subprocess
import sys

from symbiont.core.runtime import OrganismRuntime


def test_default_organism_run_has_canonical_cognition():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "symbiont_lab.cli.main",
            "organism",
            "run",
            "--ticks",
            "1",
            "--investigate-ticks",
            "0",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ticks"][0]["cognition"] is not None
    assert payload["checkpoint"]["genome"]["genome_id"] == "genome_symbiont_base_v2"
    assert payload["checkpoint"]["cognitive_bridge"] is not None


def test_default_organism_run_adopts_a_legacy_state_file(tmp_path):
    state_file = tmp_path / "legacy.json"
    legacy = OrganismRuntime(bootstrap_semantic_senses=False)
    legacy.save(state_file)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "symbiont_lab.cli.main",
            "organism",
            "run",
            "--ticks",
            "1",
            "--state-file",
            str(state_file),
            "--investigate-ticks",
            "0",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["checkpoint"]["genome"]["genome_id"] == "genome_symbiont_base_v2"
    assert payload["checkpoint"]["cognitive_bridge"] is not None

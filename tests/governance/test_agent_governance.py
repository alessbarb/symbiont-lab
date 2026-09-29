from __future__ import annotations

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "docs" / "governance"


def _agentctl():
    spec = importlib.util.spec_from_file_location("agentctl", ROOT / "scripts" / "agentctl.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _contract(path: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    start = "<!-- BEGIN CANONICAL AGENT CONTRACT -->"
    end = "<!-- END CANONICAL AGENT CONTRACT -->"
    return text[text.index(start): text.index(end) + len(end)]


def test_agent_contract_is_identical() -> None:
    assert _contract("AGENTS.md") == _contract("CLAUDE.md")


def test_governance_toml_is_parseable() -> None:
    for name in (
        "project-state.toml", "frozen-artifacts.toml", "active-work.toml",
        "validation-matrix.toml", "authority-grants.toml", "resource-policy.toml",
        "owner-root.toml",
        "bootstrap-exceptions.toml",
    ):
        with (GOV / name).open("rb") as handle:
            assert tomllib.load(handle)


def test_control_plane_is_l4() -> None:
    ctl = _agentctl()
    for path in (
        "AGENTS.md", "docs/governance/project-state.toml", "scripts/agentctl.py",
        "tests/governance/test_agent_governance.py", ".github/workflows/ci.yml",
        ".github/CODEOWNERS", ".pre-commit-config.yaml", ".claude/settings.json",
        ".codex/hooks.json", ".agents/rules/graphify.md", "pyproject.toml",
        "pyrightconfig.json", ".gitignore",
    ):
        assert ctl.required_authority(path, "HEAD") == "L4"


def test_completed_experiment_freezes_entire_directory() -> None:
    ctl = _agentctl()
    base = "experiments/embodiment/yoked-external-causation"
    for path in (f"{base}/experiment.toml", f"{base}/README.md", f"{base}/results.json"):
        assert ctl.required_authority(path, "HEAD") == "L4"


def test_integrity_and_protocol_surfaces_are_not_l1() -> None:
    ctl = _agentctl()
    assert ctl.required_authority("tests/experimental_integrity/test_example.py", "HEAD") == "L2"
    assert ctl.required_authority("tests/experiments/test_example.py", "HEAD") == "L3"
    assert ctl.required_authority("docs/design/example.md", "HEAD") == "L3"
    assert ctl.required_authority("research/example.md", "HEAD") == "L3"


def test_commit_exists_uses_return_code() -> None:
    ctl = _agentctl()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()
    assert ctl.commit_exists(head)
    assert not ctl.commit_exists("0" * 40)


def test_git_common_dir_exists() -> None:
    assert _agentctl().git_common_dir().exists()


def test_agentctl_verifies_repository_governance() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/agentctl.py", "verify"], cwd=ROOT,
        check=False, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


def test_bootstrap_exceptions_are_exact() -> None:
    with (GOV / "bootstrap-exceptions.toml").open("rb") as handle:
        entries = tomllib.load(handle)["commit"]
    assert entries
    for entry in entries:
        assert entry["status"] == "accepted"
        assert len(entry["sha"]) == 40
        int(entry["sha"], 16)
        assert entry["reason"]



def test_resource_policy_uses_run_start() -> None:
    with (GOV / "resource-policy.toml").open("rb") as handle:
        policy = tomllib.load(handle)["scientific_runs"]
    assert policy["launcher"] == "python scripts/agentctl.py run start"
    assert policy["trusted_state"] == "origin/main"



def test_trusted_governance_helpers_share_explicit_ref(monkeypatch) -> None:
    ctl = _agentctl()
    calls: list[tuple[str, str]] = []

    def fake_show(ref: str, path: str) -> str | None:
        calls.append((ref, path))
        if path.endswith("active-work.toml"):
            return 'schema_version = 1\n[[work]]\nid = "x"\nstate = "RUNNING"\n'
        if path.endswith("resource-policy.toml"):
            return 'schema_version = 1\n[scientific_runs]\nmax_memory_gb = 12\n'
        return None

    monkeypatch.setattr(ctl, "git_show", fake_show)
    ref = "a" * 40
    assert ctl._tracked_running_at(ref) == ["x"]
    policy = ctl._trusted_governance_at(ref, "resource-policy.toml")
    assert policy["scientific_runs"]["max_memory_gb"] == 12
    assert {item[0] for item in calls} == {ref}



def test_equivalence_evidence_requires_matching_parent_and_passes() -> None:
    ctl = _agentctl()

    class Assessment:
        equivalence_scenarios = ("s1", "s2")

    parent = "a" * 40
    commit = "c" * 40
    monkey_tree = "d" * 40
    original_git = ctl.git
    ctl.git = lambda *args, **kwargs: monkey_tree if args == ("show", "-s", "--format=%T", commit) else original_git(*args, **kwargs)
    try:
        valid = {
            "_meta": {"baseline_commit": parent, "candidate_tree": monkey_tree},
            "s1": {"status": "PASS"},
            "s2": {"status": "PASS"},
        }
        assert ctl._equivalence_evidence_errors(
            parent, commit, Assessment(), __import__("json").dumps(valid)
        ) == []

        wrong_parent = {
            "_meta": {"baseline_commit": "b" * 40, "candidate_tree": monkey_tree},
            "s1": {"status": "PASS"},
            "s2": {"status": "PASS"},
        }
        assert ctl._equivalence_evidence_errors(
            parent, commit, Assessment(), __import__("json").dumps(wrong_parent)
        )
        wrong_tree = {
            "_meta": {"baseline_commit": parent, "candidate_tree": "e" * 40},
            "s1": {"status": "PASS"},
            "s2": {"status": "PASS"},
        }
        assert ctl._equivalence_evidence_errors(
            parent, commit, Assessment(), __import__("json").dumps(wrong_tree)
        )
        missing = {
            "_meta": {"baseline_commit": parent, "candidate_tree": monkey_tree},
            "s1": {"status": "PASS"},
        }
        assert ctl._equivalence_evidence_errors(
            parent, commit, Assessment(), __import__("json").dumps(missing)
        )
    finally:
        ctl.git = original_git


def test_governance_adr_must_be_accepted_inside_docs_adr(monkeypatch) -> None:
    ctl = _agentctl()
    monkeypatch.setattr(
        ctl,
        "git_show",
        lambda ref, path: "- **Status:** Accepted\n" if path == "docs/adr/ADR-9999-test.md" else None,
    )
    assert ctl._governance_adr_valid("a" * 40, "docs/adr/ADR-9999-test.md")
    assert not ctl._governance_adr_valid("a" * 40, "../ADR-9999-test.md")
    assert not ctl._governance_adr_valid("a" * 40, "docs/adr/not-an-adr.md")


def test_active_run_path_is_blocked_for_governance_class_commits() -> None:
    ctl = _agentctl()
    blocked = ctl._path_blocked_by_active(
        "src/symbiont_lab/studies/learning/visual_acquisition.py",
        "HEAD",
        None,
    )
    assert blocked == "visual-acquisition-d1-v2"

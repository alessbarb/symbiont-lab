"""One-command governed publication.

The user-facing contract is intentionally small: agents call agentctl publish.
This module owns synchronization, final-diff classification, bounded equivalence
evidence, validation, audit trailers, commit normalization and optimistic publication.
"""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from governance.classify import ChangeClass, Assessment, assess  # noqa: E402
from symbiont_lab.experiments.execution_workspace import pinned_worktree  # noqa: E402
from symbiont_lab.experiments.resource_guard import ResourceRequest, assess_resources  # noqa: E402
from symbiont_lab.physics3d.equivalence_suite import compare, load_suite, suite_status  # noqa: E402


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _untracked_context() -> str:
    chunks: list[str] = []
    for raw in filter(None, _git("ls-files", "--others", "--exclude-standard").splitlines()):
        path = ROOT / raw
        chunks.append(f"\n--- untracked:{raw} ---\n")
        try:
            if path.is_file() and path.stat().st_size <= 1_000_000:
                chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            else:
                chunks.append("<binary-or-large>")
        except OSError:
            chunks.append("<unreadable>")
    return "".join(chunks)


def _changed_against(base: str) -> tuple[list[str], str]:
    paths = set(filter(None, _git("diff", "--name-only", base).splitlines()))
    paths.update(filter(None, _git("ls-files", "--others", "--exclude-standard").splitlines()))
    diff = _git("diff", "--no-ext-diff", base, check=False) + _untracked_context()
    return sorted(paths), diff


def _classify(base: str) -> tuple[list[str], Assessment]:
    paths, diff = _changed_against(base)
    return paths, assess(ROOT, base, paths, diff)


def _active_work_at(base: str) -> dict:
    """Read active-work policy from the trusted publication baseline."""
    result = subprocess.run(
        ["git", "show", f"{base}:docs/governance/active-work.toml"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError("trusted baseline is missing active-work.toml")
    return tomllib.loads(result.stdout)


def _active_work_conflicts(paths: list[str], base: str) -> list[str]:
    data = _active_work_at(base)
    conflicts: list[str] = []
    for work in data.get("work", []):
        if work.get("state") != "RUNNING":
            continue
        for path in paths:
            if any(fnmatch.fnmatchcase(path, pattern) for pattern in work.get("protected_paths", [])):
                conflicts.append(f"{work.get('id')}: {path}")
    return conflicts


def _running_long_work(base: str) -> list[str]:
    data = _active_work_at(base)
    return [str(work.get("id")) for work in data.get("work", []) if work.get("state") == "RUNNING"]


def _git_common_dir() -> Path:
    raw = _git("rev-parse", "--git-common-dir")
    path = Path(raw)
    return path if path.is_absolute() else (ROOT / path).resolve()


def _scientific_lock_path() -> Path:
    return _git_common_dir() / "symbiont-agent" / "scientific-run.json"


def _equivalence_lock_path() -> Path:
    return _git_common_dir() / "symbiont-agent" / "equivalence-run.json"


class _EquivalenceLock:
    def __enter__(self) -> "_EquivalenceLock":
        if _scientific_lock_path().exists():
            raise RuntimeError("equivalence unavailable while a scientific run lock exists")
        lock = _equivalence_lock_path()
        lock.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise RuntimeError("another equivalence run is already active") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "started_at": time.time(), "kind": "causal-equivalence"}, handle)
            handle.write("\n")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _equivalence_lock_path().unlink(missing_ok=True)


def _run_scenario(code_root: Path, suite: Path, scenario: str, output: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(code_root / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "symbiont_lab.physics3d.equivalence_suite",
            str(suite),
            scenario,
            str(output),
        ],
        cwd=code_root,
        env=env,
        check=False,
    )
    if not output.exists():
        return {"status": "ERROR", "reason": f"runner exit {result.returncode} without output"}
    return json.loads(output.read_text(encoding="utf-8"))


def run_equivalence(base: str, scenarios: tuple[str, ...]) -> tuple[bool, dict[str, dict]]:
    if not scenarios:
        return True, {}

    running = _running_long_work(base)
    if running:
        return False, {"suite": {"status": "NOT_ASSESSABLE_ACTIVE_RUN", "active_work": running}}

    suite = ROOT / "experiments/equivalence/suite-v1/suite.toml"
    if not suite.is_file():
        return False, {"suite": {"status": "ERROR", "reason": "equivalence suite missing"}}
    readiness = suite_status(suite)
    if not readiness.get("ready"):
        return False, {"suite": {"status": "NOT_ASSESSABLE_SNAPSHOT_SET", "details": readiness}}

    _, definitions = load_suite(suite)
    by_id = {item.scenario_id: item for item in definitions}
    evidence: dict[str, dict] = {}

    with _EquivalenceLock():
        with pinned_worktree(ROOT, base) as baseline_tree:
            for scenario_id in scenarios:
                definition = by_id.get(scenario_id)
                if definition is None:
                    evidence[scenario_id] = {"status": "ERROR", "reason": "unknown scenario"}
                    return False, evidence
                resources = assess_resources(
                    ResourceRequest(
                        peak_memory_gb=definition.memory_gb,
                        disk_gb=definition.disk_gb,
                        cpu_threads=definition.cpu_threads,
                        safety_memory_gb=1.0,
                    ),
                    disk_path=ROOT,
                )
                if not resources.allowed:
                    evidence[scenario_id] = {
                        "status": "NOT_ASSESSABLE_RESOURCES",
                        "reason": list(resources.reasons),
                    }
                    return False, evidence
                with tempfile.TemporaryDirectory() as td:
                    td_path = Path(td)
                    baseline = _run_scenario(
                        baseline_tree, suite, scenario_id, td_path / "baseline.json"
                    )
                    candidate = _run_scenario(ROOT, suite, scenario_id, td_path / "candidate.json")
                    result = compare(definition, baseline, candidate)
                    evidence[scenario_id] = result
                    if result.get("status") != "PASS":
                        return False, evidence
    return True, evidence


def _accepted_adr(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(
        re.search(
            r"(?im)^-\s*\*\*Status:\*\*\s*Accepted\s*$|^Status:\s*Accepted\s*$",
            text,
        )
    )


def _normalize_adr_ref(value: str) -> Path:
    raw = value.strip()
    candidate = Path(raw)
    if candidate.suffix.lower() == ".md":
        path = candidate if candidate.is_absolute() else ROOT / candidate
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        return path

    slug = raw
    if not slug.upper().startswith("ADR-"):
        slug = f"ADR-{slug}"
    matches = sorted((ROOT / "docs/adr").glob(f"{slug}*.md"))
    if len(matches) != 1:
        raise PermissionError(
            f"CONSTITUTIONAL: ADR reference {value!r} did not resolve uniquely"
        )
    return matches[0]


def _resolve_constitutional_adr(
    paths: list[str],
    *,
    adr_ref: str | None,
) -> str:
    changed_adrs = [
        ROOT / path
        for path in paths
        if path.startswith("docs/adr/") and path.endswith(".md")
    ]
    accepted_changed = [path for path in changed_adrs if _accepted_adr(path)]

    if adr_ref:
        path = _normalize_adr_ref(adr_ref)
        if not _accepted_adr(path):
            raise PermissionError(
                f"CONSTITUTIONAL: ADR {path.relative_to(ROOT)} is not Accepted"
            )
        return path.relative_to(ROOT).as_posix()

    if len(accepted_changed) == 1:
        return accepted_changed[0].relative_to(ROOT).as_posix()
    if len(accepted_changed) > 1:
        raise PermissionError(
            "CONSTITUTIONAL: multiple Accepted ADRs changed; select one with --adr"
        )
    raise PermissionError(
        "CONSTITUTIONAL: an Accepted ADR is required; change one in this task or pass --adr"
    )


def _evaluate(
    base: str,
    *,
    owner_approved: bool,
    adr_ref: str | None,
) -> tuple[Assessment, ChangeClass, dict[str, dict], str | None]:
    paths, assessment = _classify(base)
    if not paths:
        return assessment, ChangeClass.ORDINARY, {}, None

    conflicts = _active_work_conflicts(paths, base)
    if conflicts:
        raise RuntimeError(
            "ACTIVE-WORK: proposed diff touches a RUNNING campaign:\n  - "
            + "\n  - ".join(conflicts)
        )

    print(f"classification: {assessment.classification}")
    for reason in assessment.reasons:
        print(f"  - {reason}")

    if assessment.classification == ChangeClass.FROZEN:
        raise RuntimeError("FROZEN: completed scientific evidence must be versioned, not modified")

    constitutional_adr: str | None = None
    if assessment.classification == ChangeClass.CONSTITUTIONAL:
        if not owner_approved:
            raise PermissionError("CONSTITUTIONAL: explicit owner approval required")
        constitutional_adr = _resolve_constitutional_adr(paths, adr_ref=adr_ref)

    eq_pass, evidence = run_equivalence(base, assessment.equivalence_scenarios)
    effective = assessment.classification
    if effective == ChangeClass.SCIENTIFIC:
        if assessment.equivalence_scenarios and eq_pass:
            effective = ChangeClass.ORDINARY
            print("equivalence: PASS — causally transparent within declared scenario coverage")
        elif not owner_approved:
            detail = json.dumps(evidence, indent=2) if evidence else "no covering equivalence scenario"
            raise PermissionError(f"SCIENTIFIC: explicit owner decision required\n{detail}")
    return assessment, effective, evidence, constitutional_adr


def _publication_message(
    message: str,
    *,
    effective: ChangeClass,
    owner_approved: bool,
    evidence: dict[str, dict],
    constitutional_adr: str | None,
) -> str:
    trailers = [
        f"Governance-Class: {effective}",
        f"Owner-Approval: {'explicit' if owner_approved else 'not-required'}",
    ]
    if constitutional_adr:
        trailers.append(f"Governance-ADR: {constitutional_adr}")
    if evidence:
        trailers.append(
            "Equivalence-Evidence: "
            + json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        )
    return message.rstrip() + "\n\n" + "\n".join(trailers)


def _validate_staged() -> None:
    subprocess.run(
        [sys.executable, "scripts/agentctl.py", "validate", "--staged"],
        cwd=ROOT,
        check=True,
    )


def _backup_local_head() -> str | None:
    remote = _git("rev-parse", "origin/main")
    head = _git("rev-parse", "HEAD")
    if head == remote:
        return None
    name = f"refs/agentctl/prepublish/{int(time.time())}-{head[:10]}"
    _git("update-ref", name, head)
    return name


def _normalize_local_commits(remote: str) -> str | None:
    """Collapse unpublished local commits into the final proposed diff.

    A backup ref preserves the original local history. This avoids requiring every
    intermediate local commit to carry publication governance metadata.
    """

    head = _git("rev-parse", "HEAD")
    if head == remote:
        return None
    backup = _backup_local_head()
    _git("reset", "--soft", remote)
    if backup:
        print(f"local history preserved at {backup}")
    return backup


def _sync_to_remote() -> str:
    _git("fetch", "origin", "main")
    remote = _git("rev-parse", "origin/main")
    if _git("rev-parse", "HEAD") == remote:
        return remote

    result = subprocess.run(
        ["git", "rebase", "--autostash", "origin/main"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("concurrent semantic conflict during rebase")
    return _git("rev-parse", "origin/main")


def _stage_validate_commit(
    message: str,
    *,
    effective: ChangeClass,
    owner_approved: bool,
    evidence: dict[str, dict],
    constitutional_adr: str | None,
    amend: bool = False,
) -> str:
    _git("add", "-A")
    _validate_staged()
    full_message = _publication_message(
        message,
        effective=effective,
        owner_approved=owner_approved,
        evidence=evidence,
        constitutional_adr=constitutional_adr,
    )
    args = ["commit"]
    if amend:
        args.append("--amend")
    args += ["-m", full_message]
    _git(*args)
    return _git("rev-parse", "HEAD")


def publish(
    *,
    message: str,
    owner_approved: bool = False,
    adr_ref: str | None = None,
    retries: int = 3,
) -> int:
    """Publish the final task diff while keeping governance invisible for ordinary work."""

    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        print("BLOCKED — publish requires a branch checkout", file=sys.stderr)
        return 2

    try:
        remote = _sync_to_remote()
        _normalize_local_commits(remote)

        paths, _ = _classify(remote)
        if not paths:
            print("nothing to publish")
            return 0

        _, effective, evidence, constitutional_adr = _evaluate(
            remote,
            owner_approved=owner_approved,
            adr_ref=adr_ref,
        )
        _stage_validate_commit(
            message,
            effective=effective,
            owner_approved=owner_approved,
            evidence=evidence,
            constitutional_adr=constitutional_adr,
        )

        for attempt in range(1, retries + 1):
            _git("fetch", "origin", "main")
            latest = _git("rev-parse", "origin/main")
            if latest != remote:
                result = subprocess.run(
                    ["git", "rebase", "origin/main"],
                    cwd=ROOT,
                    check=False,
                )
                if result.returncode:
                    print("BLOCKED — main changed and rebase conflicts", file=sys.stderr)
                    return 2
                remote = latest

                # The baseline changed: recompute evidence and validation, then amend
                # the publication attestation to match the final rebased diff.
                _, effective, evidence, constitutional_adr = _evaluate(
                    remote,
                    owner_approved=owner_approved,
                    adr_ref=adr_ref,
                )
                _stage_validate_commit(
                    message,
                    effective=effective,
                    owner_approved=owner_approved,
                    evidence=evidence,
                    constitutional_adr=constitutional_adr,
                    amend=True,
                )

            result = subprocess.run(
                ["git", "push", "origin", "HEAD:main"],
                cwd=ROOT,
                check=False,
            )
            if result.returncode == 0:
                print(f"published: {_git('rev-parse', 'HEAD')}")
                return 0

            _git("fetch", "origin", "main")
            if attempt == retries:
                break

        print("BLOCKED — main kept changing; rerun agentctl publish", file=sys.stderr)
        return 4
    except PermissionError as exc:
        print(f"BLOCKED — {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        print(f"BLOCKED — {exc}", file=sys.stderr)
        return 2

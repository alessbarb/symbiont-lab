"""One-command governed publication.

The user-facing contract is intentionally small: agents call agentctl publish.
This module owns synchronization, final-diff classification, bounded equivalence
evidence, audit trailers and candidate publication. GitHub Actions owns technical
validation and promotion into main.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from governance.classify import Assessment, ChangeClass, assess  # noqa: E402
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
            if any(
                fnmatch.fnmatchcase(path, pattern) for pattern in work.get("protected_paths", [])
            ):
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
            json.dump(
                {"pid": os.getpid(), "started_at": time.time(), "kind": "causal-equivalence"},
                handle,
            )
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

    suite_id, definitions = load_suite(suite)
    by_id = {item.scenario_id: item for item in definitions}
    evidence: dict[str, dict] = {
        "_meta": {
            "baseline_commit": base,
            "candidate_tree": _git("write-tree"),
            "suite_id": suite_id,
            "suite_path": suite.relative_to(ROOT).as_posix(),
        }
    }

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
    adr_root = (ROOT / "docs/adr").resolve()
    candidate = Path(raw)

    if candidate.suffix.lower() == ".md":
        path = (candidate if candidate.is_absolute() else ROOT / candidate).resolve()
        try:
            path.relative_to(adr_root)
        except ValueError as exc:
            raise PermissionError("CONSTITUTIONAL: ADR must live under docs/adr") from exc
        if not path.name.upper().startswith("ADR-"):
            raise PermissionError("CONSTITUTIONAL: ADR filename must start with ADR-")
        return path

    slug = raw
    if not slug.upper().startswith("ADR-"):
        slug = f"ADR-{slug}"
    matches = sorted(adr_root.glob(f"{slug}*.md"))
    if len(matches) != 1:
        raise PermissionError(f"CONSTITUTIONAL: ADR reference {value!r} did not resolve uniquely")
    return matches[0]


def _resolve_constitutional_adr(
    paths: list[str],
    *,
    adr_ref: str | None,
) -> str:
    changed_adrs = [
        ROOT / path for path in paths if path.startswith("docs/adr/") and path.endswith(".md")
    ]
    accepted_changed = [path for path in changed_adrs if _accepted_adr(path)]

    if adr_ref:
        path = _normalize_adr_ref(adr_ref)
        if not _accepted_adr(path):
            raise PermissionError(f"CONSTITUTIONAL: ADR {path.relative_to(ROOT)} is not Accepted")
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
        constitutional_adr = _resolve_constitutional_adr(paths, adr_ref=adr_ref)

    eq_pass, evidence = run_equivalence(base, assessment.equivalence_scenarios)
    effective = assessment.classification
    if effective == ChangeClass.SCIENTIFIC:
        if assessment.equivalence_scenarios and eq_pass:
            effective = ChangeClass.ORDINARY
            print("equivalence: PASS — causally transparent within declared scenario coverage")
        else:
            print("scientific candidate: external owner review required before promotion")
    return assessment, effective, evidence, constitutional_adr


def _publication_message(
    message: str,
    *,
    effective: ChangeClass,
    evidence: dict[str, dict],
    constitutional_adr: str | None,
) -> str:
    trailers = [f"Governance-Class: {effective}"]
    if constitutional_adr:
        trailers.append(f"Governance-ADR: {constitutional_adr}")
    if evidence:
        trailers.append(
            "Equivalence-Evidence: " + json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        )
    return message.rstrip() + "\n\n" + "\n".join(trailers)


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


def _rebase_and_reprepare(latest: str) -> None:
    """Rebase a prepared candidate and restore its final diff to the index."""

    result = subprocess.run(
        ["git", "rebase", latest],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("main changed and rebase conflicts")
    _normalize_local_commits(latest)


def _stage_commit(
    message: str,
    *,
    effective: ChangeClass,
    evidence: dict[str, dict],
    constitutional_adr: str | None,
) -> str:
    """Create one governed candidate commit; CI owns technical validation."""
    _git("add", "-A")
    full_message = _publication_message(
        message,
        effective=effective,
        evidence=evidence,
        constitutional_adr=constitutional_adr,
    )
    _git("commit", "--no-verify", "-m", full_message)
    return _git("rev-parse", "HEAD")


def _candidate_branch(commit: str) -> str:
    return f"agentctl/{int(time.time())}-{commit[:12]}"


_GOVERNANCE_LABELS = {
    ChangeClass.ORDINARY: (
        "0075ca",
        "Governance classification: ordinary maintenance or engineering.",
    ),
    ChangeClass.SCIENTIFIC: (
        "d93f0b",
        "Governance classification: scientific change; external review required.",
    ),
    ChangeClass.CONSTITUTIONAL: (
        "5319e7",
        "Constitutional control-plane/invariant change; external review required.",
    ),
    ChangeClass.FROZEN: (
        "6f42c1",
        "Governance classification: frozen evidence; requires its governed versioning path.",
    ),
}


def _create_candidate_pr(candidate: str, commit: str, effective: ChangeClass) -> str:
    """Open the review handoff using metadata from the pushed candidate commit."""
    color, description = _GOVERNANCE_LABELS[effective]
    # Labels are repository metadata and are not versioned in Git. Provision
    # the required class label when absent; never alter an existing label.
    listed = subprocess.run(
        ["gh", "label", "list", "--json", "name"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if listed.returncode:
        raise RuntimeError("cannot list GitHub labels; candidate was pushed but PR was not created")
    labels = {item["name"] for item in json.loads(listed.stdout)}
    if effective.value not in labels:
        created = subprocess.run(
            [
                "gh",
                "label",
                "create",
                effective.value,
                "--color",
                color,
                "--description",
                description,
            ],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if created.returncode:
            raise RuntimeError(
                "cannot create governance label; candidate was pushed but PR was not created"
            )

    title = _git("show", "-s", "--format=%s", commit)
    body = _git("show", "-s", "--format=%b", commit)
    if not body:
        body = f"Governed candidate `{candidate}` created by agentctl."

    result = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            candidate,
            "--title",
            title,
            "--body",
            body,
            "--label",
            effective.value,
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.strip() or "GitHub CLI failed"
        raise RuntimeError(f"candidate pushed but PR creation failed: {detail}")
    return result.stdout.strip()


def publish(
    *,
    message: str,
    adr_ref: str | None = None,
    retries: int = 3,
) -> int:
    """Publish a governed candidate; CI is the sole technical validation gate."""

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

        # Governance remains local: active-work, classification/authority,
        # FROZEN/CONSTITUTIONAL policy and causal-equivalence evidence.
        _git("add", "-A")
        _, effective, evidence, constitutional_adr = _evaluate(
            remote,
            adr_ref=adr_ref,
        )
        _stage_commit(
            message,
            effective=effective,
            evidence=evidence,
            constitutional_adr=constitutional_adr,
        )

        for _attempt in range(1, retries + 1):
            _git("fetch", "origin", "main")
            latest = _git("rev-parse", "origin/main")
            if latest != remote:
                _rebase_and_reprepare(latest)
                remote = latest
                _git("add", "-A")
                _, effective, evidence, constitutional_adr = _evaluate(
                    remote,
                    adr_ref=adr_ref,
                )
                _stage_commit(
                    message,
                    effective=effective,
                    evidence=evidence,
                    constitutional_adr=constitutional_adr,
                )
                continue

            commit = _git("rev-parse", "HEAD")
            candidate = _candidate_branch(commit)
            result = subprocess.run(
                ["git", "push", "origin", f"HEAD:refs/heads/{candidate}"],
                cwd=ROOT,
                check=False,
            )
            if result.returncode == 0:
                try:
                    pr_url = _create_candidate_pr(candidate, commit, effective)
                except (RuntimeError, json.JSONDecodeError) as exc:
                    print(f"candidate: {candidate}")
                    print(f"commit: {commit}")
                    print(f"BLOCKED — {exc}", file=sys.stderr)
                    return 2
                print(f"candidate: {candidate}")
                print(f"commit: {commit}")
                print(f"pull request: {pr_url}")
                print("publication: awaiting GitHub Actions validation and promotion")
                return 0

            print(
                "BLOCKED — candidate push failed; inspect remote policy, credentials or network",
                file=sys.stderr,
            )
            return 2

        print("BLOCKED — main kept changing; rerun agentctl publish", file=sys.stderr)
        return 4
    except subprocess.CalledProcessError as exc:
        print(
            f"BLOCKED — candidate preparation failed with exit code {exc.returncode}",
            file=sys.stderr,
        )
        return 2
    except PermissionError as exc:
        print(f"BLOCKED — {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        print(f"BLOCKED — {exc}", file=sys.stderr)
        return 2

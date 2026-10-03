"""Detached, commit-pinned workspaces for scientific execution."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


@contextmanager
def pinned_worktree(repo: Path, commit: str) -> Iterator[Path]:
    """Create a detached worktree pinned to exactly one commit."""
    repo = repo.resolve()
    root = Path(tempfile.gettempdir()) / "symbiont-lab-worktrees"
    root.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix=f"run-{commit[:10]}-", dir=root))
    shutil.rmtree(path)
    _git(repo, "worktree", "add", "--detach", str(path), commit)
    try:
        actual = _git(path, "rev-parse", "HEAD")
        if actual != commit:
            raise RuntimeError(f"pinned worktree mismatch: {actual} != {commit}")
        yield path
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(path)],
            cwd=repo,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

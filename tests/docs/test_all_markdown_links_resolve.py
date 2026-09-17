from __future__ import annotations

import re
import subprocess

from .conftest import REPO_ROOT

_MARKDOWN_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_FENCE_RE = re.compile(r"^\s*```")


def _tracked_markdown_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_every_markdown_link_in_every_tracked_md_file_resolves():
    """Pattern-independent broken-link check across the whole repo.

    Earlier link-repair tasks in this project each grepped for one specific
    old path string (e.g. ``docs/_internal``) to find references that needed
    fixing after a move/delete. That approach is fragile: a link written
    relative (``../_internal/...``) rather than path-prefixed
    (``docs/_internal/...``) slips past a string grep entirely, as happened
    with a link in docs/design/percepcion-y-embodiment.md pointing at a plan
    file deleted in a later docs cleanup task.

    This test instead parses every markdown link in every git-tracked
    ``*.md`` file in the repo and asserts each local (non-http, non-anchor)
    link resolves to a real file or directory on disk, relative to that
    file's own location. It cannot miss a broken link regardless of what old
    path string someone forgets to grep for.
    """
    broken: list[str] = []
    unbalanced_fences: list[str] = []
    checked = 0

    for rel_path in _tracked_markdown_files():
        doc_path = REPO_ROOT / rel_path
        text = doc_path.read_text(encoding="utf-8")

        in_fence = False
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            for link in _MARKDOWN_LINK_RE.findall(line):
                link = link.strip()
                if not link:
                    continue
                if link.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path_part = link.split("#", 1)[0].strip()
                if not path_part:
                    continue
                if path_part.startswith(("http://", "https://", "mailto:")):
                    continue

                checked += 1
                target = (doc_path.parent / path_part).resolve()
                if not target.exists():
                    broken.append(f"{rel_path}:{lineno}: {link} -> {target}")

        # A single unbalanced ``` fence flips in_fence for the rest of the
        # file and silently skips every link after it, which would make
        # this check pass for the wrong reason. Fail loudly instead.
        if in_fence:
            unbalanced_fences.append(rel_path)

    assert not unbalanced_fences, (
        "unbalanced code fence(s) (odd number of ``` lines) would cause "
        "link-checking to silently skip content in:\n" + "\n".join(unbalanced_fences)
    )
    assert checked > 100, f"expected 100+ resolvable local links repo-wide, found {checked}"
    assert not broken, "broken relative link(s) found:\n" + "\n".join(broken)

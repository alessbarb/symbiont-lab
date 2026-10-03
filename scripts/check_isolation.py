"""Prove each domain library is self-contained, in a real isolated environment.

For every library this creates a virtual environment in a temporary directory
outside the repository, installs only that library with its declared
dependencies, copies the library's tests to an empty directory, and runs them
from there. Nothing of the repository is on `sys.path`, so another domain
cannot be picked up as a namespace package from the working directory.

    python scripts/check_isolation.py              # all four libraries
    python scripts/check_isolation.py embodiment   # one
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARIES = ("symbiont", "embodiment", "modality", "environment")
FIRST_PARTY = (*LIBRARIES, "lab")
TEST_TOOLS = ("pytest", "pytest-xdist", "hypothesis")

PROBE = """
import importlib.util, sys
own, others = sys.argv[1], sys.argv[2:]
assert importlib.util.find_spec(own) is not None, f"{own} is not importable"
visible = [name for name in others if importlib.util.find_spec(name) is not None]
assert not visible, f"other first-party packages are importable: {visible}"
"""


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> int:
    return subprocess.run(command, cwd=cwd, env=env, check=False).returncode


def check(library: str) -> bool:
    with tempfile.TemporaryDirectory(prefix=f"{library}-alone-") as temporary:
        work = Path(temporary)
        if work.is_relative_to(ROOT):
            raise SystemExit("the temporary directory must be outside the repository")
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}
        }
        venv = work / "venv"
        python = venv / "bin" / "python"
        steps = [
            [
                "uv",
                "venv",
                "--quiet",
                "--python",
                f"{sys.version_info[0]}.{sys.version_info[1]}",
                str(venv),
            ],
            [
                "uv",
                "pip",
                "install",
                "--quiet",
                "--python",
                str(python),
                str(ROOT / library),
                *TEST_TOOLS,
            ],
        ]
        for step in steps:
            if run(step, cwd=work, env=environment):
                return False
        suite = work / "suite"
        shutil.copytree(
            ROOT / library / "tests", suite / "tests", ignore=shutil.ignore_patterns("__pycache__")
        )
        others = [name for name in FIRST_PARTY if name != library]
        if run([str(python), "-c", PROBE, library, *others], cwd=suite, env=environment):
            return False
        return (
            run(
                [
                    str(python),
                    "-m",
                    "pytest",
                    "tests",
                    "-o",
                    "addopts=",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                ],
                cwd=suite,
                env=environment,
            )
            == 0
        )


def main(argv: list[str]) -> int:
    unknown = [name for name in argv if name not in LIBRARIES]
    if unknown:
        raise SystemExit(f"unknown library {unknown}; choose from {list(LIBRARIES)}")
    failed = []
    for library in argv or LIBRARIES:
        print(f"=== {library}: installed alone, tested from an isolated directory ===", flush=True)
        if not check(library):
            failed.append(library)
    print("not self-contained: " + (", ".join(failed) if failed else "none"), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Run every test suite of the repository, one pytest session per suite.

The four domain libraries and the Lab each own `<domain>/tests`; `tests/` holds
the repository-wide checks. Extra arguments are passed to every pytest session.

    python scripts/run_tests.py                # everything
    python scripts/run_tests.py symbiont lab   # only these suites
    python scripts/run_tests.py -- -n 8 -q     # with pytest arguments
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITES = {
    "symbiont": ["symbiont/tests"],
    "embodiment": ["embodiment/tests"],
    "modality": ["modality/tests"],
    "environment": ["environment/tests"],
    "lab": ["lab/tests", "lab/src/lab/observatory/tests"],
    "repository": ["tests"],
}


def main(argv: list[str]) -> int:
    names, _, extra = (
        (argv, "", [])
        if "--" not in argv
        else (
            argv[: argv.index("--")],
            "--",
            argv[argv.index("--") + 1 :],
        )
    )
    unknown = [name for name in names if name not in SUITES]
    if unknown:
        raise SystemExit(f"unknown suite(s) {unknown}; choose from {sorted(SUITES)}")
    failed = []
    for name in names or SUITES:
        print(f"=== {name} ===", flush=True)
        command = [sys.executable, "-m", "pytest", *SUITES[name], *extra]
        if subprocess.run(command, cwd=ROOT, check=False).returncode not in (0, 5):
            failed.append(name)
    print("failed suites: " + (", ".join(failed) if failed else "none"), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

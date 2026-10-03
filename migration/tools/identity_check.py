"""Organism identity across the layout change: old code vs new code.

Saves an organism with one source tree and restores it with the other, in
separate interpreters, and compares state hashes and serialized checkpoints.

Usage:
    git archive 593c2a02 src | tar -x -C /tmp/old
    python migration/tools/identity_check.py --old /tmp/old/src
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = os.pathsep.join(
    str(ROOT / domain / "src")
    for domain in ("symbiont", "environment", "modality", "embodiment", "lab")
)

CHILD = r"""
import json, sys
import symbiont
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.checkpoint import checkpoint_state_hash, load_checkpoint_file
mode, path = sys.argv[1], sys.argv[2]
if mode == "create":
    organism = OrganismRuntime(min_samples=1, investigate_ticks=0)
    organism.run(int(sys.argv[3]))
    organism.save(path)
else:
    organism = OrganismRuntime.load_or_create(path, min_samples=1, investigate_ticks=0)
    if mode == "resave":
        organism.save(sys.argv[3])
payload = load_checkpoint_file(path)
print(json.dumps({
    "code": symbiont.__file__,
    "state_hash": organism.state_hash(),
    "checkpoint_hash": checkpoint_state_hash(payload),
    "schema_version": payload.get("schema_version"),
    "fields": sorted(payload),
    "lineage": payload.get("checkpoint_lineage"),
}))
"""


def run(pythonpath: str, *args: str) -> dict:
    env = {**os.environ, "PYTHONPATH": pythonpath, "PYTHONDONTWRITEBYTECODE": "1"}
    out = subprocess.run(
        [sys.executable, "-c", CHILD, *args], env=env, check=True, capture_output=True, text=True
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--old", required=True, type=Path, help="old layout src/ directory")
    parser.add_argument("--ticks", default="5")
    args = parser.parse_args()
    old = str(args.old.resolve())
    failures = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}{'  ' + detail if detail else ''}")

    with tempfile.TemporaryDirectory() as tmp:
        a, b, c = (str(Path(tmp) / name) for name in ("old.json", "new.json", "resaved.json"))

        saved_old = run(old, "create", a, args.ticks)
        check("old code resolved from old tree", saved_old["code"].startswith(old))
        in_old = run(old, "load", a)
        in_new = run(NEW, "load", a)
        check("new code resolved from new tree", in_new["code"].startswith(str(ROOT)))
        check("old save -> old load", in_old["state_hash"] == saved_old["state_hash"])
        check(
            "old save -> new load: same state hash",
            in_new["state_hash"] == saved_old["state_hash"],
            saved_old["state_hash"][:16],
        )
        check("old save -> new load: same serialized fields", in_new["fields"] == in_old["fields"])
        check("old save -> new load: lineage preserved", in_new["lineage"] == in_old["lineage"])

        # A re-save advances checkpoint lineage by design, so the comparison is
        # old-code re-save against new-code re-save of the same checkpoint.
        d = str(Path(tmp) / "resaved-by-old.json")
        run(old, "resave", a, d)
        resaved = run(NEW, "resave", a, c)
        check(
            "re-save by old code == re-save by new code (bytes)",
            Path(d).read_bytes() == Path(c).read_bytes(),
        )
        check("resave keeps state hash", resaved["state_hash"] == saved_old["state_hash"])

        saved_new = run(NEW, "create", b, args.ticks)
        check("new save -> new load", run(NEW, "load", b)["state_hash"] == saved_new["state_hash"])
        check(
            "new save -> old load: same state hash",
            run(old, "load", b)["state_hash"] == saved_new["state_hash"],
        )
        check(
            "checkpoint schema unchanged",
            saved_new["schema_version"] == saved_old["schema_version"],
            f"schema {saved_new['schema_version']}",
        )
        check("serialized field set unchanged", saved_new["fields"] == saved_old["fields"])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

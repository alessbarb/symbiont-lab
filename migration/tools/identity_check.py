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
from symbiont.core import organism_profile
mode, path = sys.argv[1], sys.argv[2]
if sys.argv[-1] == "composed":
    # new tree: the Lab composes the organism's sense sources
    from lab.integration.organism import (
        create_canonical_organism as create,
        load_or_create_canonical_organism as load_or_create,
        restore_canonical_organism as restore,
    )
else:
    # old tree: the organism built its own
    create, load_or_create = OrganismRuntime, OrganismRuntime.load_or_create
    restore = OrganismRuntime.from_checkpoint

def options(stated):
    return {
        key: getattr(organism_profile, value) if key == "profile" else value
        for key, value in stated.items()
    }

if mode == "matrix":
    cases, overrides = json.loads(path)
    hashes = {}
    for name, stated in cases.items():
        born = create(organism_id="identity-matrix", **options(stated))
        hashes[name] = [born.state_hash(), born.checkpoint(advance_lineage=False)]
        payload = born.checkpoint()
        for other, override in overrides.items():
            restored = restore(payload, **options(override))
            hashes[f"{name} / {other}"] = [
                restored.state_hash(), restored.checkpoint(advance_lineage=False)
            ]
    print(json.dumps(hashes))
    sys.exit(0)
if mode == "create":
    organism = create(min_samples=1, investigate_ticks=0)
    organism.run(int(sys.argv[3]))
    organism.save(path)
else:
    organism = load_or_create(path, min_samples=1, investigate_ticks=0)
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


# stdlib/discovery combinations, interoception on/sham/off, both profiles
CASES = {
    "canonical": {},
    "historical-v0": {"profile": "HISTORICAL_V0"},
    "v1": {"profile": "V1"},
    "interoception": {"interoception_mode": "enabled", "discover_senses": True},
    "sham": {"interoception_mode": "sham", "discover_senses": True},
    "absent": {"interoception_enabled": False, "discover_senses": True},
    "both": {"discover_senses": True, "bootstrap_semantic_senses": True},
    "bootstrap": {"discover_senses": False, "bootstrap_semantic_senses": True},
    "no-senses": {"discover_senses": False, "bootstrap_semantic_senses": False},
}
# what a restore may state differently from what the checkpoint recorded
OVERRIDES = {
    "recorded-controls": {},
    "discovery-off": {"discover_senses": False},
    "interoception-on": {"discover_senses": True, "interoception_mode": "enabled"},
    "bootstrap": {"bootstrap_semantic_senses": True},
    "interoception-off": {"interoception_enabled": False},
    "profile": {"profile": "V1"},
}


def run(pythonpath: str, *args: str) -> dict:
    env = {**os.environ, "PYTHONPATH": pythonpath, "PYTHONDONTWRITEBYTECODE": "1"}
    out = subprocess.run(
        [sys.executable, "-c", CHILD, *args, *(["composed"] if pythonpath == NEW else [])],
        env=env, check=True, capture_output=True, text=True
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

        # The old organism built its own sense sources; the new one is given
        # them by the Lab. Same organism for every option set, born or restored.
        matrix = json.dumps([CASES, OVERRIDES])
        by_old, by_new = run(old, "matrix", matrix), run(NEW, "matrix", matrix)
        differing = sorted(name for name in by_old if by_old[name] != by_new.get(name))
        check(
            f"composed by the Lab == self-built by the old organism ({len(by_old)} cases)",
            not differing and len(by_old) == len(by_new),
            ", ".join(differing[:5]),
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

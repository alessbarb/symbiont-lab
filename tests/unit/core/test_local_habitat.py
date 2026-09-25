from __future__ import annotations

import json
import time
from pathlib import Path

from symbiont.core.capsule import CapsuleKeyPair, create_capsule
from symbiont.core.local_habitat import LocalHabitat


def test_publish_and_poll_capsules(tmp_path: Path):
    habitat = LocalHabitat(tmp_path)
    key_a = CapsuleKeyPair.generate()
    key_b = CapsuleKeyPair.generate()

    capsule_a = create_capsule(key_a, {"sender": "a", "stat": 42.0})
    capsule_b = create_capsule(key_b, {"sender": "b", "stat": 99.0})

    path_a = habitat.publish_capsule(capsule_a)
    path_b = habitat.publish_capsule(capsule_b)

    assert path_a is not None and path_a.is_file()
    assert path_b is not None and path_b.is_file()

    # Poll excluding signer A -> should return only capsule B
    polled_for_a = habitat.poll_capsules(exclude_signer=key_a.public_bytes)
    assert len(polled_for_a) == 1
    assert polled_for_a[0].payload["sender"] == "b"

    # Poll excluding signer B -> should return only capsule A
    polled_for_b = habitat.poll_capsules(exclude_signer=key_b.public_bytes)
    assert len(polled_for_b) == 1
    assert polled_for_b[0].payload["sender"] == "a"


def test_tampered_capsules_are_rejected(tmp_path: Path):
    habitat = LocalHabitat(tmp_path)
    key = CapsuleKeyPair.generate()
    capsule = create_capsule(key, {"claim": "original"})

    target = habitat.publish_capsule(capsule)
    assert target is not None

    # Tamper with the saved JSON on disk
    data = json.loads(target.read_text(encoding="utf-8"))
    data["payload"]["claim"] = "forged"
    target.write_text(json.dumps(data), encoding="utf-8")

    # Poll should filter out forged capsule
    polled = habitat.poll_capsules()
    assert len(polled) == 0


def test_circular_retention_capsules(tmp_path: Path):
    habitat = LocalHabitat(tmp_path, max_capsules=2)
    key = CapsuleKeyPair.generate()

    cap1 = create_capsule(key, {"seq": 1})
    cap2 = create_capsule(key, {"seq": 2})
    cap3 = create_capsule(key, {"seq": 3})

    habitat.publish_capsule(cap1)
    time.sleep(0.01)
    habitat.publish_capsule(cap2)
    time.sleep(0.01)
    habitat.publish_capsule(cap3)

    remaining_files = list(habitat.capsules_dir.glob("*.json"))
    assert len(remaining_files) <= 2


def test_deposit_and_count_incubated(tmp_path: Path):
    habitat = LocalHabitat(tmp_path)
    assert habitat.count_incubated() == 0

    embryo = {"organism_id": "child-1", "generation": 2}
    path = habitat.deposit_embryo(embryo, "child-1")

    assert path is not None and path.is_file()
    assert habitat.count_incubated() == 1

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["organism_id"] == "child-1"
    assert saved["generation"] == 2

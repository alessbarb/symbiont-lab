from __future__ import annotations

from pathlib import Path

import pytest

from symbiont_lab.experiments.generations import GenerationStore


def _files(label: str) -> dict[str, bytes | str]:
    return {
        "checkpoint": f"checkpoint-{label}",
        "manifest": f'{{"label":"{label}"}}',
        "provenance/runtime.txt": f"runtime-{label}",
        "model-artifacts/model.bin": f"model-{label}".encode(),
        "telemetry-index": f"telemetry-{label}",
    }


def test_generation_store_commits_complete_generation(tmp_path: Path) -> None:
    store = GenerationStore(tmp_path / "run")

    committed = store.commit(0, _files("zero"))

    assert committed.index == 0
    assert committed.path.name == "generation-000000"
    assert (committed.path / "COMPLETE").is_file()
    assert (store.root / "CURRENT").read_text(encoding="utf-8") == "generation-000000\n"
    assert set(committed.files) == set(_files("zero"))
    assert store.open_current() == committed


@pytest.mark.parametrize(
    "fault_point,expected_index",
    [
        ("before_generation_publish", 0),
        ("after_generation_publish", 0),
        ("current.before_write", 0),
        ("current.during_write", 0),
        ("current.before_file_fsync", 0),
        ("current.after_file_fsync", 0),
        ("current.before_replace", 0),
        ("current.after_replace", 1),
        ("current.before_dir_fsync", 1),
        ("current.after_dir_fsync", 1),
        ("after_current_publish", 1),
    ],
)
def test_generation_crash_leaves_previous_or_complete_new_generation(
    tmp_path: Path, fault_point: str, expected_index: int
) -> None:
    store = GenerationStore(tmp_path / "run")
    store.commit(0, _files("zero"))

    def fault_hook(point: str) -> None:
        if point == fault_point:
            raise OSError(f"simulated crash at {point}")

    with pytest.raises(OSError, match="simulated crash"):
        store.commit(1, _files("one"), _fault_point=fault_hook)

    current = store.open_current()
    assert current.index == expected_index
    expected_label = "zero" if expected_index == 0 else "one"
    assert (current.path / "checkpoint").read_text(encoding="utf-8") == (
        f"checkpoint-{expected_label}"
    )


def test_unreferenced_complete_generation_is_not_current(tmp_path: Path) -> None:
    store = GenerationStore(tmp_path / "run")
    store.commit(0, _files("zero"))

    def fault_hook(point: str) -> None:
        if point == "after_generation_publish":
            raise OSError("stop before CURRENT")

    with pytest.raises(OSError, match="stop before CURRENT"):
        store.commit(1, _files("one"), _fault_point=fault_hook)

    assert (store.root / "generation-000001" / "COMPLETE").is_file()
    assert store.open_current().index == 0


def test_generation_store_rejects_corrupted_current_payload(tmp_path: Path) -> None:
    store = GenerationStore(tmp_path / "run")
    committed = store.commit(0, _files("zero"))
    (committed.path / "checkpoint").write_text("corrupted", encoding="utf-8")

    with pytest.raises(ValueError, match="digest mismatch"):
        store.open_current()


def test_generation_store_rejects_mixed_file_set(tmp_path: Path) -> None:
    store = GenerationStore(tmp_path / "run")
    committed = store.commit(0, _files("zero"))
    (committed.path / "unexpected").write_text("mixed", encoding="utf-8")

    with pytest.raises(ValueError, match="file set mismatch"):
        store.open_current()


@pytest.mark.parametrize(
    "path",
    ["../escape", "/absolute", "COMPLETE", "CURRENT", "nested/COMPLETE", "nested/CURRENT"],
)
def test_generation_store_rejects_unsafe_payload_paths(tmp_path: Path, path: str) -> None:
    store = GenerationStore(tmp_path / "run")

    with pytest.raises(ValueError):
        store.commit(0, {path: "payload"})

"""Guard the boundary between executable tests and scientific runs."""
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
TESTS = REPO_ROOT / "tests"
EXPERIMENTS = REPO_ROOT / "experiments"
REQUIRED_TEST_DIRS = {
    "unit",
    "integration",
    "contract",
    "experimental_integrity",
    "regression",
    "smoke",
    "docs",
    "observatory",
    "experiments",
    "experiments/protocols",
    "experiments/runners",
    "experiments/pilots",
}


def _meaningful_readme(path: Path) -> bool:
    text = (path / "README.md").read_text(encoding="utf-8") if (path / "README.md").exists() else ""
    lowered = text.lower()
    return len(text.strip()) >= 180 and all(
        marker in lowered
        for marker in ("## purpose", "## belongs here", "## does not belong here", "## criterion for creating a file", "## execution", "## limits")
    )


def test_expected_test_layers_have_specific_readmes() -> None:
    missing = [name for name in sorted(REQUIRED_TEST_DIRS) if not _meaningful_readme(TESTS / name)]
    assert not missing, f"test layers without a specific README: {missing}"


def test_every_directory_containing_tests_has_a_readme() -> None:
    dirs = {path.parent for path in TESTS.rglob("test_*.py") if "__pycache__" not in path.parts}
    missing = sorted(str(path.relative_to(REPO_ROOT)) for path in dirs if not _meaningful_readme(path))
    assert not missing, f"test directories without README: {missing}"


def test_experiment_directories_with_protocol_content_have_readmes() -> None:
    dirs = {
        path.parent
        for path in EXPERIMENTS.rglob("*")
        if path.is_file() and path.name not in {"README.md"} and "__pycache__" not in path.parts
    }
    missing = sorted(str(path.relative_to(REPO_ROOT)) for path in dirs if not _meaningful_readme(path))
    assert not missing, f"experiment directories without README: {missing}"


def test_experiments_contain_no_pytest_files() -> None:
    misplaced = sorted(
        str(path.relative_to(REPO_ROOT))
        for path in EXPERIMENTS.rglob("test_*.py")
        if "__pycache__" not in path.parts
    )
    assert not misplaced, f"pytest files must live under tests/: {misplaced}"

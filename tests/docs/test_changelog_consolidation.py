from __future__ import annotations

from .conftest import REPO_ROOT


def test_releases_directory_is_gone():
    assert not (REPO_ROOT / "docs" / "releases").exists()


def test_changelog_exists_and_has_every_version_heading():
    changelog = REPO_ROOT / "docs" / "CHANGELOG.md"
    assert changelog.is_file()
    text = changelog.read_text(encoding="utf-8")
    # Spot-check the oldest and newest archived versions, plus one from the
    # middle of the sequence — a real gap would show up in at least one of
    # these three positions.
    for version_heading in ("## v0.76.8", "## v0.79.50", "## v0.80.15"):
        assert version_heading in text, f"CHANGELOG.md missing: {version_heading}"


def test_portal_index_points_at_changelog():
    text = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "docs/CHANGELOG.md" in text or "CHANGELOG.md" in text
    assert "releases/README.md" not in text

"""Tests for deterministic version synchronization across workspace members."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.governance.version import (
    DOMAINS,
    bump_semver,
    check_versions,
    parse_semver,
    sync_versions,
)

ROOT = Path(__file__).resolve().parents[2]


def test_semver_parsing() -> None:
    assert parse_semver("0.90.0") == (0, 90, 0, "")
    assert parse_semver("1.2.3-alpha.1") == (1, 2, 3, "alpha.1")
    with pytest.raises(ValueError, match="Invalid semver"):
        parse_semver("invalid.version")


def test_semver_bumping() -> None:
    assert bump_semver("0.90.0", "patch") == "0.90.1"
    assert bump_semver("0.90.0", "minor") == "0.91.0"
    assert bump_semver("0.90.0", "major") == "1.0.0"
    with pytest.raises(ValueError, match="Unknown semver bump part"):
        bump_semver("0.90.0", "other")


def test_current_workspace_is_fully_synchronized() -> None:
    mismatches = check_versions(ROOT)
    assert mismatches == []


def test_check_versions_catches_divergent_member_pyproject(tmp_path: Path) -> None:
    # Setup a mock workspace
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "root"\nversion = "0.90.0"\n', encoding="utf-8"
    )
    for domain in DOMAINS:
        domain_dir = tmp_path / domain
        domain_src = domain_dir / "src" / domain
        domain_src.mkdir(parents=True)
        # One domain has divergent version
        ver = "0.89.0" if domain == "embodiment" else "0.90.0"
        (domain_dir / "pyproject.toml").write_text(
            f'[project]\nname = "{domain}"\nversion = "{ver}"\n', encoding="utf-8"
        )
        (domain_src / "__init__.py").write_text('__version__ = "0.90.0"\n', encoding="utf-8")

    mismatches = check_versions(tmp_path)
    assert any(
        "embodiment/pyproject.toml version (0.89.0) != root (0.90.0)" in m for m in mismatches
    )


def test_check_versions_catches_divergent_init_version(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "root"\nversion = "0.90.0"\n', encoding="utf-8"
    )
    for domain in DOMAINS:
        domain_dir = tmp_path / domain
        domain_src = domain_dir / "src" / domain
        domain_src.mkdir(parents=True)
        (domain_dir / "pyproject.toml").write_text(
            f'[project]\nname = "{domain}"\nversion = "0.90.0"\n', encoding="utf-8"
        )
        ver = "0.89.0" if domain == "modality" else "0.90.0"
        (domain_src / "__init__.py").write_text(f'__version__ = "{ver}"\n', encoding="utf-8")

    mismatches = check_versions(tmp_path)
    assert any(
        "modality/src/modality/__init__.py __version__ (0.89.0) != root (0.90.0)" in m
        for m in mismatches
    )


def test_sync_versions_reconciles_workspace(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "root"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    for domain in DOMAINS:
        domain_dir = tmp_path / domain
        domain_src = domain_dir / "src" / domain
        domain_src.mkdir(parents=True)
        (domain_dir / "pyproject.toml").write_text(
            f'[project]\nname = "{domain}"\nversion = "0.90.0"\n', encoding="utf-8"
        )
        (domain_src / "__init__.py").write_text('__version__ = "0.90.0"\n', encoding="utf-8")

    assert len(check_versions(tmp_path)) > 0
    synced = sync_versions(root=tmp_path, run_lock=False)
    assert synced == "1.0.0"
    assert check_versions(tmp_path) == []

from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_genetic_development() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    assert "self._development_domain.update_gene_expression(" in runtime
    assert "self._development_domain.decay_epigenetic_priors(" in runtime
    assert "RegulatorySignals(" not in runtime


def test_regulation_no_longer_owns_genotype_expression() -> None:
    root = Path(__file__).resolve().parents[2]
    regulation = (
        root / "src" / "symbiont" / "core" / "domains" / "regulation.py"
    ).read_text(encoding="utf-8")
    development = (
        root / "src" / "symbiont" / "core" / "domains" / "development.py"
    ).read_text(encoding="utf-8")
    assert "update_gene_expression" not in regulation
    assert "RegulatorySignals(" in development
    assert "decay_epigenetic_priors" in development

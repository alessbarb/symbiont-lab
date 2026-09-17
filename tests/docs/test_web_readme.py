from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAPTERS = [
    "01-que-es-un-symbiont.md",
    "02-cuerpo-y-percepcion.md",
    "03-cognicion-y-plasticidad.md",
    "04-atencion-y-decision.md",
    "05-fisiologia.md",
    "06-reproduccion-y-linaje.md",
    "07-ecologia-y-sociabilidad.md",
    "08-desarrollo-predictivo.md",
    "09-metodologia-y-limites.md",
]


def test_readme_lists_every_chapter_and_three_reading_paths():
    text = (REPO_ROOT / "docs" / "web" / "README.md").read_text(encoding="utf-8")
    for chapter in CHAPTERS:
        assert chapter in text, f"README missing link to {chapter}"
    for path_name in ("Lector curioso", "Investigador", "Implementador"):
        assert path_name in text, f"README missing reading path: {path_name}"
    assert "milestone" not in text.lower(), "no project-management vocabulary in docs/web/"

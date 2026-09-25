import json
import os
import re


def validate():
    meta_dir = os.path.dirname(__file__)
    inventory_path = os.path.join(meta_dir, "document-inventory.json")
    redirects_path = os.path.join(meta_dir, "redirects.json")
    glossary_path = os.path.join(meta_dir, "translation-glossary.json")

    with open(inventory_path, "r", encoding="utf-8") as f:
        inventory = json.load(f)

    with open(redirects_path, "r", encoding="utf-8") as f:
        redirects = json.load(f)

    with open(glossary_path, "r", encoding="utf-8") as f:
        glossary = json.load(f)

    # --- 1. GLOSSARY INVARIANTS ---
    for k in [
        "canonical_terms",
        "code_identifiers",
        "cli_commands",
        "configuration_keys",
        "schema_fields",
        "event_names",
        "telemetry_fields",
        "never_modify_patterns",
    ]:
        assert isinstance(glossary[k], list), f"{k} is not a list"
        assert len(glossary[k]) == len(set(glossary[k])), f"Duplicates found in {k}"
        for item in glossary[k]:
            assert item.strip() != "", f"Empty string in {k}"

    for pat in glossary["never_modify_patterns"]:
        try:
            re.compile(pat)
        except re.error as e:
            assert False, f"Invalid regex pattern in glossary: {pat} -> {e}"

    assert isinstance(glossary["contextual_terms"], dict)
    for k, v in glossary["contextual_terms"].items():
        assert isinstance(v, dict), f"contextual_term {k} is not a struct"

    # --- 2. INVENTORY INVARIANTS ---
    ids = [e["canonical_id"] for e in inventory]
    assert len(inventory) == 163
    assert len(set(ids)) == 163

    spanish_blocklist = [
        "y",
        "de",
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "en",
        "para",
        "con",
        "sin",
        "por",
        "sobre",
        "entre",
        "fisiologia",
        "cognicion",
        "atencion",
        "ecologia",
        "reproduccion",
        "cuerpo",
        "futuro",
        "agentes",
        "metacognicion",
        "presupuestos",
        "automodelo",
        "sensores",
        "adaptativos",
        "percepcion",
        "aclimatacion",
        "relaciones",
        "deteccion",
        "deriva",
        "regimenes",
        "seleccion",
        "evaluacion",
        "estadistica",
        "creencias",
        "disidencia",
        "sociabilidad",
        "linaje",
        "fuentes",
        "metodologia",
        "limites",
        "plasticidad",
        "herencia",
    ]

    for entry in inventory:
        assert entry["document_type"] != "unknown"
        assert not entry["canonical_id"].startswith("todo.")

        # Taxonomy bounds
        assert (
            entry["target_path"].startswith("docs/")
            or entry["target_path"].startswith("research/")
            or entry["target_path"] in ["README.md", "CLAUDE.md", "AGENTS.md", "ORGANISM.md"]
        )

        # docs/web mapped to docs/explanation/concepts
        assert "docs/web/" not in entry["target_path"], (
            f"docs/web/ found in target_path: {entry['target_path']}"
        )

        # English translation of paths
        basename = os.path.basename(entry["target_path"])
        words = basename.replace(".md", "").split("-")
        for w in words:
            w_clean = w.lower()
            assert w_clean not in spanish_blocklist, (
                f"Target path contains Spanish token '{w_clean}': {entry['target_path']}"
            )

        # Check coherence
        if entry["canonical"]:
            assert entry["status"] == "active"
        if entry["status"] == "superseded":
            assert not entry["canonical"]

        for rel in ["supersedes", "superseded_by", "depends_on", "extends", "implements"]:
            if rel in entry:
                for target in entry[rel]:
                    assert target in ids, f"Broken relation: {target}"

    # --- 3. REDIRECTS INVARIANTS ---
    source_paths = {e["current_path"] for e in inventory}
    target_paths = [e["target_path"] for e in inventory]

    assert len(redirects) == len(set(redirects.keys())), "Duplicate source paths in redirects"

    # Exact equivalence check
    expected_redirects = {
        e["current_path"]: e["target_path"]
        for e in inventory
        if e["current_path"] != e["target_path"]
    }
    assert redirects == expected_redirects, (
        "Redirects do not match exact difference between current and target paths"
    )

    for src, targ in redirects.items():
        assert src in source_paths
        assert targ in target_paths

    from collections import Counter

    target_counts = Counter(target_paths)
    for targ, count in target_counts.items():
        assert count == 1, f"Collision detected: {count} documents resolve to target_path: {targ}"

    print("ALL Phase 1 Validations Passed!")


if __name__ == "__main__":
    validate()

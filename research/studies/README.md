# Frozen Research Studies

This directory contains validated and frozen scientific findings that serve as baselines for published research.

## Structure of a Frozen Study
Each frozen study folder follows the pattern:
```text
research/studies/<YYYY-MM-study-name>/
├── PROTOCOL.md
├── ANALYSIS.md
├── MANIFEST.json
├── RESULTS.json
└── checksums.txt
```

Unlike `.symbiont/runs/` (which serves as mutable working scratch space), entries here are permanent scientific artifacts.

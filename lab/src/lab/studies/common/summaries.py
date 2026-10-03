from __future__ import annotations

from typing import Any


def format_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Format headers and rows into a clean GitHub-flavored markdown table."""
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    header_line = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    separator_line = "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |"
    data_lines = [
        "| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |"
        for row in str_rows
    ]
    return "\n".join([header_line, separator_line] + data_lines)

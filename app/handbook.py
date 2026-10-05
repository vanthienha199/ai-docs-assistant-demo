"""Turn a handbook passage into the HTML the source pane prints.

The documents are plain markdown with paragraphs, one bullet list and one price
table, so a full markdown library would be more dependency than the job needs.
"""

from __future__ import annotations

import html
import re


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _table(rows: list[str]) -> str:
    head, body = _cells(rows[0]), [r for r in rows[2:] if r.strip()]
    columns = len(head)
    out = ["<table><thead><tr>"]
    for i, cell in enumerate(head):
        klass = ' class="num"' if i else ""
        out.append(f"<th{klass}>{html.escape(cell)}</th>")
    out.append("</tr></thead><tbody>")
    for row in body:
        values = (_cells(row) + [""] * columns)[:columns]
        out.append("<tr>")
        for i, cell in enumerate(values):
            klass = ' class="num"' if i else ""
            out.append(f"<td{klass}>{html.escape(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def to_html(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    buffer: list[str] = []
    mode = ""

    def flush() -> None:
        nonlocal buffer, mode
        if not buffer:
            mode = ""
            return
        if mode == "table":
            out.append(_table(buffer))
        elif mode == "list":
            items = "".join(
                f"<li>{html.escape(re.sub(r'^[-*]\s+', '', item))}</li>" for item in buffer
            )
            out.append(f"<ul>{items}</ul>")
        else:
            out.append("<p>" + html.escape(" ".join(buffer)) + "</p>")
        buffer = []
        mode = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("|"):
            if mode != "table":
                flush()
                mode = "table"
            buffer.append(stripped)
        elif re.match(r"^[-*]\s+", stripped):
            if mode != "list":
                flush()
                mode = "list"
            buffer.append(stripped)
        else:
            if mode not in ("", "para"):
                flush()
            mode = "para"
            buffer.append(stripped)
    flush()
    return "".join(out)

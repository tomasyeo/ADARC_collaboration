"""Render exploratory PI co-participation views from the maintained TSV.

Run from the repository root: python3 prototypes/pi_projection.py
Requires the Graphviz `dot` and `sfdp` commands on PATH.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from html import escape
from itertools import combinations
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_source" / "project_participant.txt"
OUTPUT = Path(__file__).resolve().parent / "output"
MIN_NETWORK_WEIGHT = 2


def quoted(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def graphviz_html(value: str) -> str:
    return escape(value, quote=True)


def read_projection() -> tuple[list[str], dict[str, set[str]], Counter[tuple[str, str]]]:
    projects: dict[str, set[str]] = defaultdict(set)
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        if rows.fieldnames != ["project", "participant"]:
            raise ValueError("Expected project and participant TSV columns")
        for row in rows:
            projects[row["project"]].add(row["participant"])

    names = sorted({name for team in projects.values() for name in team}, key=str.casefold)
    shared_projects: Counter[tuple[str, str]] = Counter(
        pair for team in projects.values() for pair in combinations(sorted(team), 2)
    )
    return names, projects, shared_projects


def matrix_cell(count: int, *, diagonal: bool = False) -> tuple[str, str]:
    if diagonal:
        return "#d9d2f1", "#222138"
    if count == 0:
        return "#f1f4f7", "#7b8792"
    if count == 1:
        return "#d3eeec", "#173e40"
    if count <= 3:
        return "#8acdc8", "#123c3d"
    if count <= 7:
        return "#347e84", "#ffffff"
    return "#164f69", "#ffffff"


def render_matrix(names: list[str], projects: dict[str, set[str]], weights: Counter) -> str:
    totals = Counter(name for team in projects.values() for name in team)
    lines = [
        "digraph matrix {",
        '  graph [bgcolor="white", margin="0.20"];',
        '  node [shape=plain, fontname="Helvetica"];',
        "  matrix [label=<",
        '    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" COLOR="#d5dfe4">',
        f'      <TR><TD COLSPAN="{len(names) + 1}" BGCOLOR="#112d40" ALIGN="LEFT"><FONT COLOR="white" POINT-SIZE="18"><B>PI × PI: projects in common</B></FONT></TD></TR>',
        f'      <TR><TD COLSPAN="{len(names) + 1}" ALIGN="LEFT"><FONT POINT-SIZE="11">Rows use full names; numbered columns follow the same order. Diagonal = projects per PI.</FONT></TD></TR>',
        '      <TR><TD BGCOLOR="#e7ecf0"><B>PI / column</B></TD>',
    ]
    for column in range(1, len(names) + 1):
        lines.append(f'        <TD BGCOLOR="#e7ecf0" WIDTH="35"><B>{column:02}</B></TD>')
    lines.append("      </TR>")
    for row_number, row_name in enumerate(names, 1):
        lines.append(f'      <TR><TD BGCOLOR="#e7ecf0" ALIGN="LEFT"><B>{row_number:02}  {graphviz_html(row_name)}</B></TD>')
        for column_name in names:
            diagonal = row_name == column_name
            count = totals[row_name] if diagonal else weights[tuple(sorted((row_name, column_name)))]
            background, foreground = matrix_cell(count, diagonal=diagonal)
            lines.append(
                f'        <TD BGCOLOR="{background}" WIDTH="35">'
                f'<FONT COLOR="{foreground}">{count if count else "·"}</FONT></TD>'
            )
        lines.append("      </TR>")
    lines.extend(
        [
            f'      <TR><TD COLSPAN="{len(names) + 1}" ALIGN="LEFT"><FONT POINT-SIZE="11">Off diagonal: 0  ·     1  light teal     2–3  medium teal     4–7  dark teal     8+  navy. Purple diagonal: own project count.</FONT></TD></TR>',
            f'      <TR><TD COLSPAN="{len(names) + 1}" ALIGN="LEFT"><FONT POINT-SIZE="10">{len(projects)} projects · {len(names)} PIs · {sum(len(team) for team in projects.values())} participations · {len(weights)} PI pairs with at least one shared project</FONT></TD></TR>',
            "    </TABLE>",
            "  >];",
            "}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_network(names: list[str], projects: dict[str, set[str]], weights: Counter) -> str:
    totals = Counter(name for team in projects.values() for name in team)
    displayed = {pair: count for pair, count in weights.items() if count >= MIN_NETWORK_WEIGHT}
    linked_names = {name for pair in displayed for name in pair}
    lines = [
        "graph network {",
        '  graph [bgcolor="white", overlap=false, splines=true, sep="+18", pad="0.35",',
        '         outputorder=edgesfirst, fontname="Helvetica", fontsize=18, fontcolor="#112d40",',
        f'         label="PI co-participation · shared projects ≥ {MIN_NETWORK_WEIGHT}\\n'
        f'{len(linked_names)} of {len(names)} PIs shown; omitted PIs have only one-project ties", labelloc=t];',
        '  node [shape=ellipse, style=filled, fillcolor="#d3eeec", color="#256d75",',
        '        fontname="Helvetica", fontsize=11, fontcolor="#102b3b", margin="0.14,0.08"];',
        '  edge [color="#6b98a0", fontname="Helvetica", fontsize=10, fontcolor="#274950"];',
    ]
    for name in names:
        if name not in linked_names:
            continue
        lines.append(
            f'  {quoted(name)} [ '
            f'tooltip={quoted(f"{name}: {totals[name]} projects")}];'
        )
    for (first, second), count in sorted(displayed.items()):
        width = min(5.5, 1.1 + 0.36 * count)
        color = "#18536a" if count >= 4 else "#75a4aa"
        lines.append(
            f'  {quoted(first)} -- {quoted(second)} '
            f'[label={quoted(str(count))}, penwidth={width:.2f}, color="{color}", '
            f'len={max(0.9, 2.1 - 0.08 * count):.2f}, '
            f'tooltip={quoted(f"{count} shared projects")}];'
        )
    lines.extend(
        [
            '  graph [tooltip="Nodes: PIs. Edge labels: number of shared projects."];',
            "}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_and_render(stem: str, source: str, engine: str) -> None:
    dot_file = OUTPUT / f"{stem}.dot"
    dot_file.write_text(source, encoding="utf-8")
    for format_name in ("svg", "png"):
        subprocess.run(
            [engine, f"-T{format_name}", str(dot_file), "-o", str(OUTPUT / f"{stem}.{format_name}")],
            check=True,
        )


def main() -> None:
    names, projects, weights = read_projection()
    OUTPUT.mkdir(exist_ok=True)
    write_and_render("pi_pi_matrix", render_matrix(names, projects, weights), "dot")
    write_and_render("pi_pi_network_min2", render_network(names, projects, weights), "sfdp")
    print(
        f"Rendered {len(names)} PIs, {len(projects)} projects, {len(weights)} pairwise ties; "
        f"{sum(count >= MIN_NETWORK_WEIGHT for count in weights.values())} network edges shown."
    )


if __name__ == "__main__":
    main()

"""Explore recorded project–PI participation with a matrix and bipartite graph."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from data_model import CollaborationData, SourceError, load_data
from network_component import render_network


SOURCE = Path(__file__).with_name("project_participant.txt")
TEAL = "#087F75"
GOLD = "#D88900"


def short_label(label: str, limit: int = 30) -> str:
    return label if len(label) <= limit else label[: limit - 1].rstrip() + "…"


def matrix_figure(data: CollaborationData, selection: tuple[str, str] | None) -> go.Figure:
    projects = data.matrix.index.tolist()
    participants = data.matrix.columns.tolist()
    custom = [[[project, pi] for pi in participants] for project in projects]
    figure = go.Figure(
        go.Heatmap(
            x=list(range(len(participants))),
            y=list(range(len(projects))),
            z=data.matrix.to_numpy(),
            customdata=custom,
            colorscale=[[0, "#F0F3F5"], [0.499, "#F0F3F5"], [0.5, TEAL], [1, TEAL]],
            zmin=0,
            zmax=1,
            showscale=False,
            xgap=2,
            ygap=2,
            hovertemplate=(
                "Project: %{customdata[0]}<br>"
                "PI: %{customdata[1]}<br>"
                "Recorded participation: %{z}<extra></extra>"
            ),
        )
    )
    if selection:
        kind, name = selection
        if kind == "Project":
            row = projects.index(name)
            bounds = (-0.5, len(participants) - 0.5, row - 0.5, row + 0.5)
        else:
            column = participants.index(name)
            bounds = (column - 0.5, column + 0.5, -0.5, len(projects) - 0.5)
        figure.add_shape(
            type="rect", x0=bounds[0], x1=bounds[1], y0=bounds[2], y1=bounds[3],
            line=dict(color=GOLD, width=4), fillcolor="rgba(0,0,0,0)",
        )
    figure.update_layout(
        height=max(650, len(projects) * 29 + 150),
        margin=dict(l=10, r=10, t=25, b=20),
        plot_bgcolor="white",
        xaxis=dict(
            tickmode="array", tickvals=list(range(len(participants))),
            ticktext=[short_label(name, 20) for name in participants],
            tickangle=-50, side="top", title="PIs",
            range=[-0.5, len(participants) - 0.5], fixedrange=False,
        ),
        yaxis=dict(
            tickmode="array", tickvals=list(range(len(projects))),
            ticktext=[short_label(title, 43) for title in projects],
            range=[len(projects) - 0.5, -0.5], title="Projects",
            automargin=True, fixedrange=False,
        ),
    )
    return figure


def show_details(data: CollaborationData, selection: tuple[str, str] | None) -> None:
    st.subheader("Selection details")
    if selection is None:
        st.write("Choose a project or PI above to see its recorded connections.")
        return
    kind, name = selection
    if kind == "Project":
        related = data.pairs.loc[data.pairs.project == name, "participant"].tolist()
        st.markdown(f"**Project:** {name}")
        st.write(f"{len(related)} participating PIs")
        st.dataframe({"PI": related}, hide_index=True, width="stretch")
    else:
        related = data.pairs.loc[data.pairs.participant == name, "project"].tolist()
        st.markdown(f"**PI:** {name}")
        st.write(f"{len(related)} projects")
        st.dataframe({"Project": related}, hide_index=True, width="stretch")


def on_graph_selected() -> None:
    component_state = st.session_state.get("cytoscape_network", {})
    event = component_state.get("selected")
    if event is None:
        st.session_state["selected"] = None
        return
    if not isinstance(event, dict):
        return
    candidate = (event.get("kind"), event.get("name"))
    data = load_data(SOURCE)
    allowed = {("Project", name) for name in data.projects.project}
    allowed.update(("PI", name) for name in data.participants.participant)
    if candidate in allowed:
        st.session_state["selected"] = candidate


def main() -> None:
    st.set_page_config(page_title="ADARC project participation", layout="wide")
    st.title("Project participation at ADARC")
    st.caption("Each mark and link means a PI is listed as a participant in a project. Unmarked cells mean the pair is not listed in this source.")
    try:
        data = load_data(SOURCE)
    except SourceError as exc:
        st.error(f"Source validation failed:\n\n{exc}")
        st.stop()
    for warning in data.warnings:
        st.warning(warning)

    options = [None] + [("Project", name) for name in data.projects.project] + [("PI", name) for name in data.participants.participant]
    if st.session_state.get("selected") not in options:
        st.session_state["selected"] = None
    selection = st.selectbox(
        "Find a project or PI", options=options, key="selected",
        format_func=lambda item: "Show all" if item is None else f"{item[0]} · {item[1]}",
        help="Type to search. The same selection highlights the matrix and network.",
    )
    count_columns = st.columns(3)
    count_columns[0].metric("Projects", len(data.projects))
    count_columns[1].metric("PIs", len(data.participants))
    count_columns[2].metric("Recorded participations", len(data.pairs))

    matrix_tab, network_tab, records_tab = st.tabs(["Matrix", "Network", "All records"])
    with matrix_tab:
        st.write("**Teal cell:** recorded participation. **Gold outline:** selected project row or PI column. Hover for full names; the table below has every pair.")
        st.plotly_chart(matrix_figure(data, selection), width="stretch", config={"displaylogo": False})
    with network_tab:
        st.write("**Blue squares:** projects. **Teal circles:** PIs. **Lines:** recorded participation. Select a node to highlight its links. The two-column layout makes membership explicit; force layout positions are exploratory and do not measure collaboration strength.")
        render_network(data, selection, on_graph_selected)
    with records_tab:
        st.write("Search and sort the complete set of recorded project–PI pairs.")
        st.dataframe(data.pairs.rename(columns={"project": "Project", "participant": "PI"}), hide_index=True, width="stretch")
    show_details(data, selection)


if __name__ == "__main__":
    main()

"""Explore recorded project–PI participation with a matrix and bipartite graph."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

from data_model import CollaborationData, SourceError, load_data


SOURCE = Path(__file__).with_name("project_participant.txt")
BLUE = "#176B91"
TEAL = "#087F75"
GOLD = "#D88900"
MUTED = "#6C8193"


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


def build_graph(data: CollaborationData) -> nx.Graph:
    graph = nx.Graph()
    for row in data.projects.itertuples(index=False):
        graph.add_node(f"project:{row.project_id}", kind="Project", label=row.project)
    for row in data.participants.itertuples(index=False):
        graph.add_node(f"participant:{row.pi_id}", kind="PI", label=row.participant)
    project_ids = dict(zip(data.projects.project, data.projects.project_id))
    pi_ids = dict(zip(data.participants.participant, data.participants.pi_id))
    for row in data.pairs.itertuples(index=False):
        graph.add_edge(f"project:{project_ids[row.project]}", f"participant:{pi_ids[row.participant]}")
    return graph


@st.cache_data(show_spinner=False)
def layout_for_graph(
    nodes: tuple[str, ...], edges: tuple[tuple[str, str], ...]
) -> dict[str, tuple[float, float]]:
    """Cache by source relationships so selection never rearranges the graph."""
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    positions = nx.spring_layout(graph, seed=13, iterations=250)
    return {node: (float(x), float(y)) for node, (x, y) in positions.items()}


def network_figure(
    graph: nx.Graph,
    positions: dict[str, tuple[float, float]],
    selection: tuple[str, str] | None,
    neighborhood: bool,
) -> go.Figure:
    selected_node = next(
        (node for node, attrs in graph.nodes(data=True)
         if selection and (attrs["kind"], attrs["label"]) == selection),
        None,
    )
    visible = set(graph.nodes)
    if neighborhood and selected_node:
        visible = {selected_node, *graph.neighbors(selected_node)}
    neighbors = set(graph.neighbors(selected_node)) if selected_node else set()

    def edge_trace(active: bool) -> go.Scatter:
        xs: list[float | None] = []
        ys: list[float | None] = []
        for left, right in graph.edges:
            if left not in visible or right not in visible:
                continue
            if bool(selected_node and selected_node in (left, right)) != active:
                continue
            xs.extend([positions[left][0], positions[right][0], None])
            ys.extend([positions[left][1], positions[right][1], None])
        return go.Scatter(
            x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
            line=dict(color=GOLD if active else MUTED, width=3 if active else 1),
        )

    figure = go.Figure()
    figure.add_trace(edge_trace(False))
    figure.add_trace(edge_trace(True))
    for kind, symbol, color in (("Project", "square", BLUE), ("PI", "circle", TEAL)):
        nodes = [node for node in graph if node in visible and graph.nodes[node]["kind"] == kind]
        labels = [
            short_label(graph.nodes[node]["label"], 16)
            if kind == "PI" and (neighborhood or node == selected_node or node in neighbors)
            else ""
            for node in nodes
        ]
        figure.add_trace(go.Scatter(
            x=[positions[node][0] for node in nodes],
            y=[positions[node][1] for node in nodes],
            mode="markers+text" if kind == "PI" else "markers",
            text=labels if kind == "PI" else None,
            textposition="top center",
            customdata=[[graph.nodes[node]["label"], graph.degree[node]] for node in nodes],
            hovertemplate="%{customdata[0]}<br>Recorded memberships: %{customdata[1]}<extra></extra>",
            name=kind,
            marker=dict(
                symbol=symbol,
                size=[19 if node == selected_node else 14 if node in neighbors else 10 for node in nodes],
                color=color,
                opacity=[1 if not selected_node or node == selected_node or node in neighbors else 0.55 for node in nodes],
                line=dict(color="#FFFFFF", width=1),
            ),
        ))
    figure.update_layout(
        height=700, margin=dict(l=10, r=10, t=15, b=10),
        hovermode="closest", dragmode="pan",
        plot_bgcolor="#14202B", paper_bgcolor="#14202B", font=dict(color="#E7EEF5"),
        legend=dict(orientation="h", y=1.04),
        xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
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
        st.write("**Square:** project. **Circle:** PI. **Line:** recorded participation. Gold lines connect the selection. Hover for full names. Positions show layout only, not collaboration strength.")
        neighborhood = st.toggle("Show selected neighborhood only", value=False, disabled=selection is None)
        graph = build_graph(data)
        positions = layout_for_graph(tuple(graph.nodes), tuple(graph.edges))
        st.plotly_chart(network_figure(graph, positions, selection, neighborhood), width="stretch", config={"displaylogo": False})
    with records_tab:
        st.write("Search and sort the complete set of recorded project–PI pairs.")
        st.dataframe(data.pairs.rename(columns={"project": "Project", "participant": "PI"}), hide_index=True, width="stretch")
    show_details(data, selection)


if __name__ == "__main__":
    main()

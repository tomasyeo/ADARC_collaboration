"""Explore project participation and PI shared-project counts from one TSV."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from data_model import CollaborationData, SourceError, load_data
from network_component import render_network
from pi_network_component import render_pi_network
from pi_projection import PIProjection, pair_key, project_pi_pairs


SOURCE = Path(__file__).parent / "data_source" / "project_participant.txt"
TEAL = "#087F75"
GOLD = "#D88900"
Selection = tuple[str, str] | tuple[str, str, str] | None


def short_label(label: str, limit: int = 30) -> str:
    return label if len(label) <= limit else label[: limit - 1].rstrip() + "…"


def matrix_figure(data: CollaborationData, selection: Selection) -> go.Figure:
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
    if selection and len(selection) == 2 and selection[0] in ("Project", "PI"):
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


def show_details(data: CollaborationData, selection: Selection) -> None:
    st.subheader("Selection details")
    if selection is None or selection[0] == "Pair":
        st.write("Choose a project or PI above to see its recorded connections.")
        return
    kind, name = selection
    if kind == "Project":
        related = data.pairs.loc[data.pairs.project == name, "participant"].tolist()
        st.text(f"Project: {name}")
        st.write(f"{len(related)} participating PIs")
        st.dataframe({"PI": related}, hide_index=True, width="stretch")
    else:
        related = data.pairs.loc[data.pairs.participant == name, "project"].tolist()
        st.text(f"PI: {name}")
        st.write(f"{len(related)} projects")
        st.dataframe({"Project": related}, hide_index=True, width="stretch")


def valid_selection(selection: Selection, data: CollaborationData) -> bool:
    if selection is None:
        return True
    if not isinstance(selection, tuple):
        return False
    if len(selection) == 2:
        kind, name = selection
        return ((kind == "Project" and name in set(data.projects.project)) or
                (kind == "PI" and name in set(data.participants.participant)))
    if len(selection) == 3 and selection[0] == "Pair":
        first, second = selection[1:]
        if not all(isinstance(name, str) for name in (first, second)):
            return False
        if first == second or (first, second) != pair_key(first, second):
            return False
        if first not in data.matrix.columns or second not in data.matrix.columns:
            return False
        return bool((data.matrix[first] & data.matrix[second]).any())
    return False


def apply_pending_selection(data: CollaborationData) -> None:
    pending = st.session_state.pop("pending_selection", "unchanged")
    if pending != "unchanged" and valid_selection(pending, data):
        st.session_state["semantic_selection"] = pending
    if not valid_selection(st.session_state.get("semantic_selection"), data):
        st.session_state["semantic_selection"] = None


def on_graph_selected() -> None:
    """Queue a browser selection; main validates it after reading the TSV."""
    event = st.session_state.get("cytoscape_network", {}).get("selected")
    if event is None:
        st.session_state["pending_selection"] = None
    elif isinstance(event, dict):
        kind, name = event.get("kind"), event.get("name")
        if isinstance(kind, str) and isinstance(name, str):
            st.session_state["pending_selection"] = (kind, name)


def on_pi_graph_selected() -> None:
    event = st.session_state.get("cytoscape_pi_network", {}).get("selected")
    if isinstance(event, dict):
        # Keep the positions and selection from the same browser click together.
        view = event.get("view")
        if isinstance(view, dict):
            st.session_state["pi_graph_view"] = view
        if event.get("kind") == "Clear":
            st.session_state["pending_selection"] = None
        if event.get("kind") == "PI" and isinstance(event.get("name"), str):
            st.session_state["pending_selection"] = ("PI", event["name"])
        elif (event.get("kind") == "Pair" and isinstance(event.get("first"), str)
              and isinstance(event.get("second"), str)):
            st.session_state["pending_selection"] = ("Pair", *pair_key(event["first"], event["second"]))


def selection_box(key: str, label: str, options: list[Selection], formatter) -> Selection:
    selected = st.session_state.get("semantic_selection")
    foreign = selected is not None and selected not in options
    display_options = [None, selected, *options[1:]] if foreign else options
    if st.session_state.get(key) != selected:
        st.session_state[key] = selected

    def display_label(item: Selection) -> str:
        if foreign and item == selected:
            if item[0] == "Pair":
                return f"Pair · {item[1]} + {item[2]} (on PI shared projects)"
            return f"Project · {item[1]} (on Projects and PIs)"
        return formatter(item)

    def on_change() -> None:
        st.session_state["semantic_selection"] = st.session_state[key]

    chosen = st.selectbox(label, options=display_options, format_func=display_label, key=key,
                          on_change=on_change, help="Type to search or choose Show all to clear selection.")
    if foreign:
        st.caption("This selection is retained for your return to its page; it has no highlight here.")
    return chosen


def pi_matrix_figure(projection: PIProjection, selection: Selection) -> go.Figure:
    names = list(projection.names)
    size = len(names)
    values = projection.matrix.to_numpy()
    off_diagonal = [[None if row == column else int(values[row, column])
                     for column in range(size)] for row in range(size)]
    diagonal = [[int(values[row, column]) if row == column else None
                 for column in range(size)] for row in range(size)]
    labels = [[[first, second] for second in names] for first in names]
    numbers = [[str(value) if value else "" for value in row] for row in off_diagonal]
    max_shared = max((len(titles) for titles in projection.shared_projects.values()), default=1)
    figure = go.Figure()
    figure.add_trace(go.Heatmap(
        z=off_diagonal, x=list(range(size)), y=list(range(size)), customdata=labels,
        text=numbers, texttemplate="%{text}", textfont=dict(size=11),
        colorscale=[[0, "#F0F3F5"], [0.001, "#E1F3EF"], [1, TEAL]],
        zmin=0, zmax=max_shared, showscale=True,
        colorbar=dict(title=dict(text="Shared<br>projects"), len=0.55), xgap=2, ygap=2,
        hovertemplate="%{customdata[0]} + %{customdata[1]}<br>Projects shared by these two PIs: %{z}<extra></extra>",
    ))
    figure.add_trace(go.Heatmap(
        z=diagonal, x=list(range(size)), y=list(range(size)), customdata=labels,
        text=[[str(value) if value is not None else "" for value in row] for row in diagonal],
        texttemplate="%{text}", textfont=dict(size=11, color="#13243A"),
        colorscale=[[0, "#F7DD9A"], [1, "#F7DD9A"]], showscale=False,
        xgap=2, ygap=2, hovertemplate="%{customdata[0]}<br>Projects for this PI: %{z}<extra></extra>",
    ))
    if selection and selection[0] == "PI" and selection[1] in names:
        index = names.index(selection[1])
        for bounds in ((-0.5, size - 0.5, index - 0.5, index + 0.5),
                       (index - 0.5, index + 0.5, -0.5, size - 0.5)):
            figure.add_shape(type="rect", x0=bounds[0], x1=bounds[1], y0=bounds[2], y1=bounds[3],
                             line=dict(color=GOLD, width=3), fillcolor="rgba(0,0,0,0)")
    elif selection and selection[0] == "Pair" and selection[1] in names and selection[2] in names:
        for row, column in ((names.index(selection[1]), names.index(selection[2])),
                            (names.index(selection[2]), names.index(selection[1]))):
            figure.add_shape(type="rect", x0=column - 0.5, x1=column + 0.5,
                             y0=row - 0.5, y1=row + 0.5,
                             line=dict(color=GOLD, width=4), fillcolor="rgba(0,0,0,0)")
    figure.update_layout(
        height=max(720, size * 36 + 135), margin=dict(l=10, r=10, t=20, b=20),
        xaxis=dict(tickmode="array", tickvals=list(range(size)),
                   ticktext=[short_label(n, 20) for n in names], tickangle=-50,
                   side="top", title="PIs", range=[-0.5, size - 0.5]),
        yaxis=dict(tickmode="array", tickvals=list(range(size)),
                   ticktext=[short_label(n, 24) for n in names],
                   range=[size - 0.5, -0.5], title="PIs", automargin=True),
    )
    return figure


def show_pi_details(projection: PIProjection, selection: Selection) -> None:
    st.subheader("Selection details")
    if not selection or selection[0] == "Project":
        st.write("Choose a PI or PI pair above to see source project titles.")
    elif selection[0] == "PI":
        name = selection[1]
        projects = projection.projects_by_pi[name]
        st.write(f"**{name}** · {len(projects)} listed project{'s' if len(projects) != 1 else ''}")
        st.dataframe({"Project": projects}, hide_index=True, width="stretch")
        connections = [(second if first == name else first, len(titles))
                       for (first, second), titles in projection.shared_projects.items()
                       if name in (first, second)]
        connections.sort(key=lambda item: (-item[1], item[0].casefold(), item[0]))
        st.write("**Other PIs by shared-project count**")
        st.dataframe({"PI": [name for name, _ in connections],
                      "Shared projects": [count for _, count in connections]},
                     hide_index=True, width="stretch")
    else:
        first, second = selection[1:]
        titles = projection.shared_projects[(first, second)]
        st.write(f"**{first} + {second}** · {len(titles)} shared project{'s' if len(titles) != 1 else ''}")
        st.dataframe({"Shared project": titles}, hide_index=True, width="stretch")


def projects_page(data: CollaborationData) -> None:
    st.title("Projects and PIs")
    st.caption("Each mark and link means a PI is listed as a participant in a project. Unmarked cells mean the pair is not listed in this source.")
    options: list[Selection] = [None] + [("Project", name) for name in data.projects.project] + [("PI", name) for name in data.participants.participant]
    selection = selection_box("projects_search", "Find a project or PI", options,
                              lambda item: "Show all" if item is None else f"{item[0]} · {item[1]}")
    columns = st.columns(3)
    columns[0].metric("Projects", len(data.projects))
    columns[1].metric("PIs", len(data.participants))
    columns[2].metric("Recorded participations", len(data.pairs))
    matrix_tab, network_tab, records_tab = st.tabs(["Matrix", "Network", "All records"],
                                                    key="projects_tabs", on_change="rerun")
    if matrix_tab.open:
        with matrix_tab:
            st.write("**Teal cell:** recorded participation. **Gold outline:** selected project row or PI column. Hover for full names.")
            st.plotly_chart(matrix_figure(data, selection), width="stretch", config={"displaylogo": False})
    if network_tab.open:
        with network_tab:
            st.write("**Blue squares:** projects. **Teal circles:** PIs. **Lines:** recorded participation. Select a node to highlight its links. Layout distance does not measure collaboration strength.")
            render_network(data, selection if selection and len(selection) == 2 else None, on_graph_selected)
    if records_tab.open:
        with records_tab:
            st.write("Search and sort the complete set of recorded project–PI pairs.")
            st.dataframe(data.pairs.rename(columns={"project": "Project", "participant": "PI"}),
                         hide_index=True, width="stretch")
    show_details(data, selection)


def pi_page(data: CollaborationData) -> None:
    projection = project_pi_pairs(data)
    st.title("PI shared projects")
    st.caption("A pair count is the number of source projects listing both PIs. It does not establish direct work between them.")
    options: list[Selection] = [None] + [("PI", name) for name in projection.names]
    options += [("Pair", *pair) for pair in sorted(
        projection.shared_projects,
        key=lambda pair: (pair[0].casefold(), pair[0], pair[1].casefold(), pair[1]),
    )]

    def label(item: Selection) -> str:
        if item is None:
            return "Show all"
        if item[0] == "PI":
            count = len(projection.projects_by_pi[item[1]])
            return f"PI · {item[1]} ({count} project{'s' if count != 1 else ''})"
        count = len(projection.shared_projects[item[1:]])
        return f"Pair · {item[1]} + {item[2]} ({count} shared)"

    selection = selection_box("pi_search", "Find a PI or PI pair", options, label)
    if selection and selection[0] != "Project":
        st.write(f"**Selected:** {label(selection)}")
    columns = st.columns(3)
    columns[0].metric("PIs", len(projection.names))
    columns[1].metric("Pairs sharing a project", len(projection.shared_projects))
    columns[2].metric("Source projects", len(data.projects))
    matrix_tab, network_tab = st.tabs(["Matrix", "Network"], key="pi_tabs", on_change="rerun")
    if matrix_tab.open:
        with matrix_tab:
            st.write("**Off diagonal:** shared-project count. **Gold diagonal:** projects for that PI. **Pale cells:** zero shared projects. **Gold outline:** selection. Both halves show the same pair; pair totals count it once.")
            st.plotly_chart(pi_matrix_figure(projection, selection), width="stretch", config={"displaylogo": False})
    if network_tab.open:
        with network_tab:
            st.write("**Circle area:** PI project count. **Lines:** shared-project count; one-project ties are thin and pale. Select a circle or line for exact titles below. Positions are exploratory.")
            render_pi_network(data, projection, selection, on_pi_graph_selected)
    show_pi_details(projection, selection)


def main() -> None:
    st.set_page_config(page_title="ADARC project participation", layout="wide")
    try:
        data = load_data(SOURCE)
    except SourceError as exc:
        st.error(f"Source validation failed:\n\n{exc}")
        st.stop()
    apply_pending_selection(data)
    for warning in data.warnings:
        st.warning(warning)
    page = st.navigation([
        st.Page(lambda: projects_page(data), title="Projects and PIs",
                url_path="projects-and-pis", default=True),
        st.Page(lambda: pi_page(data), title="PI shared projects",
                url_path="pi-shared-projects"),
    ], position="top")
    page.run()


if __name__ == "__main__":
    main()

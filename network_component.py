"""Cytoscape.js graph data and Streamlit component registration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import networkx as nx
import streamlit as st

from data_model import CollaborationData


ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend"


def short_label(label: str, limit: int) -> str:
    return label if len(label) <= limit else label[: limit - 1].rstrip() + "…"


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


def _bipartite_positions(graph: nx.Graph) -> dict[str, dict[str, int]]:
    """Order each column by neighbor barycenter to reduce unnecessary crossings."""
    projects = [node for node, attrs in graph.nodes(data=True) if attrs["kind"] == "Project"]
    pis = [node for node, attrs in graph.nodes(data=True) if attrs["kind"] == "PI"]
    for _ in range(6):
        project_rank = {node: index for index, node in enumerate(projects)}
        pis.sort(key=lambda node: (
            sum(project_rank[neighbor] for neighbor in graph.neighbors(node)) / graph.degree[node],
            graph.nodes[node]["label"].casefold(),
        ))
        pi_rank = {node: index for index, node in enumerate(pis)}
        projects.sort(key=lambda node: (
            sum(pi_rank[neighbor] for neighbor in graph.neighbors(node)) / graph.degree[node],
            graph.nodes[node]["label"].casefold(),
        ))
    project_spacing = 26
    pi_spacing = project_spacing * (len(projects) - 1) / max(1, len(pis) - 1)
    return {
        **{node: {"x": 260, "y": 45 + index * project_spacing} for index, node in enumerate(projects)},
        **{node: {"x": 1060, "y": 45 + round(index * pi_spacing)} for index, node in enumerate(pis)},
    }


def graph_payload(data: CollaborationData, selection: tuple[str, str] | None) -> dict:
    graph = build_graph(data)
    elements = []
    selected_id = None
    for node, attrs in graph.nodes(data=True):
        kind = attrs["kind"]
        label = attrs["label"]
        if selection == (kind, label):
            selected_id = node
        elements.append({"data": {
            "id": node, "kind": kind, "label": label,
            "short": short_label(label, 27 if kind == "Project" else 20),
        }})
    for project, pi in graph.edges:
        elements.append({"data": {"id": f"edge:{project}:{pi}", "source": project, "target": pi}})
    source_pairs = data.pairs[["project", "participant"]].values.tolist()
    signature = hashlib.sha256(json.dumps(source_pairs, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {
        "elements": elements,
        "positions": _bipartite_positions(graph),
        "selectedId": selected_id,
        "signature": signature,
    }


HTML = """
<div class="network-component">
  <div class="network-toolbar">
    <label>Layout
      <select class="layout-choice" aria-label="Network layout">
        <option value="bipartite">Two columns</option>
        <option value="force">Force layout</option>
      </select>
    </label>
    <button class="recompute-layout" type="button">Recompute force layout</button>
    <button class="reset-layout" type="button">Reset positions</button>
    <button class="fit-network" type="button">Fit to view</button>
    <button class="focus-selection" type="button" aria-pressed="false">Focus selection</button>
    <button class="reveal-fellow-pis" type="button" aria-pressed="false" title="Select a PI to reveal other PIs on their projects">Reveal fellow PIs</button>
  </div>
  <div class="network-frame">
    <div class="network-canvas" role="img" aria-label="Interactive project and PI membership network"></div>
    <div class="network-tooltip" role="tooltip"></div>
  </div>
  <p class="network-help">Orange: selected node and direct memberships. Reveal fellow PIs adds other PIs on the selected PI’s projects, with lavender connections. Drag nodes to adjust the view; use the searchable selector and records table for full keyboard access.</p>
</div>
"""


def _register_component():
    bundle = (FRONTEND / "dist" / "network.js").read_text(encoding="utf-8")
    css = (FRONTEND / "network.css").read_text(encoding="utf-8")
    return st.components.v2.component(
        name="adarc_cytoscape_network", html=HTML, css=css, js=bundle,
    )


NETWORK_COMPONENT = None


def _on_view_change() -> None:
    view = st.session_state.get("cytoscape_network", {}).get("view")
    if isinstance(view, dict):
        st.session_state["project_graph_view"] = view


def render_network(data: CollaborationData, selection: tuple[str, str] | None, on_select):
    global NETWORK_COMPONENT
    if NETWORK_COMPONENT is None:
        NETWORK_COMPONENT = _register_component()
    payload = graph_payload(data, selection)
    payload["savedView"] = st.session_state.get("project_graph_view")
    return NETWORK_COMPONENT(
        data=payload, key="cytoscape_network",
        on_selected_change=on_select, on_view_change=_on_view_change,
        width="stretch",
    )

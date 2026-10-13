"""Cytoscape payload for the PI shared-project projection."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import streamlit as st

from data_model import CollaborationData
from pi_projection import PIProjection


FRONTEND = Path(__file__).parent / "frontend"


def pi_graph_payload(data: CollaborationData, projection: PIProjection, selection) -> dict:
    ids = dict(zip(data.participants.participant, data.participants.pi_id))
    elements = []
    selected_id = None
    for index, name in enumerate(projection.names):
        node_id = f"pi:{ids[name]}"
        count = len(projection.projects_by_pi[name])
        if selection == ("PI", name):
            selected_id = node_id
        angle = -math.pi / 2 + 2 * math.pi * index / len(projection.names)
        side = "right" if math.cos(angle) >= 0 else "left"
        elements.append({"data": {"id": node_id, "kind": "PI", "name": name,
                                   "short": name if len(name) <= 22 else name[:21].rstrip() + "…",
                                   "count": count, "side": side}})
    for (first, second), titles in projection.shared_projects.items():
        source, target = f"pi:{ids[first]}", f"pi:{ids[second]}"
        edge_id = f"pair:{ids[first]}:{ids[second]}"
        if selection == ("Pair", first, second):
            selected_id = edge_id
        elements.append({"data": {"id": edge_id, "kind": "Pair", "source": source,
                                   "target": target, "first": first, "second": second,
                                   "count": len(titles)}})
    positions = {}
    for index, name in enumerate(projection.names):
        angle = -math.pi / 2 + 2 * math.pi * index / len(projection.names)
        positions[f"pi:{ids[name]}"] = {"x": 600 + 440 * math.cos(angle),
                                         "y": 440 + 360 * math.sin(angle)}
    signature_source = [(first, second, titles) for (first, second), titles in projection.shared_projects.items()]
    signature_source += [(name, projection.projects_by_pi[name]) for name in projection.names]
    signature = hashlib.sha256(json.dumps(signature_source, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"elements": elements, "positions": positions, "selectedId": selected_id,
            "signature": signature}


HTML = """
<div class="network-component">
  <div class="network-toolbar">
    <button class="recompute-layout" type="button">Recompute layout</button>
    <button class="reset-layout" type="button">Reset positions</button>
    <button class="fit-network" type="button">Fit to view</button>
    <button class="focus-selection" type="button" aria-pressed="false">Focus selection</button>
  </div>
  <div class="network-frame">
    <div class="network-canvas" role="img" aria-label="Interactive PI shared-project network"></div>
    <div class="network-tooltip" role="tooltip"></div>
  </div>
  <p class="network-help">Select a circle or line to inspect its source projects. Drag nodes, zoom, or use the search above for keyboard and touch access.</p>
</div>
"""


def _register_component():
    return st.components.v2.component(
        name="adarc_pi_shared_network", html=HTML,
        css=(FRONTEND / "network.css").read_text(encoding="utf-8"),
        js=(FRONTEND / "dist" / "pi_network.js").read_text(encoding="utf-8"),
    )


PI_NETWORK_COMPONENT = None


def _on_view_change() -> None:
    view = st.session_state.get("cytoscape_pi_network", {}).get("view")
    if isinstance(view, dict):
        st.session_state["pi_graph_view"] = view


def render_pi_network(data: CollaborationData, projection: PIProjection, selection, on_select):
    global PI_NETWORK_COMPONENT
    if PI_NETWORK_COMPONENT is None:
        PI_NETWORK_COMPONENT = _register_component()
    payload = pi_graph_payload(data, projection, selection)
    payload["savedView"] = st.session_state.get("pi_graph_view")
    return PI_NETWORK_COMPONENT(
        data=payload, key="cytoscape_pi_network",
        on_selected_change=on_select, on_view_change=_on_view_change,
        width="stretch",
    )

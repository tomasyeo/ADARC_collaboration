import cytoscape from "cytoscape";

function styles() {
  return [
    { selector: "node", style: {
      "shape": "ellipse", "background-color": "#15A78E",
      "width": (node) => Math.sqrt(324 + 120 * node.data("count")),
      "height": (node) => Math.sqrt(324 + 120 * node.data("count")),
      "border-width": 1.5, "border-color": "#EAF2F7",
      "label": "data(short)", "font-family": "sans-serif", "font-size": 12,
      "color": "#F3F7FA", "text-outline-width": 2,
      "text-outline-color": "#14202B", "text-halign": "right",
      "text-margin-x": 12,
    } },
    { selector: 'node[side = "left"]', style: {
      "text-halign": "left", "text-margin-x": -12,
    } },
    { selector: "edge", style: {
      "width": (edge) => edge.data("count") === 1 ? 0.8 : Math.min(5, 1.3 + 0.55 * edge.data("count")),
      "line-color": (edge) => edge.data("count") === 1 ? "#8293A0" : "#71BFC0",
      "opacity": (edge) => edge.data("count") === 1 ? 0.24 : 0.67,
      "curve-style": "straight", "line-cap": "round",
    } },
    { selector: "node.selected, node.neighbor", style: {
      "border-width": 4, "border-color": "#F0A727", "z-index": 10,
    } },
    { selector: "edge.active", style: {
      "line-color": "#F0A727", "opacity": 1, "z-index": 9,
    } },
    { selector: ".muted", style: { "opacity": 0.16 } },
    { selector: ".hidden", style: { "display": "none" } },
  ];
}

export default function component({ parentElement, data, setStateValue, setTriggerValue }) {
  const root = parentElement.querySelector(".network-component");
  const canvas = root.querySelector(".network-canvas");
  const tooltip = root.querySelector(".network-tooltip");
  const recomputeButton = root.querySelector(".recompute-layout");
  const resetButton = root.querySelector(".reset-layout");
  const fitButton = root.querySelector(".fit-network");
  const focusButton = root.querySelector(".focus-selection");
  const saved = data.savedView;
  const restore = saved?.signature === data.signature ? saved : null;
  const sameViewport = restore && Math.abs((restore.width ?? 0) - canvas.clientWidth) < 10;
  let selectedId = data.selectedId ?? null;
  let focused = restore?.focused ?? false;
  let publishTimer = null;
  const cy = cytoscape({
    container: canvas, elements: data.elements, style: styles(),
    layout: { name: "preset", positions: restore?.positions ?? data.positions,
              fit: !sameViewport, padding: 70 },
    minZoom: 0.15, maxZoom: 4, wheelSensitivity: 0.25,
    boxSelectionEnabled: false,
  });
  if (sameViewport && restore.zoom && restore.pan) {
    cy.zoom(restore.zoom);
    cy.pan(restore.pan);
  }

  function snapshot() {
    const positions = {};
    cy.nodes().forEach((node) => { positions[node.id()] = node.position(); });
    const state = { signature: data.signature, positions, zoom: cy.zoom(),
      pan: cy.pan(), width: canvas.clientWidth, focused, selectedId };
    return state;
  }

  function publishView() {
    if (publishTimer !== null) clearTimeout(publishTimer);
    publishTimer = null;
    setStateValue("view", snapshot());
  }

  function schedulePublish() {
    if (publishTimer !== null) clearTimeout(publishTimer);
    publishTimer = setTimeout(publishView, 300);
  }

  function neighborhood() {
    const selected = selectedId ? cy.$id(selectedId) : cy.collection();
    if (selected.length !== 1) return cy.collection();
    return selected.isNode() ? selected.closedNeighborhood() : selected.union(selected.connectedNodes());
  }

  function refreshLabelSides() {
    const nodes = cy.nodes().toArray();
    const center = nodes.reduce((sum, node) => sum + node.position().x, 0) / Math.max(1, nodes.length);
    nodes.forEach((node) => node.data("side", node.position().x < center ? "left" : "right"));
  }

  function applySelection() {
    cy.elements().removeClass("selected neighbor active muted hidden");
    const selected = selectedId ? cy.$id(selectedId) : cy.collection();
    const hasSelection = selected.length === 1;
    if (!hasSelection) focused = false;
    focusButton.disabled = !hasSelection;
    focusButton.setAttribute("aria-pressed", String(focused));
    if (!hasSelection) return;
    const nearby = neighborhood();
    cy.elements().addClass("muted");
    nearby.removeClass("muted");
    if (selected.isNode()) {
      selected.addClass("selected");
      selected.neighborhood("node").addClass("neighbor");
      selected.connectedEdges().addClass("active");
    } else {
      selected.addClass("active");
      selected.connectedNodes().addClass("selected");
    }
    if (focused) cy.elements().not(nearby).addClass("hidden");
  }

  function fitVisible() {
    const visible = cy.elements().not(".hidden");
    cy.fit(visible, 75);
    if (cy.zoom() > 1.5) {
      cy.zoom(1.5);
      cy.center(visible);
    }
    snapshot();
  }

  function runLayout(reset) {
    tooltip.style.display = "none";
    if (reset) {
      cy.layout({ name: "preset", positions: data.positions, fit: true, padding: 70,
                  animate: false }).run();
    } else {
      cy.layout({ name: "cose", randomize: true, animate: false, fit: true,
                  padding: 70, numIter: 1800, nodeRepulsion: () => 32000,
                  idealEdgeLength: () => 150, edgeElasticity: () => 60,
                  nodeOverlap: 30 }).run();
    }
    refreshLabelSides();
    fitVisible();
    publishView();
  }

  refreshLabelSides();
  applySelection();
  if (!sameViewport || (focused && restore?.selectedId !== selectedId)) fitVisible();
  recomputeButton.onclick = () => runLayout(false);
  resetButton.onclick = () => runLayout(true);
  fitButton.onclick = () => { fitVisible(); publishView(); };
  focusButton.onclick = () => {
    focused = !focused;
    applySelection();
    fitVisible();
    publishView();
  };

  cy.on("tap", "node, edge", (event) => {
    const element = event.target;
    selectedId = element.id();
    applySelection();
    if (element.isNode()) {
      setTriggerValue("selected", { kind: "PI", name: element.data("name"), view: snapshot() });
    } else {
      setTriggerValue("selected", { kind: "Pair", first: element.data("first"),
                                     second: element.data("second"), view: snapshot() });
    }
  });
  cy.on("tap", (event) => {
    if (event.target !== cy) return;
    selectedId = null;
    focused = false;
    applySelection();
    setTriggerValue("selected", { kind: "Clear", view: snapshot() });
  });

  cy.on("mouseover", "node, edge", (event) => {
    const element = event.target;
    tooltip.textContent = element.isNode()
      ? `${element.data("name")} · ${element.data("count")} listed project${element.data("count") === 1 ? "" : "s"}`
      : `${element.data("first")} + ${element.data("second")} · ${element.data("count")} shared project${element.data("count") === 1 ? "" : "s"}. Select for titles.`;
    tooltip.style.display = "block";
  });
  cy.on("mousemove", "node, edge", (event) => {
    const point = event.renderedPosition;
    tooltip.style.left = `${Math.max(8, Math.min(point.x + 20, canvas.clientWidth - tooltip.offsetWidth - 8))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(point.y + 16, canvas.clientHeight - tooltip.offsetHeight - 8))}px`;
  });
  cy.on("mouseout", "node, edge", () => { tooltip.style.display = "none"; });
  cy.on("dragfree", "node", () => { refreshLabelSides(); publishView(); });
  cy.on("pan zoom", () => { snapshot(); schedulePublish(); });

  let previousWidth = canvas.clientWidth;
  let disposed = false;
  let bounds = canvas.getBoundingClientRect();
  let scrollFrame = null;
  function refreshBounds() {
    if (disposed || cy.destroyed()) return;
    const next = canvas.getBoundingClientRect();
    if (next.left !== bounds.left || next.top !== bounds.top ||
        next.width !== bounds.width || next.height !== bounds.height) {
      bounds = next;
      cy.resize();
    }
  }
  function onScroll() {
    if (scrollFrame !== null) return;
    scrollFrame = requestAnimationFrame(() => {
      scrollFrame = null;
      refreshBounds();
    });
  }
  const eventRoot = canvas.getRootNode();
  window.addEventListener("scroll", onScroll, true);
  if (eventRoot !== document) eventRoot.addEventListener("scroll", onScroll, true);
  canvas.addEventListener("pointerdown", refreshBounds, true);
  const observer = new ResizeObserver(() => {
    if (disposed || cy.destroyed()) return;
    bounds = canvas.getBoundingClientRect();
    cy.resize();
    const nextWidth = canvas.clientWidth;
    if (Math.abs(nextWidth - previousWidth) > 10) {
      previousWidth = nextWidth;
      fitVisible();
      publishView();
    }
  });
  observer.observe(canvas);
  return () => {
    disposed = true;
    observer.disconnect();
    window.removeEventListener("scroll", onScroll, true);
    if (eventRoot !== document) eventRoot.removeEventListener("scroll", onScroll, true);
    canvas.removeEventListener("pointerdown", refreshBounds, true);
    if (scrollFrame !== null) cancelAnimationFrame(scrollFrame);
    if (publishTimer !== null) clearTimeout(publishTimer);
    snapshot();
    cy.destroy();
  };
}

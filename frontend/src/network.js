import cytoscape from "cytoscape";

const viewStates = new Map();

function sameGraph(previous, signature) {
  return previous?.signature === signature;
}

function styleSheet() {
  return [
    { selector: "node", style: {
      "width": 19, "height": 19, "border-width": 1.5,
      "border-color": "#EAF2F7", "font-family": "sans-serif",
      "font-size": 12, "color": "#F3F7FA", "text-outline-width": 2,
      "text-outline-color": "#14202B", "text-wrap": "none",
      "label": "data(short)",
    } },
    { selector: 'node[kind = "Project"]', style: {
      "shape": "round-rectangle", "background-color": "#358EC0",
      "text-halign": "left", "text-margin-x": -13,
    } },
    { selector: 'node[kind = "PI"]', style: {
      "shape": "ellipse", "background-color": "#15A78E",
      "text-halign": "right", "text-margin-x": 13,
    } },
    { selector: "edge", style: {
      "width": 1.2, "line-color": "#65798C", "opacity": 0.55,
      "curve-style": "straight",
    } },
    { selector: "node.selected", style: {
      "width": 28, "height": 28, "border-width": 4,
      "border-color": "#F0A727", "z-index": 10,
    } },
    { selector: "node.neighbor", style: {
      "border-width": 3, "border-color": "#F0A727", "z-index": 8,
    } },
    { selector: "edge.active", style: {
      "width": 3, "line-color": "#F0A727", "opacity": 1, "z-index": 9,
    } },
    { selector: "node.mobile-focus", style: {
      "text-halign": "center", "text-valign": "bottom", "text-margin-x": 0,
      "text-margin-y": 8, "text-wrap": "ellipsis", "text-max-width": 280,
    } },
    { selector: "node.mobile-dense", style: { "text-max-width": 130, "font-size": 11 } },
    { selector: ".muted", style: { "opacity": 0.35 } },
    { selector: "node.hidden, edge.hidden", style: { "display": "none" } },
  ];
}

export default function component({ parentElement, data, key, setTriggerValue }) {
  const root = parentElement.querySelector(".network-component");
  const canvas = root.querySelector(".network-canvas");
  const layoutSelect = root.querySelector(".layout-choice");
  const recomputeButton = root.querySelector(".recompute-layout");
  const resetButton = root.querySelector(".reset-layout");
  const fitButton = root.querySelector(".fit-network");
  const focusButton = root.querySelector(".focus-selection");
  const tooltip = root.querySelector(".network-tooltip");
  const saved = viewStates.get(key);
  const restore = sameGraph(saved, data.signature) ? saved : null;
  const sameViewport = restore && Math.abs((restore.width ?? 0) - canvas.clientWidth) < 10;
  let mode = restore?.mode ?? "bipartite";
  let focused = restore?.focused ?? false;
  let selectedId = data.selectedId ?? null;
  let overviewPositions = restore?.overviewPositions ?? restore?.positions ?? data.positions;
  let mobileFocusActive = restore?.mobileFocusActive ?? false;
  layoutSelect.value = mode;

  function syncFocusButton(hasSelection) {
    focusButton.disabled = !hasSelection;
    focusButton.setAttribute("aria-pressed", String(focused));
  }

  const initialPositions = restore?.positions ?? data.positions;
  const cy = cytoscape({
    container: canvas,
    elements: data.elements,
    style: styleSheet(),
    layout: { name: "preset", positions: initialPositions, fit: !sameViewport, padding: 45 },
    minZoom: 0.15,
    maxZoom: 4,
    wheelSensitivity: 0.25,
    boxSelectionEnabled: false,
  });
  if (sameViewport && restore.zoom && restore.pan) {
    cy.zoom(restore.zoom);
    cy.pan(restore.pan);
  }

  function snapshot() {
    const positions = {};
    cy.nodes().forEach((node) => { positions[node.id()] = node.position(); });
    viewStates.set(key, {
      signature: data.signature, mode, focused, selectedId, positions,
      overviewPositions, mobileFocusActive,
      zoom: cy.zoom(), pan: cy.pan(), width: canvas.clientWidth,
    });
  }

  function positionsNow() {
    const positions = {};
    cy.nodes().forEach((node) => { positions[node.id()] = node.position(); });
    return positions;
  }

  function placeNodes(positions) {
    cy.nodes().forEach((node) => {
      if (positions[node.id()]) node.position(positions[node.id()]);
    });
  }

  function arrangeMobileFocus() {
    const selected = selectedId ? cy.$id(selectedId) : cy.collection();
    const useMobile = focused && selected.length === 1 && canvas.clientWidth < 600;
    if (!useMobile) {
      if (mobileFocusActive) placeNodes(overviewPositions);
      mobileFocusActive = false;
      cy.nodes().removeClass("mobile-focus mobile-dense");
      return;
    }
    if (!mobileFocusActive) overviewPositions = positionsNow();
    mobileFocusActive = true;
    const neighbors = selected.neighborhood("node").toArray()
      .sort((a, b) => a.data("label").localeCompare(b.data("label")));
    const dense = neighbors.length > 2;
    const rowGap = neighbors.length > 8 ? 75 : 105;
    cy.nodes().removeClass("mobile-focus mobile-dense");
    selected.addClass("mobile-focus");
    selected.position({ x: 180, y: 25 });
    neighbors.forEach((node, index) => {
      node.addClass("mobile-focus");
      if (dense) node.addClass("mobile-dense");
      node.position({
        x: dense ? (index % 2 === 0 ? 90 : 270) : 180,
        y: 135 + Math.floor(index / (dense ? 2 : 1)) * rowGap,
      });
    });
  }

  function applySelection() {
    cy.elements().removeClass("selected neighbor active muted hidden");
    const selected = selectedId ? cy.$id(selectedId) : cy.collection();
    const hasSelection = selected.length === 1;
    if (!hasSelection) {
      focused = false;
      syncFocusButton(false);
      return;
    }
    syncFocusButton(true);
    const neighborhood = selected.closedNeighborhood();
    cy.elements().addClass("muted");
    neighborhood.removeClass("muted");
    selected.addClass("selected");
    selected.neighborhood("node").addClass("neighbor");
    selected.connectedEdges().addClass("active");
    if (focused) cy.elements().not(neighborhood).addClass("hidden");
  }

  function fitVisible() {
    arrangeMobileFocus();
    const visible = cy.elements().not(".hidden");
    cy.fit(visible, 70);
    if (cy.zoom() > 1.5) {
      cy.zoom(1.5);
      cy.center(visible);
    }
    snapshot();
  }

  function runLayout(nextMode) {
    tooltip.style.display = "none";
    mode = nextMode;
    recomputeButton.disabled = mode !== "force";
    if (mode === "bipartite") {
      cy.layout({ name: "preset", positions: data.positions, fit: true, padding: 45, animate: false }).run();
    } else {
      cy.layout({
        name: "cose", randomize: true, animate: false, fit: true, padding: 55,
        nodeRepulsion: () => 25000, idealEdgeLength: () => 110,
        edgeElasticity: () => 60, nodeOverlap: 25, numIter: 1500,
      }).run();
    }
    mobileFocusActive = false;
    overviewPositions = positionsNow();
    if (focused) fitVisible();
    snapshot();
  }

  applySelection();
  if (mobileFocusActive && !(focused && canvas.clientWidth < 600)) arrangeMobileFocus();
  if (!sameViewport || (focused && restore?.selectedId !== selectedId)) fitVisible();
  recomputeButton.disabled = mode !== "force";

  layoutSelect.onchange = () => runLayout(layoutSelect.value);
  recomputeButton.onclick = () => runLayout("force");
  resetButton.onclick = () => {
    mode = "bipartite";
    layoutSelect.value = mode;
    runLayout(mode);
  };
  fitButton.onclick = fitVisible;
  focusButton.onclick = () => {
    tooltip.style.display = "none";
    focused = !focused;
    applySelection();
    fitVisible();
  };

  cy.on("tap", "node", (event) => {
    const node = event.target;
    selectedId = node.id();
    applySelection();
    snapshot();
    setTriggerValue("selected", {
      kind: node.data("kind"), name: node.data("label"),
    });
  });
  cy.on("tap", (event) => {
    if (event.target !== cy) return;
    selectedId = null;
    focused = false;
    applySelection();
    snapshot();
    setTriggerValue("selected", null);
  });
  cy.on("mouseover", "node", (event) => {
    const node = event.target;
    tooltip.textContent = `${node.data("kind")}: ${node.data("label")} · ${node.degree()} memberships`;
    tooltip.style.display = "block";
  });
  cy.on("mousemove", "node", (event) => {
    const point = event.renderedPosition;
    tooltip.style.left = `${Math.max(8, Math.min(point.x + 20, canvas.clientWidth - tooltip.offsetWidth - 8))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(point.y + 16, canvas.clientHeight - tooltip.offsetHeight - 8))}px`;
  });
  cy.on("mouseout", "node", () => { tooltip.style.display = "none"; });
  cy.on("dragfree", "node", () => {
    if (!mobileFocusActive) overviewPositions = positionsNow();
    snapshot();
  });
  cy.on("pan zoom", snapshot);

  let previousWidth = canvas.clientWidth;
  let disposed = false;
  const observer = new ResizeObserver(() => {
    if (disposed || cy.destroyed()) return;
    cy.resize();
    const nextWidth = canvas.clientWidth;
    if (Math.abs(nextWidth - previousWidth) > 10) {
      previousWidth = nextWidth;
      fitVisible();
    }
  });
  observer.observe(canvas);
  return () => {
    disposed = true;
    observer.disconnect();
    snapshot();
    cy.destroy();
  };
}

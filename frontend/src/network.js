import cytoscape from "cytoscape";
import { selectionNeighborhood, mobileFocusPositions, sharedProjectTitles } from "./project_selection.mjs";

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
      "width": 28, "height": 28, "border-width": 2,
      "border-color": "#F0A727", "z-index": 10,
    } },
    { selector: "node.neighbor", style: {
      "border-width": 2, "border-color": "#F0A727", "z-index": 8,
    } },
    { selector: "edge.active", style: {
      "width": 2, "line-color": "#F0A727", "opacity": 1, "z-index": 9,
    } },
    { selector: "node.secondary", style: {
      "border-width": 1.5, "border-color": "#B39DDB", "opacity": 0.9, "z-index": 6,
    } },
    { selector: "edge.secondary", style: {
      "width": 1.5, "line-color": "#B39DDB", "opacity": 0.9, "z-index": 5,
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

export default function component({ parentElement, data, setStateValue, setTriggerValue }) {
  const root = parentElement.querySelector(".network-component");
  const canvas = root.querySelector(".network-canvas");
  const layoutSelect = root.querySelector(".layout-choice");
  const recomputeButton = root.querySelector(".recompute-layout");
  const resetButton = root.querySelector(".reset-layout");
  const fitButton = root.querySelector(".fit-network");
  const focusButton = root.querySelector(".focus-selection");
  const fellowPisButton = root.querySelector(".reveal-fellow-pis");
  const tooltip = root.querySelector(".network-tooltip");
  const saved = data.savedView;
  const restore = sameGraph(saved, data.signature) ? saved : null;
  const sameViewport = restore && Math.abs((restore.width ?? 0) - canvas.clientWidth) < 10;
  let mode = restore?.mode ?? "bipartite";
  let focused = restore?.focused ?? false;
  let revealFellowPis = restore?.revealFellowPis ?? false;
  let selectedId = data.selectedId ?? null;
  let overviewPositions = restore?.overviewPositions ?? restore?.positions ?? data.positions;
  let mobileFocusActive = restore?.mobileFocusActive ?? false;
  let publishTimer = null;
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
    const state = {
      signature: data.signature, mode, focused, revealFellowPis, selectedId, positions,
      overviewPositions, mobileFocusActive,
      zoom: cy.zoom(), pan: cy.pan(), width: canvas.clientWidth,
    };
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
    const { positions, dense } = mobileFocusPositions(selected, revealFellowPis);
    cy.nodes().removeClass("mobile-focus mobile-dense");
    selected.addClass("mobile-focus");
    placeNodes(positions);
    cy.nodes().filter(node => node.id() !== selectedId && positions[node.id()]).forEach((node) => {
      node.addClass("mobile-focus");
      if (dense) node.addClass("mobile-dense");
    });
  }

  function applySelection() {
    cy.elements().removeClass("selected neighbor active secondary muted hidden");
    const selected = selectedId ? cy.$id(selectedId) : cy.collection();
    const hasSelection = selected.length === 1;
    fellowPisButton.disabled = !hasSelection || selected.data("kind") !== "PI";
    fellowPisButton.setAttribute("aria-pressed", String(revealFellowPis));
    if (!hasSelection) {
      focused = false;
      syncFocusButton(false);
      return;
    }
    syncFocusButton(true);
    const { expanded: neighborhood, secondary } = selectionNeighborhood(selected, revealFellowPis);
    cy.elements().addClass("muted");
    neighborhood.removeClass("muted");
    selected.addClass("selected");
    selected.neighborhood("node").addClass("neighbor");
    selected.connectedEdges().addClass("active");
    secondary.addClass("secondary");
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
    fitVisible();
    publishView();
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
  fitButton.onclick = () => { fitVisible(); publishView(); };
  focusButton.onclick = () => {
    tooltip.style.display = "none";
    focused = !focused;
    applySelection();
    fitVisible();
    publishView();
  };
  fellowPisButton.onclick = () => {
    tooltip.style.display = "none";
    revealFellowPis = !revealFellowPis;
    applySelection();
    if (focused) fitVisible();
    publishView();
  };

  cy.on("tap", "node", (event) => {
    const node = event.target;
    selectedId = node.id();
    applySelection();
    if (focused) fitVisible();
    if (publishTimer !== null) clearTimeout(publishTimer);
    publishTimer = null;
    setTriggerValue("selected", {
      kind: node.data("kind"), name: node.data("label"), view: snapshot(),
    });
  });
  cy.on("tap", (event) => {
    if (event.target !== cy) return;
    const wasFocused = focused;
    selectedId = null;
    focused = false;
    applySelection();
    if (wasFocused) fitVisible();
    if (publishTimer !== null) clearTimeout(publishTimer);
    publishTimer = null;
    setTriggerValue("selected", { kind: "Clear", view: snapshot() });
  });
  function positionTooltip(event) {
    const point = event.renderedPosition;
    tooltip.style.left = `${Math.max(8, Math.min(point.x + 20, canvas.clientWidth - tooltip.offsetWidth - 8))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(point.y + 16, canvas.clientHeight - tooltip.offsetHeight - 8))}px`;
  }
  cy.on("mouseover", "node", (event) => {
    const node = event.target;
    tooltip.textContent = `${node.data("kind")}: ${node.data("label")} · ${node.degree()} memberships`;
    if (node.hasClass("secondary")) {
      const selected = selectedId ? cy.$id(selectedId) : cy.collection();
      const titles = sharedProjectTitles(selected, node);
      if (titles.length) {
        tooltip.textContent += `\n\nShares ${titles.length} project${titles.length === 1 ? "" : "s"} with ${selected.data("label")}:\n${titles.map(title => `• ${title}`).join("\n")}`;
      }
    }
    tooltip.style.display = "block";
    positionTooltip(event);
  });
  cy.on("mousemove", "node", positionTooltip);
  cy.on("mouseout", "node", () => { tooltip.style.display = "none"; });
  cy.on("dragfree", "node", () => {
    if (!mobileFocusActive) overviewPositions = positionsNow();
    publishView();
  });
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
  // Streamlit can scroll outside the graph's DOM ancestry, which Cytoscape does
  // not observe. Refresh synchronously before its pointer handlers as a fallback.
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

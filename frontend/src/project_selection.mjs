// Expand only through the selected PI's projects; never through fellow PIs' projects.
export function selectionNeighborhood(selected, revealFellowPis) {
  const direct = selected.closedNeighborhood();
  const projects = selected.neighborhood('node[kind = "Project"]');
  const expanded = revealFellowPis && selected.data("kind") === "PI"
    ? direct.union(projects.closedNeighborhood()) : direct;
  return { direct, expanded, secondary: expanded.difference(direct) };
}

export function mobileFocusPositions(selected, revealFellowPis) {
  const neighbors = selectionNeighborhood(selected, revealFellowPis).expanded.nodes().not(selected).toArray()
    .sort((a, b) => a.data("label").localeCompare(b.data("label")));
  const dense = neighbors.length > 2;
  const rowGap = neighbors.length > 8 ? 75 : 105;
  const positions = { [selected.id()]: { x: 180, y: 25 } };
  neighbors.forEach((node, index) => {
    positions[node.id()] = {
      x: dense ? (index % 2 === 0 ? 90 : 270) : 180,
      y: 135 + Math.floor(index / (dense ? 2 : 1)) * rowGap,
    };
  });
  return { positions, dense };
}

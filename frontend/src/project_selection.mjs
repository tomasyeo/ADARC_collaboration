// Expand only through the selected PI's projects; never through fellow PIs' projects.
export function selectionNeighborhood(selected, revealFellowPis) {
  const direct = selected.closedNeighborhood();
  const projects = selected.neighborhood('node[kind = "Project"]');
  const expanded = revealFellowPis && selected.data("kind") === "PI"
    ? direct.union(projects.closedNeighborhood()) : direct;
  return { direct, expanded, secondary: expanded.difference(direct) };
}

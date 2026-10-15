import assert from "node:assert/strict";
import test from "node:test";
import cytoscape from "cytoscape";
import { selectionNeighborhood } from "./project_selection.mjs";

test("PI expansion includes shared participation but stops before unrelated projects", () => {
  const cy = cytoscape({ headless: true, elements: [
    ...["a", "b", "c"].map(id => ({ data: { id, kind: "PI" } })),
    ...["x", "y", "z"].map(id => ({ data: { id, kind: "Project" } })),
    ...[["a", "x"], ["a", "y"], ["b", "x"], ["b", "y"], ["c", "y"], ["b", "z"]]
      .map(([source, target]) => ({ data: { id: source + target, source, target } })),
  ] });
  try {
    const ids = collection => collection.map(element => element.id()).sort();
    const direct = selectionNeighborhood(cy.$id("a"), false);
    assert.deepEqual(ids(direct.expanded), ["a", "ax", "ay", "x", "y"]);
    assert.equal(direct.secondary.length, 0);
    const expanded = selectionNeighborhood(cy.$id("a"), true);
    assert.deepEqual(ids(expanded.secondary), ["b", "bx", "by", "c", "cy"]);
    assert.equal(expanded.expanded.contains(cy.$id("z")), false);
    assert.equal(expanded.expanded.contains(cy.$id("bz")), false);
    const project = selectionNeighborhood(cy.$id("x"), true);
    assert.deepEqual(ids(project.expanded), ["a", "ax", "b", "bx", "x"]);
    assert.equal(project.secondary.length, 0);
  } finally {
    cy.destroy();
  }
});

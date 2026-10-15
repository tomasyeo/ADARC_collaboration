import assert from "node:assert/strict";
import test from "node:test";
import cytoscape from "cytoscape";
import { selectionNeighborhood, mobileFocusPositions } from "./project_selection.mjs";

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

test("mobile focus follows the new selected PI and the reveal toggle", () => {
  const cy = cytoscape({ headless: true, elements: [
    ...["a", "b"].map(id => ({ data: { id, label: id, kind: "PI" } })),
    ...["x", "z"].map(id => ({ data: { id, label: id, kind: "Project" } })),
    ...[["a", "x"], ["b", "x"], ["b", "z"]]
      .map(([source, target]) => ({ data: { id: source + target, source, target } })),
  ] });
  try {
    const first = mobileFocusPositions(cy.$id("a"), true).positions;
    assert.deepEqual(first.a, { x: 180, y: 25 });
    assert.ok(first.b);
    assert.equal(first.z, undefined);
    const second = mobileFocusPositions(cy.$id("b"), true).positions;
    assert.deepEqual(second.b, { x: 180, y: 25 });
    assert.notDeepEqual(second.a, first.a);
    assert.ok(second.z);
    const hidden = mobileFocusPositions(cy.$id("b"), false).positions;
    assert.equal(hidden.a, undefined);
    assert.ok(hidden.x);
    assert.ok(hidden.z);
  } finally {
    cy.destroy();
  }
});

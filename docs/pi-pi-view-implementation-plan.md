# PI shared projects view: implementation plan and review

## Status and decisions

This plan is implemented on `main` (originally developed on the
`feature-improvements` branch). The maintained input remains
`data_source/project_participant.txt`: one project–PI participation per row.
The original workbook is historical. Do not add a second maintained pair
table, stable external IDs, years, project leads, or inferred relationships.

The PI–PI view uses **raw counts**, not normalized scores:

- A PI's count is the number of distinct projects listing that PI.
- A pair's count is the number of distinct projects listing both PIs.
- A pair means *co-participation in listed projects*. It does not establish
  direct work between those people.

Agreed interface decisions are the **PI shared projects** page name, a matrix
opening on both pages, all PI–PI ties visible by default, a PI selection that
follows the user between pages, and one searchable **Find a PI or PI pair**
control on the new page. The agreed performance approach is one validated TSV
read per rerun, page-specific derivation, lazy tab rendering, and no cache
initially. The prototype illustrated the selected-pair state; the implemented
page must show the complete current source.

The current TSV has 29 projects, 18 PIs, and 107 participation rows. Its
PI–PI projection has 77 unordered pairs with at least one shared project:
40 pairs share one project and 37 share two or more. These values are review
baselines, not hard-coded product limits.

The Graphviz files in `prototypes/output/` are exploratory. Their network
omits one-project ties to show a simpler static layout. The Cytoscape
page shows **all** PI nodes and all PI–PI ties, drawing one-project
ties thin and pale. This all-ties default is agreed; tune contrast and line
width after inspecting the implemented Cytoscape view. Do not add a default
`≥2` visibility filter.

## 1. Derive the PI–PI data

**Ingestion lifecycle.** Streamlit reruns the app for user interactions and
page navigation; there is no one-time ingestion at server startup. On each
rerun, the entry point reads and validates the TSV once and creates the base
`CollaborationData`. Only the active page renders. The Projects and PIs page
uses the existing memberships and binary matrix; the PI shared projects page
derives the PI–PI projection from that same validated data when it is active.
Do not read the TSV independently in each page or persist a second processed
source. This dataset is small enough to recompute on reruns; avoid a cache
until measurement shows a need. A source change takes effect on the next
rerun, including validation errors, changed counts, and selection cleanup.
Graph callbacks should queue a requested selection; the entry point validates
it against the freshly loaded data before applying it on that rerun. This
avoids a second TSV read solely for click validation.

**Performance priority.** On one local measurement of the current source,
`load_data()` averaged about 1.4 ms and a simple PI–PI projection about
0.15 ms per call. These are machine-specific observations, not page-load
targets. Focus first on mounting only the active page and tab, then on
preserving Cytoscape's positions and viewport without recomputing layout for
ordinary selections. Measure the completed page before adding a cache. If
source processing later becomes material, use `st.cache_data` keyed to TSV
content so edits invalidate the result; do not use a process-wide mutable
`st.cache_resource` object for these data tables.

For the PI–PI projection, take each project's unique PI names and enumerate
unordered pairs.
Accumulate the project title as evidence for each pair. Derive:

| Structure | Meaning |
| --- | --- |
| `projects_by_pi[name]` | Distinct project titles listing the PI. |
| `shared_projects[(pi_a, pi_b)]` | Distinct project titles listing both PIs; pair key has a deterministic name order. |
| PI × PI count matrix | Off diagonal: length of `shared_projects` for the pair; diagonal: length of `projects_by_pi`. |
| PI network | One node per PI and one undirected edge for every pair with count at least 1. |

Keep exact display names and titles from the TSV. Use generated internal IDs
only inside the app; the names in the current TSV cannot distinguish two
different people with the same display name. Build the projection in memory
on active-page reruns. Keep the project-title evidence available to detail
tables even if the network sends only PI names or IDs in click events.

The matrix diagonal is **project count**, not self-collaboration. Off-diagonal
zero means no shared project is listed in this source. A project with 11 PIs
contributes up to 55 PI pairs, so edge counts measure repeated listing, not
effort or collaboration strength.

## 2. Organize the Streamlit interface

Keep `app.py` as the deployment entry point and use `st.Page` with
`st.navigation(position="top")` for two top-level pages:

1. **Projects and PIs** (default): retain the current project × PI matrix,
   project–PI Cytoscape network, and complete participation table.
2. **PI shared projects**: add a PI × PI matrix, PI–PI Cytoscape network, and
   a project-evidence table for a selected PI or pair.

Both pages open with their **matrix**. Keep the same order and placement for
title, search, summary metrics, Matrix and Network views, legend, and selected
details. Use distinct legends and color scales: page one is binary
participation; page two displays raw counts. Do not imply that a marked
project–PI cell and a numbered PI–PI cell have the same unit.
Use three clear metrics per page: Projects / PIs / Participations on the
existing page, and PIs / Pairs sharing a project / Source projects on the new
page. Do not show the symmetric PI × PI cells as twice as many relationships.

On the PI shared projects page, place one searchable **Find a PI or PI pair**
control in the same position as the current page's search control. Include
every PI and every pair with at least one shared project: 18 PI choices and
77 pair choices for the current source. Distinguish the option types in their
labels and show each pair's raw count. A PI selection shows that person's
project count, complete project list, and other PIs ranked by raw
shared-project count. A pair selection shows both names, its exact count,
and every shared project title. **Show all** clears the semantic selection.
Cytoscape node and edge clicks should update the same details. The searchable
control is the primary keyboard and touch route when a thin edge is hard to
tap. A browsable pair table may supplement it, but must not become a second
maintained source. Matrix hover exposes full names and counts. Test matrix
cell selection against the pinned Plotly and Streamlit versions before
promising it as an interaction; search must provide equivalent details
regardless.

Show a compact selected-name and count summary immediately below the search
control so a network click has visible feedback without scrolling past the
matrix. Keep complete project-title evidence in a persistent detail section
below the active view; do not crowd hover text with long title lists.

Keep the existing project's selection behavior intact. Store one semantic
selection with an explicit type: Project, PI, or unordered PI Pair. A PI
selection carries across pages and is highlighted on both. A selected project
has no equivalent on the PI shared projects page; a selected pair has no
equivalent on the Projects and PIs page. In either case, the destination page
opens without a highlight while the semantic selection remains available on
return. This preservation is agreed: switching pages alone must not mutate
the semantic selection; an explicit **Show all** action clears it. Store the
selection separately from page-specific widget keys so it survives
navigation. Validate all browser click events against the current
source before changing it. Clear or reconcile a selection when a TSV update
removes its project, PI, or pair. Use distinct component keys for the two
Cytoscape graphs so layout, zoom, and drag state cannot leak between them.

Render only the active Matrix or Network view on each page. In the pinned
Streamlit version, `st.tabs` supports stateful tabs with
`on_change="rerun"`; conditionally render the active tab via its `.open`
property. Verify this with both Cytoscape components during implementation.
This retains the current tab style while avoiding two expensive graphs being
mounted when only one is visible. A first visit to either page opens its
matrix. If a user later returns to its Network tab, preserve that graph's
positions and viewport for the same source pairs, even though the tab was
unmounted while away.

## 3. Visualize the PI–PI counts

**Matrix.** Show all PIs on both axes in a stable order. Print nonzero raw
counts in cells; show exact values again in hover and a selected-pair detail
area. Leave zero cells quiet but identify them in the legend. Use a sequential
count scale for off-diagonal cells, a distinct zero treatment, and a separate
diagonal treatment labeled **Projects for this PI**. An off-diagonal cell is
labeled **Projects shared by these two PIs**. Show full names through hover,
search, and a table when axis labels must be shortened. Highlight a selected
PI's row and column; highlight both symmetric cells for a selected pair. Do
not double count symmetric cells in metrics. The eight-PI mockup is only a
layout example; the production matrix must include all PIs.

**Cytoscape network.** Show every PI and all pairs with at least one shared
project; for the current source this means 18 nodes and 77 edges. Circle
**area** should increase with each PI's raw project count, within a restrained
minimum and maximum diameter. Exact counts remain visible in the detail area.
One-project edges are thin and pale. For counts of two or more, use more
contrast and modestly increasing line width. Do not label all edges at once;
show the exact count and supporting project titles when an edge is selected.
Use border or halo changes for selection so selection does not alter the
size/count encoding. Keep a legend stating both units.

Start with a deterministic layout, offer fit and recompute controls, and
preserve user drag/zoom state across ordinary reruns for the same validated
source. An ordinary selection must not trigger a fresh layout. Reset that
state when source pairs change. Allow selecting a PI to
emphasize its incident edges and neighbors, while keeping the full graph
available. Preserve the existing Cytoscape click hit-testing behavior after
scroll, pan, zoom, recompute, and drag. Treat node distance as layout only.
If the pale one-project edges still obscure the dense center, improve local
focus or edge styling without making a hidden-edge filter the default.

**Mouse-over and selection.** A PI circle's tooltip shows the full PI name
and raw number of distinct projects listing that PI. A line's tooltip shows
both full names, their raw shared-project count, and a prompt to select it
for the project titles. An off-diagonal matrix cell shows both full names and
their shared-project count; a diagonal cell shows the full name and that PI's
own project count, explicitly labeled as a total. Keep hover content short:
do not put a long project-title list over the graph. Selecting a line opens
the complete shared-project title list in a persistent detail area. An
off-diagonal cell does the same if cell selection proves reliable in the
pinned versions. Selecting a circle opens that PI's projects and its other
PI connections. The single searchable control provides the same details for
keyboard and touch users, who cannot depend on mouse-over.

## 4. Implementation sequence

1. Add a small projection module that derives PI project counts, pair counts,
   and shared-project title lists from validated memberships. Do not edit the
   maintained TSV or write a processed data file.
2. Introduce top-level navigation and move the current page into a page
   function/module without changing its data meaning or default matrix view.
3. Add the PI shared projects matrix and its search/detail table. Confirm every
   number against the source before adding the network.
4. Add a separate PI–PI Cytoscape payload and view, reusing the installed
   frontend dependency and applicable interaction helpers. Avoid forcing the
   existing two-column bipartite layout and its assumptions onto PI–PI data.
5. Connect PI selection across pages and pair selection within the new page.
   Then check keyboard, narrow-screen, and touch use.
6. Update README and development documentation for the implemented behavior;
   rebuild and commit the browser bundle alongside frontend source changes.

## 5. Acceptance checks

- Independently read the TSV for a reconciliation check. The sum of diagonal
  project counts equals participation rows. For every distinct PI pair, the
  matrix count, graph edge weight, and shared-project title list agree.
- The sum of pair weights equals the sum of `k × (k − 1) / 2` over projects,
  where `k` is the project's distinct PI count. The current 29/18/107,
  77/40/37 figures are review baselines only.
- All 18 PIs appear in the full PI–PI matrix and network, including the four
  omitted from the static Graphviz network. No edge is inferred without a
  source project listing both endpoints.
- Each page opens with its matrix; the labels, selection details, and metrics
  have the correct units. Moving between pages preserves a selected PI but
  does not turn a selected project into a PI.
- The combined search offers all current PIs and all 77 nonzero pairs;
  selecting one reaches the same details as a node or edge click. The pair
  option, near-search summary, and detail panel show the raw count. The panel
  lists every shared project title. Verify source updates that remove a selected PI or
  pair, and graph click behavior after scroll, zoom, pan, recompute, and drag.
- The diagonal is visually distinct and labeled as a PI's own project total;
  off-diagonal cells show shared-project counts. Verify the two symmetric
  cells for a selected pair and that pair metrics count it only once.
- Inspect 77-edge density, contrast of one-project edges, circle-size
  readability, long names, narrow screens, and touch. The count remains
  available in text when color or size is hard to distinguish.
- Run the existing Python checks, add focused reconciliation checks for the
  new projection, build the frontend, and smoke-test both pages locally.
- Confirm the TSV is read once per rerun, only the active page/tab mounts its
  visualization, ordinary selection retains network positions and zoom, and
  page/tab re-entry restores the same graph state for unchanged source pairs.
  A source edit appears on the next rerun without manual cache clearing.

## Critical review: risks and planned fixes

| Risk or ambiguity | Fix included in this plan |
| --- | --- |
| “Collaboration” may imply direct PI-to-PI work. | Name the page “PI shared projects,” use “co-participation” in explanatory text, and show title evidence for a pair. |
| The static `≥2` prototype could be mistaken for the app specification. | State that the app shows all `≥1` ties, including thin one-project edges and all PI nodes. |
| An 11-person project produces many pair edges and may dominate the drawing. | Retain raw counts as agreed, explain their meaning, keep one-project edges subdued, and provide PI/pair focus plus the exact matrix. |
| The matrix diagonal could be read as a self-collaboration. | Style it separately, label it “Projects for this PI,” and label off-diagonal cells as shared-project counts. |
| Variable circle diameter could exaggerate differences. | Scale area with project count, cap the size range, and show exact counts in text. |
| Switching pages could reset a widget or leak the bipartite graph's state. | Separate semantic selection from widget keys and give each Cytoscape view its own key and layout signature. |
| Thin edges may be hard to tap and edge clicks alone exclude keyboard users. | Use the agreed combined PI-or-pair search as the primary selection path; test pointer and touch selection. |
| The full title list may sit below a tall matrix or network. | Show a compact selected-name and count summary near search, with complete evidence in a persistent detail section. |
| Unmounting an inactive tab may discard Cytoscape's layout. | Retain each graph's view snapshot in Streamlit session state and pass it back on remount. Browser-only component state reset during review. |
| Two full graphs may render on every rerun. | Conditionally render the active tab and verify the behavior with Streamlit 1.65.0. |
| A process-wide one-time precompute could become stale after a TSV edit and adds shared-mutable-state concerns. | Recompute the small validated source per rerun; consider `st.cache_data` keyed to content only if profiling later justifies it. |
| The existing Cytoscape component assumes two node types and a two-column layout. | Add a PI–PI-specific payload/view, sharing only interaction code that actually applies. |
| Stale or malformed browser events could select a pair absent from the current TSV. | Validate node and pair events against the current derived projection before updating shared state. |

Implementation review used a circular default layout after a spring overview
clustered several nodes. Recompute still offers a force layout. Visual tuning
of opacity, width, and size bounds can continue without changing raw counts
or hiding one-project ties by default. Matrix-cell click selection was left
out; the combined search reaches every PI and nonzero pair and supplies the
keyboard and touch path to the same details. A post-implementation review also
found that browser-only graph state vanished after tab remounting; both
components now publish view snapshots to Streamlit session state. Recompute
also applies the same zoom cap as Fit to view.

## References

- [Streamlit page navigation](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation)
- [Streamlit widget state across pages](https://docs.streamlit.io/develop/concepts/multipage-apps/widgets)
- [Streamlit tabs](https://docs.streamlit.io/develop/api-reference/layout/st.tabs)
- [Cytoscape.js documentation](https://js.cytoscape.org/)

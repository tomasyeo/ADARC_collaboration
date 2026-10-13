# Development guide

This guide is for maintainers and contributors working on the Streamlit app. The [README](../README.md) covers a quick local run and deployment; the earlier [data design](stage-1-2-data-design.md), [project participation plan](matrix-network-app-plan.md), and [PI shared projects plan](pi-pi-view-implementation-plan.md) record design decisions. This file describes the current implementation and the workflow for changing it.

## Source of truth and meaning

`data_source/project_participant.txt` is the only maintained data input. It is a UTF-8 TSV with the exact header `project<TAB>participant` and one recorded project–PI participation per row. Edit this file to correct the data. The original workbook is a historical reference and is not read by the app.

The app derives all other structures in memory. A project–PI link means recorded participation. A PI–PI link means both names occur in at least one source project; its count is the number of distinct shared projects. The source does not establish a project lead, direct PI-to-PI collaboration, year, or effort. The current source has 29 projects, 18 PIs, and 107 distinct participation pairs, yielding 77 PI pairs; use these as review baselines, not permanent constraints.

An exact title or name identifies an entity in this version. Two distinct projects with the same title, or two people with the same name, cannot be distinguished by the TSV. Generated IDs are temporary: project IDs depend on sorted titles, and PI IDs depend on names. Do not use them as stable external references.

## Code map

| Path | Responsibility |
| --- | --- |
| `data_source/project_participant.txt` | Maintained participation pairs. |
| `data_model.py` | Validate TSV rows, derive IDs, pair tables, and the project × PI matrix. |
| `pi_projection.py` | Derive PI project-title lists, PI-pair title evidence, and the PI × PI count matrix. |
| `app.py` | Two-page Streamlit navigation, matrices, shared semantic selection, counts, and detail tables. |
| `network_component.py` | Build the bipartite graph, prepare Cytoscape elements and initial positions, register the Streamlit component. |
| `pi_network_component.py` | Prepare the PI-pair Cytoscape graph with raw counts and a circular overview. |
| `frontend/src/network.js` | Render Cytoscape, handle layouts, focus, selection, drag, zoom, and component state. |
| `frontend/src/pi_network.js` | Render the PI network, pair selection, count styling, layout controls, and viewport state. |
| `frontend/network.css` | Network controls and canvas styling, including the narrow-screen frame. |
| `frontend/dist/*.js` | Generated browser bundles committed for deployment. Do not edit them directly. |
| `appctl` | Local Streamlit start, stop, reset, and status commands; records and logs are ignored under `.run/`. |
| `.devcontainer/devcontainer.json` | Optional Codespaces environment that installs Python dependencies and starts Streamlit on port 8501. |
| `tests/test_app.py` | Source validation and reconciliation of both matrices, graphs, and serialized network links. |

The data path is:

```text
data_source/project_participant.txt
  → data_model.load_data()
  → app.py: navigation and validated semantic selection
  → Projects and PIs: binary matrix, records, network_component.py → frontend/src/network.js
  → PI shared projects: pi_projection.py → count matrix, evidence,
    pi_network_component.py → frontend/src/pi_network.js
```

The entry point reads and validates the TSV once per Streamlit rerun. Only the active page derives its view, and only its active Matrix or Network tab mounts the visualization. The project matrix and graph read the same `CollaborationData`; each bipartite edge maps to one TSV pair. The PI projection enumerates unordered PI pairs within each project and retains the titles as evidence. Its diagonal is each PI's own project count, not a self-relationship. The browser queues a clicked node or pair; the next rerun validates it against the fresh source before changing semantic selection. Each page has its own search widget; PI selection carries across pages, while a project or pair selection stays available when returning to its page. A retained selection appears in the other page's search control with a note that it has no highlight there; Show all clears it. Search provides the keyboard route to every PI and nonzero pair.

## Local setup

From the repository root, use Python 3.11 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

After setup, `./appctl start`, `./appctl stop`, `./appctl reset`, and
`./appctl status` manage a local server on `127.0.0.1:8501`. Use `--port N`
for another port. `reset` restarts a server started by this wrapper; reload
the browser to create a fresh Streamlit session. The wrapper refuses to stop
an unrelated process using the port.

Python dependencies are pinned in `requirements.txt`. Node.js and npm are needed only when changing the Cytoscape frontend. The pinned frontend dependencies are in `frontend/package-lock.json`.

The optional Dev Container uses Python 3.11, installs `requirements.txt`, and starts Streamlit when attached. Its launch command disables Streamlit's CORS and XSRF protections, so review the forwarded port's visibility before using that environment with non-public data.

## Changing the source data

1. Edit `data_source/project_participant.txt` using its existing two-column TSV format. Preserve the exact display strings and do not add inferred relationships.
2. Run `.venv/bin/python -m unittest discover -s tests -v`. The loader rejects malformed rows, empty fields, leading or trailing whitespace, duplicate pairs, and generated PI ID collisions. It reports possible name or title variants as warnings for human review.
3. Start the app and check the counts, the affected matrix row or column, the network neighborhood, and the detail table. A valid addition or deletion may change the 29/18/107 baseline.
4. Commit the TSV correction with the relevant code or documentation change. Generated IDs and processed tables should not be written back to the TSV.

If two entities need the same display string, this format cannot represent them separately. Design a maintained key in the source before adding such records.

## Changing the app or network

For Python changes, run the test suite and smoke-test the affected Streamlit view. For frontend changes, rebuild the browser bundle from the repository root:

```sh
cd frontend
npm ci
npm run build
cd ..
```

Commit frontend source and both generated files in `frontend/dist/`. Streamlit registers the bundled JavaScript when its Python process starts, so restart the Streamlit server after rebuilding. Streamlit deployment uses the committed bundles and does not need a Node build step.

The network defaults to two columns, with projects and PIs ordered to reduce crossings. The force layout and its recompute button provide an exploratory arrangement; distance does not measure collaboration strength. The focus button shows a selected node and its immediate neighbors. Each component sends layout and viewport snapshots to separate Streamlit session-state keys and receives them when remounted; a changed source signature invalidates the saved state. On narrow screens, a focused neighborhood gets a compact arrangement. The frontend refreshes Cytoscape's cached canvas bounds when the page moves and immediately before a pointer click, so page scrolling does not offset node hit testing. These refreshes preserve the current zoom and pan.

The PI network defaults to a circular overview, so each of the 18 source PIs has a distinct starting position. Recompute runs a force layout with a zoom cap; reset returns to the circle. Circle area increases with raw PI project count. Every nonzero pair appears as an edge; one-project edges are pale, and repeated shared projects receive more contrast and width. Selecting an edge shows all supporting titles below the graph. A graph click sends its selection and current layout snapshot in one event, so the selection rerun restores the positions and viewport from that same click. The graph also retains its view across tab re-entry for an unchanged projection. Its page has a separate Cytoscape key and saved view, so it cannot inherit the project graph's layout.

## Verification before review

Run the automated checks:

```sh
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

The tests check source validation, row-order independence, a sample source update, and equality of the TSV pairs, both matrices, both graph edge sets, and serialized Cytoscape links. They do not exercise browser interactions. When changing the frontend, also check these behaviors in the running app:

- Selecting a project and a PI updates the matrix highlight, network highlight, and detail table.
- Clicking a graph node updates the shared selector; clearing selection restores the full view.
- After scrolling the page around the graph, click a colored node and confirm its highlight and selector both update. Repeat after zooming, panning, recomputing the force layout, and dragging a node.
- Focus toggles on and off, and both layout choices, force recompute, reset, drag, zoom, and fit still work.
- Long names are available in the selector, hover tooltip, or detail table; inspect the view at a narrow width.
- Both pages open on Matrix. The PI page offers all PIs and nonzero pairs in one searchable selector; a selected pair shows its count and every title.
- After a force recompute with Show all selected, clicking a PI circle or pair edge updates the selector and details without reverting the layout. Clearing a graph selection also keeps the layout. PI selection carries between pages; a project or pair selection is retained for return without highlighting the other page.
- A retained out-of-page selection remains visible in search; choose Show all to clear it from either page.
- Recompute, reset, focus, zoom, and drag the PI network, then leave and return to its tab; positions and viewport should persist for the same source.

Use a feature branch for changes and review the diff before integrating it into `main`. The public GitHub repository exposes the TSV's titles and names. The workbook and prototype images are excluded from Git; check newly added files before pushing. Streamlit deployment is a separate step after integration.

## Known limits

- A dense force layout can still overlap labels and cluster highly connected nodes. Use the two-column overview or focus mode to inspect memberships.
- The graph canvas does not provide direct keyboard navigation among nodes. The searchable selector and record table provide access to all source relationships.
- A dense PI-pair graph still crosses many edges. Use its matrix or search for exact counts and source-title evidence; graph distances have no data meaning.
- Generated IDs change when display strings change, and project IDs can shift when projects are added or renamed.

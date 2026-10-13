# Development guide

This guide is for maintainers and contributors working on the Streamlit app. The [README](../README.md) covers a quick local run and deployment; the earlier [data design](stage-1-2-data-design.md) and [visualization plan](matrix-network-app-plan.md) record the design decisions. This file describes the implementation and the workflow for changing it.

## Source of truth and meaning

`data_source/project_participant.txt` is the only maintained data input. It is a UTF-8 TSV with the exact header `project<TAB>participant` and one recorded project–PI participation per row. Edit this file to correct the data. The original workbook is a historical reference and is not read by the app.

The app derives all other structures in memory. A link means that a PI is listed as participating in a project. The source does not establish a project lead, direct PI-to-PI collaboration, year, or effort. The current source has 29 projects, 18 PIs, and 107 distinct pairs; use these as a review baseline, not as permanent constraints.

An exact title or name identifies an entity in this version. Two distinct projects with the same title, or two people with the same name, cannot be distinguished by the TSV. Generated IDs are temporary: project IDs depend on sorted titles, and PI IDs depend on names. Do not use them as stable external references.

## Code map

| Path | Responsibility |
| --- | --- |
| `data_source/project_participant.txt` | Maintained participation pairs. |
| `data_model.py` | Validate TSV rows, derive IDs, pair tables, and the project × PI matrix. |
| `app.py` | Streamlit page, matrix, shared selection, counts, and detail tables. |
| `network_component.py` | Build the bipartite graph, prepare Cytoscape elements and initial positions, register the Streamlit component. |
| `frontend/src/network.js` | Render Cytoscape, handle layouts, focus, selection, drag, zoom, and component state. |
| `frontend/network.css` | Network controls and canvas styling, including the narrow-screen frame. |
| `frontend/dist/network.js` | Generated browser bundle committed for deployment. Do not edit it directly. |
| `.devcontainer/devcontainer.json` | Optional Codespaces environment that installs Python dependencies and starts Streamlit on port 8501. |
| `tests/test_app.py` | Source validation and reconciliation of TSV, matrix, graph, and serialized network links. |

The data path is:

```text
data_source/project_participant.txt
  → data_model.load_data()
  → app.py: matrix, selector, details, record table
  → network_component.graph_payload()
  → frontend/src/network.js: Cytoscape network
```

The matrix and graph read the same validated `CollaborationData`. Graph nodes have distinct internal namespaces (`project:<id>` and `participant:<id>`). Each graph edge maps to one TSV pair. The browser sends a clicked node's type and exact display name to Streamlit; `app.py` checks that it exists in the current source before updating the shared selection. The selector is also the keyboard-accessible way to choose any project or PI.

## Local setup

From the repository root, use Python 3.11 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

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

Commit both the frontend source and `frontend/dist/network.js`. Streamlit registers the bundled JavaScript when its Python process starts, so restart the Streamlit server after rebuilding. Streamlit deployment uses the committed bundle and does not need a Node build step.

The network defaults to two columns, with projects and PIs ordered to reduce crossings. The force layout and its recompute button provide an exploratory arrangement; distance does not measure collaboration strength. The focus button shows a selected node and its immediate neighbors. The frontend retains positions and viewport state across ordinary Streamlit reruns for the same source pairs; changing the set of pairs resets that state. On narrow screens, a focused neighborhood gets a compact arrangement. The frontend refreshes Cytoscape's cached canvas bounds when the page moves and immediately before a pointer click, so page scrolling does not offset node hit testing. These refreshes preserve the current zoom and pan.

## Verification before review

Run the automated checks:

```sh
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

The tests check source validation, row-order independence, a sample source update, and equality of the TSV pairs, matrix marks, graph edges, and serialized Cytoscape links. They do not exercise browser interactions. When changing the frontend, also check these behaviors in the running app:

- Selecting a project and a PI updates the matrix highlight, network highlight, and detail table.
- Clicking a graph node updates the shared selector; clearing selection restores the full view.
- After scrolling the page around the graph, click a colored node and confirm its highlight and selector both update. Repeat after zooming, panning, recomputing the force layout, and dragging a node.
- Focus toggles on and off, and both layout choices, force recompute, reset, drag, zoom, and fit still work.
- Long names are available in the selector, hover tooltip, or detail table; inspect the view at a narrow width.

Use a feature branch for changes and review the diff before integrating it into `main`. The public GitHub repository exposes the TSV's titles and names. The workbook and prototype images are excluded from Git; check newly added files before pushing. Streamlit deployment is a separate step after integration.

## Known limits

- A dense force layout can still overlap labels and cluster highly connected nodes. Use the two-column overview or focus mode to inspect memberships.
- The graph canvas does not provide direct keyboard navigation among nodes. The searchable selector and record table provide access to all source relationships.
- Generated IDs change when display strings change, and project IDs can shift when projects are added or renamed.

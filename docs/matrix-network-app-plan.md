# Streamlit implementation plan: matrix, network, and release

## Scope and source

This plan covers the three visualization stages discussed after [stages 1 and 2](stage-1-2-data-design.md). The maintained source is `project_participant.txt`; the app validates and reads that TSV. Each `(project, participant)` pair means that the named PI participates in the named project. The same in-memory memberships drive both views. The original workbook is a historical reference, not a second maintained input.

The current file contains 29 projects, 18 PIs, and 107 unique pairs. These are verification baselines, not fixed limits. The app does not infer project leads, direct PI-to-PI work, or any relationship missing from the source.

## 1. Build the project × PI matrix

**Data:** Derive a binary matrix with projects as rows and PIs as columns. A marked cell corresponds to exactly one validated TSV pair. An unmarked cell means *not listed in this source*.

**Display:** Render the matrix as a Plotly heatmap in Streamlit. Use one clear mark color for recorded participation and a quiet background for unmarked cells; do not use a numeric gradient. Show full project and PI names in hover text and in the selection detail area. Sort both axes by full source title or name. Shorten visible axis labels only where needed for fit, without changing the underlying strings. Provide an accompanying searchable relationship table or selected-project roster so the complete data remains usable when the grid is crowded or a screen is narrow.

**Selection:** Provide one searchable Streamlit control containing both node types, labeled so a project cannot be confused with a PI. Store the selected type and exact source title or name in Streamlit session state, not a generated ID. Clear a selection if its title or name is no longer present after a source update. Selecting a project highlights its matrix row and lists its PIs; selecting a PI highlights its column and lists its projects. The selected row or column remains highlighted across ordinary app reruns. Selection through the control is the required path; chart-cell selection is optional after its behavior has been verified.

**Matrix acceptance checks:** The sum of marked cells equals the number of validated TSV pairs. Each project row and PI column matches the corresponding source membership list. Verify the longest labels, hover text, selection persistence, keyboard use of the selector, and a usable roster/table path on a narrow screen before starting the network.

## 2. Add the project–PI network

**Graph:** Create an undirected, two-type graph from the same memberships. There is one node per distinct project, one node per distinct PI, and one edge per source pair. Use separate internal ID namespaces for project and PI nodes. Do not add project-to-project or PI-to-PI edges.

**Layout and display:** Render the network with Cytoscape.js in a Streamlit component v2. Default to two columns: projects at left and PIs at right. Order each column by the average positions of its neighbors to reduce avoidable crossings. Offer a force layout with a recompute control for exploratory rearrangement. Retain dragged positions and the viewport across Streamlit reruns for the same source pairs; a source update resets the layout. Distinguish node types with both shape and color. Make unselected edges subdued; use short visible labels where full titles would crowd the view. Show exact strings and membership counts on hover or in the detail area. Treat force-layout distance as a layout aid, not a measured strength of collaboration.

**Linked selection:** Use the same session-state selection as the matrix. Selecting a project emphasizes its node, incident edges, and participating PIs. Selecting a PI emphasizes its node, incident edges, and projects. Cytoscape node taps send the exact source name and type to Streamlit; the search control updates and the matrix highlights the corresponding row or column. Other nodes remain visible but muted unless the user enables selected-neighborhood focus. The detail area lists every connected name or title. Keep the searchable control and table as the keyboard-accessible path.

**Network acceptance checks:** For the current source, the graph has 47 nodes and 107 edges. Every edge maps to one TSV pair and one marked matrix cell. Highlighted neighbors and detail lists agree with the source. Test dense regions, long labels, zooming, and small-screen behavior. If the all-node view remains too crowded, make the selected node's immediate neighborhood the default focus while retaining a full-network overview as an optional view.

## 3. Verify and package for Streamlit deployment

**Reconciliation:** Recheck the three representations—raw TSV pairs, matrix marks, and network edges—as equal sets of project–PI relationships. Read the TSV independently for this check rather than comparing only two views made by the same transformation. Verify the current 107/29/18 baseline without hard-coding it as a permanent requirement. Test a deliberate source update in a disposable copy: adding or removing a pair must update both views, counts, and selected details; removing a selected title or name must clear that selection. Invalid input must show a useful validation message and must not produce partial views.

**Usability:** Confirm that the legend states what a mark and edge mean, and that the interface never presents co-participation as direct pairwise collaboration. Check full-name access, readable contrast, shape differences, keyboard access to the selector and relationship table, label clipping, and narrower layouts. Confirm that the matrix and relationship table preserve the complete record while the network supports exploration.

**Package:** Keep the Streamlit entry point, the maintained `project_participant.txt`, and a dependency file in the public GitHub repository. Pin Streamlit, pandas, NetworkX, and Plotly versions in `requirements.txt`; pin Cytoscape.js and the frontend build tool in the npm lockfile. Commit the built browser bundle so Streamlit deployment does not need Node.js. Use paths relative to the application/repository, not machine-specific absolute paths. Make source corrections in the TSV and commit them; the app validates the committed TSV at startup and does not write IDs or processed data back to it. The original workbook and prototype images remain excluded from the public repository. Do not add a database or a separate PyArrow/Parquet pipeline.

**Deployment boundary:** The public GitHub repository is `tomasyeo/ADARC_collaboration`. This Cytoscape implementation is developed on `feature-cytoscape`; it does not change the deployed app until the branch is integrated and Streamlit redeploys it.

## Reference documentation

- [Plotly heatmaps](https://plotly.com/python/heatmaps/)
- [Cytoscape.js documentation](https://js.cytoscape.org/)
- [NetworkX drawing](https://networkx.org/documentation/stable/reference/drawing.html)
- [Streamlit custom components v2](https://docs.streamlit.io/develop/concepts/custom-components/components-v2)
- [Streamlit Community Cloud file organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)
- [Streamlit Community Cloud sharing and visibility](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)

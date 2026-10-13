# ADARC project participation

This Streamlit app reads `data_source/project_participant.txt` and offers two pages. **Projects and PIs** shows the source participation pairs in a Plotly matrix, Cytoscape.js network, and full record table. **PI shared projects** shows each PI's project count and the number of projects listed for each PI pair, with a count matrix, network, and complete source-title evidence for selections. A PI selection follows you between pages.

For code ownership, data edits, frontend builds, and review checks, see the [development guide](docs/development.md).

The maintained source is a UTF-8 tab-separated file with exactly these columns:

```text
project	participant
```

Each row means that the named PI participates in the named project. Edit this TSV to correct or add records. The app rejects empty fields, extra columns, leading or trailing whitespace, and duplicate pairs. It warns about names or titles that differ only by case, spacing, or punctuation. Project and PI IDs are generated in memory each run; they are not stable identifiers across source changes.

## Run locally

Use Python 3.11 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./appctl start
```

Manage the local app with:

```sh
./appctl status
./appctl restart          # stop and start; reload the browser for a fresh session
./appctl stop
```

Pass `--port 8502` to any command to use another port. The wrapper manages only
processes it started. It writes its PID records and logs under the ignored
`.run/` directory. If port 8501 is occupied by another server, stop that server
before using `./appctl start`.

The prebuilt Cytoscape browser bundles are committed in `frontend/dist/`, so deployment only needs the Python dependencies. To change either network component, use Node.js and rebuild before committing:

```sh
cd frontend
npm ci
npm run build
```

Restart the Streamlit server after rebuilding so it registers the updated component bundles.

Run the validation and reconciliation checks with:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Deploy

Keep `app.py`, `data_model.py`, `pi_projection.py`, both network component modules, `data_source/project_participant.txt`, `requirements.txt`, and both files in `frontend/dist/` in the public GitHub repository. Connect that repository to Streamlit Community Cloud and choose `app.py` as the entry point. The historical workbook and prototype images are excluded by `.gitignore`; the app does not use them. The public repository and deployed app will expose the TSV's project titles and PI names.

This view records co-participation in a project. It does not imply that two PIs directly collaborated with one another or identify a project lead.

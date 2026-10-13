# ADARC project participation

This Streamlit app shows which PIs are listed for each project in `project_participant.txt`. The matrix and network both represent the same project–PI pairs. A shared search selection highlights a project row or PI column in the matrix and its immediate connections in the network. The full relationship table is available in the **All records** tab.

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
.venv/bin/streamlit run app.py
```

Run the validation and reconciliation checks with:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Deploy

Put `app.py`, `data_model.py`, `project_participant.txt`, and `requirements.txt` in the root of the public GitHub repository. Connect that repository to Streamlit Community Cloud and choose `app.py` as the entry point. The historical workbook and prototype images are excluded by `.gitignore`; the app does not use them. The public repository and deployed app will expose the TSV's project titles and PI names.

This view records co-participation in a project. It does not imply that two PIs directly collaborated with one another or identify a project lead.

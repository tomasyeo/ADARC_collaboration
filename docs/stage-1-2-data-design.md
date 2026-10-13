# Data preparation plan: stages 1 and 2

## Purpose and scope

Prepare the department's project–PI participation data for a Streamlit app. This plan covers validation and in-memory transformation only. The app's input is `project_participant.txt`, a UTF-8 tab-delimited file with exactly two columns: `project` and `participant`. Each row means that the named PI participates in the named project.

`project_participant.txt` is the sole maintained source for this version. Make corrections and additions in the TSV, validate them, and commit the updated file. The existing Excel workbook documents where the initial data came from; it is a historical reference and is not used to rebuild the TSV after subsequent edits.

The current TSV has 107 distinct participation rows, 29 project titles, and 18 PI names. These counts are a baseline for reviewing the first implementation, not permanent limits. No lead, role, year, effort, or direct PI-to-PI relationship is inferred.

For this two-column source, an exact project title identifies one project, and an exact PI name identifies one person. If two different projects share a title, or two people share a name, the TSV cannot distinguish them; add an explicit maintained key to the source before accepting such records. A renamed title or person is a source correction, not an automatically detected continuation of the old identity.

## Stage 1: Read and validate the source

1. Read the TSV as text, with UTF-8 encoding and tab separation. Require the exact header `project<TAB>participant` and reject unexpected columns.
2. Require a nonempty value in both fields of every data row. Preserve the full display strings. Flag leading or trailing whitespace for correction in the source rather than silently changing names or titles.
3. Reject duplicate `(project, participant)` pairs. Report the source line numbers for invalid or duplicate rows.
4. Warn when distinct titles or names become identical after case folding, whitespace normalization, or punctuation removal. Review any additional suspected spelling variants manually; do not use fuzzy matching to merge records or block an otherwise valid source.
5. Report the number of valid rows, distinct projects, distinct PIs, and participants per project. Compare the first run with the current 107/29/18 baseline to catch an accidental omission, while allowing intentional source updates.

Validation must stop the transformation when the header, required values, or unique-pair rule fails. Name or title variants are review warnings because similarity alone cannot establish identity. Review and resolve warnings in the TSV before publishing an update when they may change the project or PI counts.

## Stage 2: Derive IDs and analysis structures

Do not write generated IDs or processed tables back to the TSV. Generate the following structures in memory each time the validated source is loaded:

| Structure | Fields | Rule |
| --- | --- | --- |
| Projects | `project_id`, `project` | Assign integers `1..N` after sorting distinct full titles case-insensitively, with the exact title as a tie-breaker. |
| Participants | `pi_id`, `participant` | Derive `pi_id` by removing spaces and punctuation from the full name while retaining letters and digits. Preserve the original name for display. |
| Memberships | `project_id`, `pi_id` | One row for each validated TSV pair; require both IDs to resolve to one record. |
| Incidence matrix | Project rows × PI columns | Mark membership from the membership rows; do not maintain a separate edited copy. |

Check that every generated `pi_id` is nonempty and unique, including when compared without case. For example, `Ho-Huang` becomes `HoHuang`. If two names produce the same ID, stop and request an explicit resolution; never merge people or add an arbitrary suffix silently. Use distinct graph namespaces such as `project:1` and `participant:HoHuang` if a visualization library requires one shared string-ID field.

Project IDs are **temporary app identifiers**. Sorting makes them reproducible when TSV rows are reordered, but adding or renaming a project can renumber them. PI IDs can change if names change. Do not use either generated ID as a permanent external reference, database key across source versions, or public URL identifier. If persistent references become necessary, add explicitly maintained IDs to the source in a later design.

Keep the selected project or PI in app session state by its exact source title or name, together with its type, rather than by a generated ID. After a source reload, verify that the selected string still exists; otherwise clear the selection. Generated IDs are used only within the current loaded dataset.

## Implementation choice

Pandas is sufficient to load and transform the TSV; Python's standard library can handle string normalization and validation. Streamlit will consume the resulting in-memory data. Do not add a database, PyArrow processing, or Parquet files for this dataset. The matrix and network should both be derived from the same validated memberships.

## Completion checks

- The current source yields 107 unique memberships, 29 projects, and 18 PIs.
- Every input row maps to exactly one membership, and every membership maps back to an input row.
- Project and PI IDs are unique within their respective sets; no two PI names normalize to the same ID.
- Reordering TSV rows does not change the generated IDs or memberships.
- A source change that removes or renames the selected title or name clears the stale selection rather than selecting another record.
- Displayed project titles and PI names match the source strings exactly.
- An invalid source produces actionable messages with line numbers and no partial visualization data.

No source or processed-data file is changed by these stages.

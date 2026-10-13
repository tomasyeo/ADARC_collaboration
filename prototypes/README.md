# PI–PI projection prototype

Run `python3 prototypes/pi_projection.py` from the repository root with Graphviz
(`dot` and `sfdp`) installed. The script reads only the maintained
`data_source/project_participant.txt` and writes DOT, SVG, and PNG files to
`prototypes/output/`.

The generated `prototypes/output/` directory is ignored by Git. Run the script
locally to regenerate these exploratory renders.

- **Matrix:** All 18 PIs appear on both axes. An off-diagonal cell counts
  projects listing both people. The diagonal counts each PI's projects.
- **Network:** An edge appears only when its pair shares at least two projects;
  the edge label gives the count. The current source has 77 pairs with at least
  one common project, of which 37 meet this display threshold. Four PIs have
  only one-project ties and are omitted from the filtered network; they remain
  visible in the complete matrix.

These views show **co-participation in listed projects**, not proof of direct
person-to-person collaboration. The threshold is for readability; the matrix
retains every pairwise count. The source TSV remains authoritative.

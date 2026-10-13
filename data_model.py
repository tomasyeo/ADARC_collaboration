"""Validate the maintained TSV and derive the app's in-memory relationships."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


class SourceError(ValueError):
    """The TSV cannot be represented without losing or inventing relationships."""


@dataclass(frozen=True)
class CollaborationData:
    pairs: pd.DataFrame
    projects: pd.DataFrame
    participants: pd.DataFrame
    memberships: pd.DataFrame
    matrix: pd.DataFrame
    warnings: tuple[str, ...]


def _sort_key(value: str) -> tuple[str, str]:
    return (value.casefold(), value)


def _pi_id(name: str) -> str:
    return "".join(char for char in name if char.isalnum())


def _variant_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(char.casefold() for char in normalized if char.isalnum())


def _variant_warnings(values: list[str], kind: str) -> list[str]:
    groups: dict[str, list[str]] = {}
    for value in values:
        groups.setdefault(_variant_key(value), []).append(value)
    return [
        f"Possible {kind} variants: " + " / ".join(sorted(group, key=_sort_key))
        for group in groups.values()
        if len(group) > 1
    ]


def load_data(path: Path) -> CollaborationData:
    """Read exact display strings; stop on ambiguity, malformed rows, or duplicate pairs."""
    try:
        rows = [line.split("\t") for line in path.read_text(encoding="utf-8-sig").splitlines()]
    except (OSError, UnicodeError) as exc:
        raise SourceError(f"Could not read {path.name}: {exc}") from exc

    if not rows or rows[0] != ["project", "participant"]:
        raise SourceError("Line 1 must contain exactly: project<TAB>participant")

    errors: list[str] = []
    pairs: list[tuple[str, str]] = []
    seen: dict[tuple[str, str], int] = {}
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != 2:
            errors.append(f"Line {line_number}: expected exactly two tab-separated fields.")
            continue
        project, participant = row
        if not project or not participant:
            errors.append(f"Line {line_number}: project and participant must both be nonempty.")
        if project != project.strip() or participant != participant.strip():
            errors.append(f"Line {line_number}: remove leading or trailing whitespace in the TSV.")
        if not project.strip() or not participant.strip():
            continue
        pair = (project, participant)
        if pair in seen:
            errors.append(f"Line {line_number}: duplicate pair (first appears on line {seen[pair]}).")
        else:
            seen[pair] = line_number
            pairs.append(pair)
    if errors:
        raise SourceError("\n".join(errors))
    if not pairs:
        raise SourceError("The TSV contains no participation rows.")

    project_names = sorted({project for project, _ in pairs}, key=_sort_key)
    participant_names = sorted({participant for _, participant in pairs}, key=_sort_key)
    project_ids = {name: number for number, name in enumerate(project_names, start=1)}
    participant_ids = {name: _pi_id(name) for name in participant_names}
    id_owners: dict[str, str] = {}
    for name, generated_id in participant_ids.items():
        if not generated_id:
            raise SourceError(f"The generated PI ID for {name!r} is empty. Add a maintained key to the source.")
        folded = generated_id.casefold()
        if folded in id_owners:
            raise SourceError(
                f"Generated PI ID collision: {id_owners[folded]!r} and {name!r}. "
                "Resolve the source identities before loading."
            )
        id_owners[folded] = name

    pair_set = set(pairs)
    pair_frame = pd.DataFrame(sorted(pair_set, key=lambda item: (_sort_key(item[0]), _sort_key(item[1]))), columns=["project", "participant"])
    projects = pd.DataFrame(
        [(project_ids[name], name) for name in project_names], columns=["project_id", "project"]
    )
    participants = pd.DataFrame(
        [(participant_ids[name], name) for name in participant_names], columns=["pi_id", "participant"]
    )
    memberships = pair_frame.assign(
        project_id=pair_frame["project"].map(project_ids),
        pi_id=pair_frame["participant"].map(participant_ids),
    )[["project_id", "pi_id"]]
    matrix = pd.DataFrame(0, index=project_names, columns=participant_names, dtype=int)
    matrix.index.name = "project"
    matrix.columns.name = "participant"
    for project, participant in pair_set:
        matrix.at[project, participant] = 1

    warnings = tuple(
        _variant_warnings(project_names, "project title")
        + _variant_warnings(participant_names, "participant name")
    )
    return CollaborationData(pair_frame, projects, participants, memberships, matrix, warnings)

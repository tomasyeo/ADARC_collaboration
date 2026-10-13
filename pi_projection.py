"""Derive PI co-participation counts and source-title evidence in memory."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import pandas as pd

from data_model import CollaborationData


Pair = tuple[str, str]


@dataclass(frozen=True)
class PIProjection:
    names: tuple[str, ...]
    projects_by_pi: dict[str, tuple[str, ...]]
    shared_projects: dict[Pair, tuple[str, ...]]
    matrix: pd.DataFrame


def pair_key(first: str, second: str) -> Pair:
    """Put pair endpoints in the same deterministic order as displayed PIs."""
    first_key = (first.casefold(), first)
    second_key = (second.casefold(), second)
    return (first, second) if first_key <= second_key else (second, first)


def project_pi_pairs(data: CollaborationData) -> PIProjection:
    names = tuple(data.participants.participant)
    projects_by_pi: dict[str, set[str]] = {name: set() for name in names}
    shared: dict[Pair, set[str]] = {}
    for project, rows in data.pairs.groupby("project", sort=False):
        participants = sorted(set(rows.participant), key=lambda name: (name.casefold(), name))
        for name in participants:
            projects_by_pi[name].add(project)
        for first, second in combinations(participants, 2):
            shared.setdefault((first, second), set()).add(project)

    title_key = lambda title: (title.casefold(), title)
    projects = {name: tuple(sorted(titles, key=title_key)) for name, titles in projects_by_pi.items()}
    evidence = {pair: tuple(sorted(titles, key=title_key)) for pair, titles in shared.items()}
    matrix = pd.DataFrame(0, index=names, columns=names, dtype=int)
    matrix.index.name = "PI"
    matrix.columns.name = "PI"
    for name in names:
        matrix.at[name, name] = len(projects[name])
    for (first, second), titles in evidence.items():
        matrix.at[first, second] = len(titles)
        matrix.at[second, first] = len(titles)
    return PIProjection(names, projects, evidence, matrix)

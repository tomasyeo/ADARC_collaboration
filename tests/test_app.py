import tempfile
import unittest
from pathlib import Path

from app import matrix_figure, pi_matrix_figure, valid_selection
from data_model import SourceError, load_data
from network_component import build_graph, graph_payload
from pi_network_component import pi_graph_payload
from pi_projection import pair_key, project_pi_pairs
from streamlit.testing.v1 import AppTest


SOURCE = Path(__file__).resolve().parents[1] / "data_source" / "project_participant.txt"


class SourceAndViewTests(unittest.TestCase):
    def test_retained_pair_can_be_cleared_from_project_page(self):
        data = load_data(SOURCE)
        pair = next(iter(project_pi_pairs(data).shared_projects))
        app = AppTest.from_file(str(SOURCE.parents[1] / "app.py"), default_timeout=10).run()
        app.session_state["semantic_selection"] = ("Pair", *pair)
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox[0].value, ("Pair", *pair))
        app.selectbox[0].set_value(None).run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["semantic_selection"])

    def test_pi_projection_reconciles_with_source(self):
        from collections import defaultdict
        from itertools import combinations

        raw = [line.split("\t") for line in SOURCE.read_text(encoding="utf-8").splitlines()[1:]]
        by_project = defaultdict(set)
        by_pi = defaultdict(set)
        for project, pi in raw:
            by_project[project].add(pi)
            by_pi[pi].add(project)
        expected_pairs = defaultdict(set)
        for project, pis in by_project.items():
            for first, second in combinations(sorted(pis), 2):
                expected_pairs[pair_key(first, second)].add(project)

        data = load_data(SOURCE)
        projection = project_pi_pairs(data)
        self.assertEqual(set(projection.names), set(by_pi))
        self.assertEqual(sum(projection.matrix.at[pi, pi] for pi in projection.names), len(raw))
        self.assertEqual(sum(map(len, projection.shared_projects.values())),
                         sum(len(pis) * (len(pis) - 1) // 2 for pis in by_project.values()))
        self.assertEqual(set(projection.shared_projects), set(expected_pairs))
        for pi in projection.names:
            self.assertEqual(set(projection.projects_by_pi[pi]), by_pi[pi])
            self.assertEqual(projection.matrix.at[pi, pi], len(by_pi[pi]))
        for pair, titles in projection.shared_projects.items():
            self.assertEqual(set(titles), expected_pairs[pair])
            self.assertEqual(projection.matrix.at[pair[0], pair[1]], len(titles))
            self.assertEqual(projection.matrix.at[pair[1], pair[0]], len(titles))

        payload = pi_graph_payload(data, projection, None)
        nodes = [item["data"] for item in payload["elements"] if "source" not in item["data"]]
        edges = [item["data"] for item in payload["elements"] if "source" in item["data"]]
        self.assertEqual(len(nodes), len(projection.names))
        self.assertEqual(len(edges), len(expected_pairs))
        self.assertEqual({(edge["first"], edge["second"]): edge["count"] for edge in edges},
                         {pair: len(titles) for pair, titles in expected_pairs.items()})
        selected = ("Pair", *next(iter(expected_pairs)))
        self.assertTrue(valid_selection(selected, data))
        self.assertIsNotNone(pi_graph_payload(data, projection, selected)["selectedId"])
        pi_matrix_figure(projection, selected).to_plotly_json()

    def test_projection_updates_and_rejects_removed_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text("project\tparticipant\nA\tP1\nA\tP2\nB\tP1\nC\tP3\n",
                            encoding="utf-8")
            data = load_data(path)
            projection = project_pi_pairs(data)
            self.assertEqual(projection.shared_projects, {("P1", "P2"): ("A",)})
            self.assertEqual(projection.matrix.at["P3", "P3"], 1)
            self.assertEqual(projection.matrix.at["P1", "P3"], 0)
            self.assertTrue(valid_selection(("Pair", "P1", "P2"), data))
            self.assertFalse(valid_selection(("Pair", "P1", "P3"), data))

            path.write_text("project\tparticipant\nA\tP1\nB\tP2\nC\tP3\n",
                            encoding="utf-8")
            changed = load_data(path)
            self.assertFalse(valid_selection(("Pair", "P1", "P2"), changed))
            self.assertEqual(project_pi_pairs(changed).shared_projects, {})

    def test_source_reconciles_with_both_views(self):
        raw_lines = SOURCE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(raw_lines[0], "project\tparticipant")
        raw_pairs = {tuple(line.split("\t")) for line in raw_lines[1:]}
        self.assertEqual(len(raw_pairs), len(raw_lines) - 1)

        data = load_data(SOURCE)
        matrix_pairs = {
            (project, pi)
            for project in data.matrix.index
            for pi in data.matrix.columns
            if data.matrix.at[project, pi] == 1
        }
        graph = build_graph(data)
        graph_pairs = {
            (
                graph.nodes[left]["label"] if graph.nodes[left]["kind"] == "Project" else graph.nodes[right]["label"],
                graph.nodes[right]["label"] if graph.nodes[right]["kind"] == "PI" else graph.nodes[left]["label"],
            )
            for left, right in graph.edges
        }
        self.assertEqual(raw_pairs, matrix_pairs)
        self.assertEqual(raw_pairs, graph_pairs)
        self.assertEqual(len(data.projects), len({project for project, _ in raw_pairs}))
        self.assertEqual(len(data.participants), len({pi for _, pi in raw_pairs}))
        self.assertEqual(graph.number_of_nodes(), len(data.projects) + len(data.participants))
        self.assertEqual(graph.number_of_edges(), len(raw_pairs))

        selected = ("Project", data.projects.project.iloc[0])
        matrix_figure(data, selected).to_plotly_json()
        payload = graph_payload(data, selected)
        nodes = [element["data"] for element in payload["elements"] if "source" not in element["data"]]
        edges = [element["data"] for element in payload["elements"] if "source" in element["data"]]
        nodes_by_id = {node["id"]: node for node in nodes}
        payload_pairs = {
            (nodes_by_id[edge["source"]]["label"], nodes_by_id[edge["target"]]["label"])
            for edge in edges
        }
        self.assertEqual({node["id"] for node in nodes}, set(graph.nodes))
        self.assertEqual(len(edges), len(raw_pairs))
        self.assertEqual(payload_pairs, raw_pairs)
        self.assertEqual(set(payload["positions"]), set(graph.nodes))
        selected_node = next(node for node in graph if graph.nodes[node]["label"] == selected[1])
        self.assertEqual(payload["selectedId"], selected_node)

    def test_row_order_and_source_update(self):
        lines = SOURCE.read_text(encoding="utf-8").splitlines()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text("\n".join([lines[0], *reversed(lines[1:])]) + "\n", encoding="utf-8")
            reordered = load_data(path)
            original = load_data(SOURCE)
            self.assertEqual(original.projects.to_dict("records"), reordered.projects.to_dict("records"))
            self.assertEqual(original.participants.to_dict("records"), reordered.participants.to_dict("records"))

            path.write_text("\n".join([lines[0], *lines[1:], "New study\tNew PI"]) + "\n", encoding="utf-8")
            changed = load_data(path)
            self.assertEqual(len(changed.projects), len(original.projects) + 1)
            self.assertEqual(len(changed.participants), len(original.participants) + 1)
            self.assertEqual(len(changed.pairs), len(original.pairs) + 1)
            self.assertEqual(changed.matrix.at["New study", "New PI"], 1)
            project_id = changed.projects.set_index("project").at["New study", "project_id"]
            self.assertTrue(build_graph(changed).has_edge(f"project:{project_id}", "participant:NewPI"))

    def test_invalid_rows_report_source_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            for body, message in (
                ("A\tB\nA\tB\n", "Line 3: duplicate pair"),
                ("A\t\n", "Line 2: project and participant"),
                (" A\tB\n", "Line 2: remove leading"),
                ("A\tB\textra\n", "Line 2: expected exactly two"),
            ):
                path.write_text("project\tparticipant\n" + body, encoding="utf-8")
                with self.subTest(body=body), self.assertRaisesRegex(SourceError, message):
                    load_data(path)


if __name__ == "__main__":
    unittest.main()

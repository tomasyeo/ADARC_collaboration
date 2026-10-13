import tempfile
import unittest
from pathlib import Path

from app import matrix_figure
from data_model import SourceError, load_data
from network_component import build_graph, graph_payload


SOURCE = Path(__file__).resolve().parents[1] / "data_source" / "project_participant.txt"


class SourceAndViewTests(unittest.TestCase):
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

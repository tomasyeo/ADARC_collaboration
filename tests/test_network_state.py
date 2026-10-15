import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import frontend_assets


class NetworkStateTests(unittest.TestCase):
    def test_project_selection_and_clear_restore_the_same_event_view(self):
        view = {
            "positions": {"participant:A": {"x": 123, "y": 456}},
            "zoom": 1.2, "pan": {"x": 50, "y": 60},
            "revealFellowPis": True, "focused": True,
        }
        state = {
            "project_graph_view": {"positions": {}},
            "cytoscape_network": {"selected": {"kind": "PI", "name": "A", "view": view}},
        }
        with patch.object(app.st, "session_state", state):
            app.on_graph_selected()
            self.assertEqual(state["pending_selection"], ("PI", "A"))
            self.assertEqual(state["project_graph_view"], view)
            cleared = {**view, "focused": False, "selectedId": None}
            state["cytoscape_network"]["selected"] = {"kind": "Clear", "view": cleared}
            app.on_graph_selected()
            self.assertIsNone(state["pending_selection"])
            self.assertEqual(state["project_graph_view"], cleared)

    def test_asset_changes_refresh_registration_and_unchanged_assets_reuse_it(self):
        frontend_assets._register.cache_clear()
        self.addCleanup(frontend_assets._register.cache_clear)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dist").mkdir()
            css = root / "network.css"
            js = root / "dist" / "network.js"
            css.write_text("old style")
            js.write_text("old bundle")
            with patch.object(frontend_assets.st.components.v2, "component") as register:
                first = frontend_assets.register_frontend("test", "html", root, "network.js")
                again = frontend_assets.register_frontend("test", "html", root, "network.js")
                self.assertIs(first, again)
                self.assertEqual(register.call_count, 1)
                js.write_text("new bundle")
                frontend_assets.register_frontend("test", "html", root, "network.js")
                css.write_text("new style")
                frontend_assets.register_frontend("test", "html", root, "network.js")
                frontend_assets.register_frontend("test", "new html", root, "network.js")
                calls = register.call_args_list
                self.assertEqual(len(calls), 4)
                self.assertEqual(len({call.kwargs["name"] for call in calls}), 4)
                self.assertEqual(calls[-1].kwargs["js"], "new bundle")
                self.assertEqual(calls[-1].kwargs["css"], "new style")

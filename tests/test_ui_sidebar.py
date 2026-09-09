"""
Unit and integration tests for SidebarView component.
SRS References: §8.1.1, §8.1.4, §8.1.5 item 1, §8.1.13, §10.7, §11.4
Implementation Plan: TASK-P3.4
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock

import customtkinter

from src.core.service import SystemHealthResponse
from src.ui.components.sidebar import (
    COLOR_STATUS_OFFLINE,
    COLOR_STATUS_ONLINE,
    COLOR_STATUS_WARNING,
    SIDEBAR_WIDTH,
    SidebarView,
)
from src.utils.config import ConfigManager, SessionSnapshot


class TestSidebarView(unittest.TestCase):
    """Test suite for SidebarView navigation and control component."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config.json")
        self.config_mgr = ConfigManager(self.config_path)

        self.root = customtkinter.CTk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_sidebar_fixed_width(self):
        """Verify sidebar enforces fixed 280px width (§8.1.4, §8.1.5 item 1)."""
        sidebar = SidebarView(self.root, service=None, config=self.config_mgr)
        sidebar.pack(fill="y", side="left")
        self.assertEqual(sidebar.cget("width"), SIDEBAR_WIDTH)
        self.assertEqual(sidebar.cget("width"), 280)

    def test_ollama_status_indicators(self):
        """Verify vector dot and text for online and offline states (§8.1.5 item 1)."""
        sidebar = SidebarView(self.root, service=None, config=self.config_mgr)

        # 1. Test Online State
        online_health = SystemHealthResponse(
            status="healthy",
            ollama_status="online",
            model_loaded="phi4-mini",
            embedding_model="bge-small-en-v1.5",
            embedding_file_status="available",
            embedding_index_count=139,
            dataset_last_modified="2026-09-09T12:00:00",
            last_embed_timestamp="2026-09-09T12:00:00",
            ram_usage_mb=75.0,
            num_ctx=2048,
        )
        sidebar.update_health(online_health)

        dot_fill = sidebar._dot_canvas.itemcget(sidebar._status_dot, "fill")
        self.assertEqual(dot_fill, COLOR_STATUS_ONLINE)
        self.assertIn("Online", sidebar._ollama_label.cget("text"))
        self.assertEqual(sidebar._index_label.cget("text"), "✓ 139 Catalog Products Active")

        # 2. Test Offline State
        offline_health = SystemHealthResponse(
            status="offline",
            ollama_status="offline",
            model_loaded="phi4-mini",
            embedding_model="bge-small-en-v1.5",
            embedding_file_status="available",
            embedding_index_count=139,
            dataset_last_modified="2026-09-09T12:00:00",
            last_embed_timestamp="2026-09-09T12:00:00",
            ram_usage_mb=75.0,
            num_ctx=2048,
        )
        sidebar.update_health(offline_health)

        dot_fill_offline = sidebar._dot_canvas.itemcget(sidebar._status_dot, "fill")
        self.assertEqual(dot_fill_offline, COLOR_STATUS_OFFLINE)
        self.assertIn("OFFLINE", sidebar._ollama_label.cget("text"))

    def test_theme_switcher_persistence(self):
        """Verify dynamic appearance mode toggle and config persistence (§8.1.13)."""
        sidebar = SidebarView(self.root, service=None, config=self.config_mgr)

        # Toggle to Light
        sidebar._on_theme_change("Light")
        self.assertEqual(customtkinter.get_appearance_mode(), "Light")
        self.assertEqual(self.config_mgr.get("appearance_mode"), "light")

        # Toggle to Dark
        sidebar._on_theme_change("Dark")
        self.assertEqual(customtkinter.get_appearance_mode(), "Dark")
        self.assertEqual(self.config_mgr.get("appearance_mode"), "dark")

    def test_session_history_fifo_and_clicks(self):
        """Verify FIFO session history capped at 20 and click callback dispatch (§8.1.5 item 1)."""
        sidebar = SidebarView(self.root, service=None, config=self.config_mgr)

        restored_sessions = []
        sidebar.set_on_session_restore(lambda snap: restored_sessions.append(snap))

        # Add 25 sessions
        for i in range(25):
            snap = SessionSnapshot(
                query_id=f"q_{i}",
                timestamp=f"2026-09-09T14:{i:02d}:00",
                requirement_text=f"Customer requirement number {i}",
                recommendations=[],
            )
            sidebar.add_session(snap)

        # Must be capped at 20
        self.assertEqual(len(sidebar._sessions), 20)
        # Newest must be at index 0
        self.assertEqual(sidebar._sessions[0].query_id, "q_24")
        # Oldest retained must be q_5
        self.assertEqual(sidebar._sessions[-1].query_id, "q_5")

        # Test click dispatch
        sidebar._handle_session_click(sidebar._sessions[0])
        self.assertEqual(len(restored_sessions), 1)
        self.assertEqual(restored_sessions[0].query_id, "q_24")

    def test_ram_meter_thresholds(self):
        """Verify RAM indicator text and progress colors at different memory levels."""
        sidebar = SidebarView(self.root, service=None, config=self.config_mgr)

        # Safe (< 500 MB)
        sidebar._update_ram_meter(220.0)
        self.assertIn("220 MB (Safe)", sidebar._ram_label.cget("text"))
        self.assertEqual(sidebar._ram_bar.cget("progress_color"), COLOR_STATUS_ONLINE)

        # Moderate (500 - 1000 MB)
        sidebar._update_ram_meter(750.0)
        self.assertIn("750 MB (Moderate)", sidebar._ram_label.cget("text"))
        self.assertEqual(sidebar._ram_bar.cget("progress_color"), COLOR_STATUS_WARNING)

        # High (> 1000 MB)
        sidebar._update_ram_meter(1250.0)
        self.assertIn("1250 MB (High)", sidebar._ram_label.cget("text"))
        self.assertEqual(sidebar._ram_bar.cget("progress_color"), COLOR_STATUS_OFFLINE)

    def test_utility_action_callbacks(self):
        """Verify utility actions dispatch registered callbacks."""
        sidebar = SidebarView(self.root, service=None, config=self.config_mgr)

        actions_fired = []
        sidebar.set_on_new_query(lambda: actions_fired.append("new_query"))
        sidebar.set_on_clear_workspace(lambda: actions_fired.append("clear"))
        sidebar.set_on_reindex(lambda: actions_fired.append("reindex"))

        sidebar._handle_new_query()
        sidebar._handle_clear_workspace()
        sidebar._handle_reindex()

        self.assertEqual(actions_fired, ["new_query", "clear", "reindex"])


if __name__ == "__main__":
    unittest.main()

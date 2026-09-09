"""
Unit and integration tests for PRISMApp and entry point lifecycle.
SRS References: §8.1.1, §8.1.6, §9.8, §9.9, §10.6, §10.7
Implementation Plan: TASK-P3.3
"""

import os
import queue
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import customtkinter

from src.ui.app import (
    COLOR_BG_CANVAS,
    COLOR_BG_SIDEBAR,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    MIN_HEIGHT,
    MIN_WIDTH,
    PRISMApp,
    WINDOW_TITLE,
)
from src.ui.splash import SplashPreloader
from src.utils.config import ConfigManager
from src.utils.system_info import release_single_instance, verify_single_instance


class TestPRISMApp(unittest.TestCase):
    """Test suite for PRISMApp root window and lifecycle."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config.json")
        self.config_mgr = ConfigManager(self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()
        release_single_instance()

    def test_window_title_and_minsize(self):
        """Verify window title and minimum size enforcement (§8.1.1, §8.1.6)."""
        app = PRISMApp(service=None, config=self.config_mgr)
        app.withdraw()

        self.assertEqual(app.title(), WINDOW_TITLE)
        self.assertEqual(app._min_width, MIN_WIDTH)
        self.assertEqual(app._min_height, MIN_HEIGHT)

        app.destroy()

    def test_default_geometry_and_layout(self):
        """Verify layout dimensions and default geometry centering."""
        app = PRISMApp(service=None, config=self.config_mgr)
        app.withdraw()

        # Check frames exist and configured
        self.assertIsNotNone(app.sidebar_frame)
        self.assertIsNotNone(app.main_canvas_frame)
        self.assertEqual(app.sidebar_frame.cget("width"), 280)

        # Check geometry starts with width >= 1024, height >= 640
        self.assertGreaterEqual(app._current_width, MIN_WIDTH)
        self.assertGreaterEqual(app._current_height, MIN_HEIGHT)

        app.destroy()

    def test_offscreen_boundary_self_healing(self):
        """Verify §10.6 disconnected monitor handling (off-screen coordinates re-centered)."""
        # Set explicitly off-screen coordinates in config (e.g. disconnected 2nd monitor at x=3500)
        self.config_mgr.set("window_geometry", [1280, 820, 4500, 2500, False])

        app = PRISMApp(service=None, config=self.config_mgr)
        app.withdraw()

        # Should be self-healed to on-screen coordinates
        screen_w = app.winfo_screenwidth()
        screen_h = app.winfo_screenheight()

        valid_x, valid_y, is_valid = app._validate_window_position(4500, 2500, 1280, 820)
        self.assertFalse(is_valid)  # Detected as offscreen
        self.assertEqual(valid_x, max(0, (screen_w - 1280) // 2))
        self.assertEqual(valid_y, max(0, (screen_h - 820) // 2))

        app.destroy()

    def test_queue_polling_drains_messages(self):
        """Verify that _process_queue drains ui_queue and routes properly (§9.8, §9.10)."""
        app = PRISMApp(service=None, config=self.config_mgr)
        app.withdraw()

        received_steps = []
        app._on_status_step = lambda step, label: received_steps.append((step, label))

        # Put messages in queue
        app.ui_queue.put({"type": "STATUS_STEP", "step": 1, "label": "Testing step 1"})
        app.ui_queue.put({"type": "STATUS_STEP", "step": 2, "label": "Testing step 2"})

        # Run process queue
        app._process_queue()

        self.assertEqual(len(received_steps), 2)
        self.assertEqual(received_steps[0], (1, "Testing step 1"))
        self.assertEqual(received_steps[1], (2, "Testing step 2"))
        self.assertTrue(app.ui_queue.empty())

        app.destroy()

    def test_graceful_shutdown_saves_geometry(self):
        """Verify that _on_close saves window geometry to ConfigManager (§8.1.6, §9.8)."""
        app = PRISMApp(service=None, config=self.config_mgr)
        app.withdraw()

        mock_worker = MagicMock()
        mock_worker.is_running = True
        app._worker = mock_worker

        # Trigger graceful shutdown
        app._on_close()

        # Check worker cancel called
        mock_worker.cancel.assert_called_once()

        # Check geometry was written to config
        saved_geom = self.config_mgr.get("window_geometry")
        self.assertIsInstance(saved_geom, list)
        self.assertEqual(len(saved_geom), 5)
        self.assertGreaterEqual(saved_geom[0], MIN_WIDTH)
        self.assertGreaterEqual(saved_geom[1], MIN_HEIGHT)

    def test_single_instance_guard(self):
        """Verify Windows named mutex single-instance guard (§10.7, INT-14)."""
        release_single_instance()
        # First verification succeeds
        first = verify_single_instance("Global\\TestPrismMutex_123")
        self.assertTrue(first)

        # Second call in same process returns True because handle held
        same_process = verify_single_instance("Global\\TestPrismMutex_123")
        self.assertTrue(same_process)

        release_single_instance()

    def test_single_root_splash_transition(self):
        """Verify single-root architecture prevents Tkinter deadlock."""
        app = PRISMApp(service=None, config=self.config_mgr)
        app.withdraw()

        splash = SplashPreloader(master=app)
        self.assertIsNotNone(splash)

        transitioned = []

        def on_done():
            transitioned.append(True)
            app.deiconify()
            app.after(50, lambda: (app.quit(), app.destroy()))

        # Finish splash with callback
        splash.finish(callback=on_done)
        # Run mainloop for the 300ms fade to finish and trigger on_done
        app.mainloop()

        self.assertTrue(len(transitioned) > 0 and transitioned[0])


if __name__ == "__main__":
    unittest.main()

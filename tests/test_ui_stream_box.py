"""
Unit and integration tests for TokenStreamTerminal component.
SRS References: §8.1.5 item 3, §8.1.10
Implementation Plan: TASK-P4.1
"""

import unittest
from unittest.mock import patch

import customtkinter

from src.ui.components.stream_box import (
    COLOR_BRAND_ACCENT,
    COLOR_STATUS_ERROR,
    COLOR_STATUS_SUCCESS,
    COLOR_TEXT_MUTED,
    DEFAULT_PHASES,
    TokenStreamTerminal,
)


class TestTokenStreamTerminal(unittest.TestCase):
    """Test suite for TokenStreamTerminal component."""

    def setUp(self):
        self.root = customtkinter.CTk()
        self.root.withdraw()
        self.terminal = TokenStreamTerminal(self.root)
        self.terminal.pack()

    def tearDown(self):
        try:
            self.terminal.destroy()
            self.root.destroy()
        except Exception:
            pass

    def test_initial_reset_state(self):
        """Verify initial stepper is pending, textbox empty, progress bar zero."""
        for step_idx in range(1, 4):
            lbl_text = self.terminal._step_labels[step_idx].cget("text")
            self.assertTrue(lbl_text.startswith("[·]"))
            self.assertEqual(self.terminal._step_labels[step_idx].cget("text_color"), COLOR_TEXT_MUTED)

        self.assertEqual(self.terminal.get_text(), "")
        self.assertEqual(self.terminal._progress_bar.get(), 0.0)

    def test_stepper_phase_transitions(self):
        """Verify phase status transitions: active, completed, error, and auto-completing prior phases."""
        # 1. Activate Phase 1
        self.terminal.set_step(1, "active")
        self.assertTrue(self.terminal._step_labels[1].cget("text").startswith("[⟳]"))
        self.assertEqual(self.terminal._step_labels[1].cget("text_color"), COLOR_BRAND_ACCENT)

        # 2. Activate Phase 2 -> Phase 1 should auto-complete
        self.terminal.set_step(2, "active")
        self.assertTrue(self.terminal._step_labels[1].cget("text").startswith("[✓]"))
        self.assertEqual(self.terminal._step_labels[1].cget("text_color"), COLOR_STATUS_SUCCESS)
        self.assertTrue(self.terminal._step_labels[2].cget("text").startswith("[⟳]"))

        # 3. Complete Phase 2 and activate Phase 3
        self.terminal.set_step(3, "active")
        self.assertTrue(self.terminal._step_labels[2].cget("text").startswith("[✓]"))
        self.assertTrue(self.terminal._step_labels[3].cget("text").startswith("[⟳]"))
        self.assertTrue(self.terminal._is_streaming)

        # 4. Complete Phase 3
        self.terminal.set_step(3, "completed")
        self.assertTrue(self.terminal._step_labels[3].cget("text").startswith("[✓]"))
        self.assertEqual(self.terminal._step_labels[3].cget("text_color"), COLOR_STATUS_SUCCESS)
        self.assertFalse(self.terminal._is_streaming)

        # 5. Error status
        self.terminal.set_step(2, "error", "Custom error message")
        self.assertTrue(self.terminal._step_labels[2].cget("text").startswith("[✕]"))
        self.assertEqual(self.terminal._step_labels[2].cget("text_color"), COLOR_STATUS_ERROR)

    def test_token_streaming_and_accumulation(self):
        """Verify tokens append one by one and accumulate accurately."""
        tokens = ["Based ", "on ", "your ", "RFP ", "requirements..."]
        for t in tokens:
            self.terminal.append_token(t)

        self.assertEqual(self.terminal.get_text(), "Based on your RFP requirements...")

        # Verify raw text in textbox contains the accumulated string
        raw_text = self.terminal._textbox.get("1.0", "end-1c")
        self.assertTrue("Based on your RFP requirements..." in raw_text)

    def test_caret_blinking_toggle(self):
        """Verify blinking caret toggle updates display and schedules next cycle."""
        self.terminal.append_token("Streaming content")
        self.assertTrue(self.terminal._is_streaming)
        self.assertIsNotNone(self.terminal._caret_timer)

        # Force caret toggle
        self.terminal._toggle_caret()
        raw_text = self.terminal._textbox.get("1.0", "end-1c")
        self.assertTrue(self.terminal._is_streaming)

        # Stop streaming removes caret
        self.terminal._stop_streaming()
        self.assertFalse(self.terminal._is_streaming)
        self.assertIsNone(self.terminal._caret_timer)

    def test_progress_bar_reduced_motion(self):
        """Verify progress bar respects reduced-motion accessibility preference (§8.1.10)."""
        with patch("src.ui.components.stream_box.check_reduced_motion", return_value=True):
            self.terminal.set_step(1, "active")
            # In reduced motion mode, mode remains determinate and sets static progress value
            self.assertEqual(self.terminal._progress_bar.cget("mode"), "determinate")
            self.assertGreater(self.terminal._progress_bar.get(), 0.0)

    def test_show_hide_reset(self):
        """Verify show, hide, and reset behaviors."""
        self.terminal.append_token("Some tokens")
        self.terminal.set_step(1, "completed")
        self.terminal.set_step(2, "active")

        # Hide
        self.terminal.hide()
        self.assertEqual(self.terminal.winfo_manager(), "")

        # Show
        self.terminal.show()
        self.assertEqual(self.terminal.winfo_manager(), "pack")

        # Reset
        self.terminal.reset()
        self.assertEqual(self.terminal.get_text(), "")
        self.assertEqual(self.terminal._step_statuses[1], "pending")
        self.assertEqual(self.terminal._step_statuses[2], "pending")


if __name__ == "__main__":
    unittest.main()

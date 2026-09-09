"""
Unit and integration tests for RequirementInputPanel component.
SRS References: §6.9, §8.1.5 item 2, §10.1, §10.7, §FR-1, §FR-1a, §FR-14
Implementation Plan: TASK-P3.5
"""

import unittest
from unittest.mock import MagicMock, patch

import customtkinter

from src.ui.components.input_panel import (
    COLOR_STATUS_ERROR,
    COLOR_STATUS_ONLINE,
    COLOR_STATUS_WARNING,
    PLACEHOLDER_TEXT,
    RequirementInputPanel,
)


class TestRequirementInputPanel(unittest.TestCase):
    """Test suite for RequirementInputPanel component."""

    def setUp(self):
        self.root = customtkinter.CTk()
        self.root.withdraw()
        self.panel = RequirementInputPanel(self.root)
        self.panel.pack()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_placeholder_initial_state(self):
        """Verify placeholder text is rendered initially and get_text returns empty."""
        self.assertTrue(self.panel._has_placeholder)
        self.assertEqual(self.panel.get_text(), "")
        raw_text = self.panel._textbox.get("1.0", "end-1c").strip()
        self.assertEqual(raw_text, PLACEHOLDER_TEXT)

    def test_set_text_and_get_text(self):
        """Verify programmatic text setting, placeholder dismissal, and text retrieval."""
        sample_text = "Need next-gen firewall with IPS and SSL inspection for 500 users."
        self.panel.set_text(sample_text)

        self.assertFalse(self.panel._has_placeholder)
        self.assertEqual(self.panel.get_text(), sample_text)

        # Clear text resets placeholder
        self.panel.clear()
        self.assertTrue(self.panel._has_placeholder)
        self.assertEqual(self.panel.get_text(), "")

    def test_token_gauge_updates_live(self):
        """Verify live character and token gauge updates and color transitions."""
        # 1. Normal short input (<8000 chars) -> Green
        short_req = "Fortinet FortiGate firewall with enterprise license."
        self.panel.set_text(short_req)
        gauge_text = self.panel._gauge_label.cget("text")
        self.assertIn(f"Characters: {len(short_req)}", gauge_text)
        self.assertIn("Tokens:", gauge_text)
        self.assertEqual(self.panel._gauge_label.cget("text_color"), COLOR_STATUS_ONLINE)

        # 2. Warning input (8000 - 10000 chars) -> Amber
        long_req = "a " * 4100  # ~8200 chars
        self.panel.set_text(long_req)
        self.assertEqual(self.panel._gauge_label.cget("text_color"), COLOR_STATUS_WARNING)

        # 3. Excessive input (>10000 chars) -> Crimson
        too_long_req = "x" * 10500
        self.panel.set_text(too_long_req)
        self.assertEqual(self.panel._gauge_label.cget("text_color"), COLOR_STATUS_ERROR)

    def test_empty_input_validation(self):
        """Verify empty input is rejected without calling analyze callback (NEG-01, NEG-02)."""
        analyzed_payloads = []
        self.panel.set_on_analyze(lambda text: analyzed_payloads.append(text))

        # Attempt to analyze while empty
        self.panel.clear()
        self.panel._handle_analyze_click()

        self.assertEqual(len(analyzed_payloads), 0)
        self.assertIn("enter a customer requirement", self.panel._feedback_label.cget("text"))

    def test_short_input_warning(self):
        """Verify brief input produces advisory warning but proceeds (NEG-03)."""
        analyzed_payloads = []
        self.panel.set_on_analyze(lambda text: analyzed_payloads.append(text))

        # Set 5 characters (< 10 threshold)
        self.panel.set_text("Fire")
        self.panel._handle_analyze_click()

        self.assertEqual(len(analyzed_payloads), 1)
        self.assertEqual(analyzed_payloads[0], "Fire")
        self.assertIn("very brief", self.panel._feedback_label.cget("text"))

    def test_analyzing_state_toggles_buttons(self):
        """Verify set_analyzing toggles Analyze vs Cancel buttons and disables input (§10.7)."""
        self.panel.set_text("Valid technical requirement for PAM.")

        # Enter analyzing state
        self.panel.set_analyzing(True)
        self.assertTrue(self.panel._is_analyzing)
        self.assertEqual(self.panel._textbox.cget("state"), "disabled")
        self.assertEqual(self.panel._load_file_btn.cget("state"), "disabled")

        # Cancel button is visible (packed), analyze button is hidden
        self.assertEqual(self.panel._cancel_btn.winfo_manager(), "pack")
        self.assertEqual(self.panel._analyze_btn.winfo_manager(), "")

        # Exit analyzing state
        self.panel.set_analyzing(False)
        self.assertFalse(self.panel._is_analyzing)
        self.assertEqual(self.panel._textbox.cget("state"), "normal")
        self.assertEqual(self.panel._load_file_btn.cget("state"), "normal")
        self.assertEqual(self.panel._analyze_btn.winfo_manager(), "pack")
        self.assertEqual(self.panel._cancel_btn.winfo_manager(), "")

    def test_cancel_button_dispatches_callback(self):
        """Verify clicking cancel button dispatches cancel callback."""
        cancelled = []
        self.panel.set_on_cancel(lambda: cancelled.append(True))

        self.panel.set_analyzing(True)
        self.panel._handle_cancel_click()

        self.assertEqual(len(cancelled), 1)
        self.assertTrue(cancelled[0])

    @patch("tkinter.filedialog.askopenfilename")
    def test_file_loader_picker_dispatch(self, mock_askopen):
        """Verify file loader button triggers native file picker with filter and callback."""
        mock_askopen.return_value = "C:/docs/sample_rfp.pdf"

        picked_files = []
        self.panel.set_on_file_load(lambda path: picked_files.append(path))

        self.panel._on_load_file_clicked()

        mock_askopen.assert_called_once()
        self.assertEqual(picked_files, ["C:/docs/sample_rfp.pdf"])

    def test_keyboard_shortcuts(self):
        """Verify Ctrl+Enter submits, Ctrl+O opens file dialog, and Escape cancels (§6.9)."""
        analyzed = []
        cancelled = []
        files_opened = []

        self.panel.set_on_analyze(lambda text: analyzed.append(text))
        self.panel.set_on_cancel(lambda: cancelled.append(True))
        self.panel.set_on_file_load(lambda path: files_opened.append(path))

        # 1. Test Ctrl+Enter
        self.panel.set_text("Valid test query for PAM solution.")
        ret = self.panel._handle_ctrl_enter(None)
        self.assertEqual(ret, "break")
        self.assertEqual(len(analyzed), 1)

        # 2. Test Escape when analyzing
        self.panel.set_analyzing(True)
        self.panel._handle_escape(None)
        self.assertEqual(len(cancelled), 1)

        # 3. Test Ctrl+O
        with patch("tkinter.filedialog.askopenfilename", return_value="test.docx"):
            self.panel.set_analyzing(False)
            ret_o = self.panel._handle_ctrl_o(None)
            self.assertEqual(ret_o, "break")
            self.assertEqual(len(files_opened), 1)


if __name__ == "__main__":
    unittest.main()

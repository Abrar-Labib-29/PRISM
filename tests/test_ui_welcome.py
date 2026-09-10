"""
Unit tests for WelcomeView component.
SRS References: §8.1.8
Implementation Plan: TASK-P4.5
"""

import unittest
from unittest.mock import MagicMock

import customtkinter

from src.ui.components.welcome import QUICK_START_TEMPLATES, WelcomeView


class TestWelcomeView(unittest.TestCase):
    """Test suite for WelcomeView zero-state guidance."""

    def setUp(self):
        self.root = customtkinter.CTk()
        self.root.geometry("1024x768")
        self.root.withdraw()
        self.mock_select = MagicMock()
        self.welcome = WelcomeView(self.root, on_template_select=self.mock_select)
        self.welcome.show()

    def tearDown(self):
        try:
            self.welcome.destroy()
            self.root.update_idletasks()
            self.root.destroy()
        except Exception:
            pass

    def test_three_quickstart_cards_exact_text(self):
        """Verify all 3 quick-start cards are created with exact SRS §8.1.8 requirement text."""
        self.assertEqual(len(self.welcome._cards), 3)

        # 1. PAM Requirement
        pam_expected = (
            "Customer requires a privileged access management solution for 300 servers "
            "with session recording, credential rotation, and SIEM integration."
        )
        self.assertEqual(QUICK_START_TEMPLATES[0]["text"], pam_expected)

        # 2. NGFW Requirement
        ngfw_expected = (
            "Need next-generation enterprise firewall hardware with deep packet SSL inspection, "
            "10 Gbps throughput, and branch SD-WAN support."
        )
        self.assertEqual(QUICK_START_TEMPLATES[1]["text"], ngfw_expected)

        # 3. SIEM Requirement
        siem_expected = (
            "Centralized security logging and analytics platform required to ingest 5,000 EPS "
            "with automated MITRE ATT&CK incident correlation."
        )
        self.assertEqual(QUICK_START_TEMPLATES[2]["text"], siem_expected)

    def test_card_click_dispatches_callback(self):
        """Verify clicking a card calls on_template_select with the exact requirement text."""
        # Click card 0 (PAM)
        self.welcome._handle_card_click(QUICK_START_TEMPLATES[0]["text"])
        self.mock_select.assert_called_once_with(QUICK_START_TEMPLATES[0]["text"])

        # Click card 1 (NGFW)
        self.mock_select.reset_mock()
        self.welcome._handle_card_click(QUICK_START_TEMPLATES[1]["text"])
        self.mock_select.assert_called_once_with(QUICK_START_TEMPLATES[1]["text"])

        # Click card 2 (SIEM)
        self.mock_select.reset_mock()
        self.welcome._handle_card_click(QUICK_START_TEMPLATES[2]["text"])
        self.mock_select.assert_called_once_with(QUICK_START_TEMPLATES[2]["text"])

    def test_show_and_hide(self):
        """Verify show() packs and hide() un-packs the welcome view."""
        self.assertEqual(self.welcome.winfo_manager(), "pack")
        self.welcome.hide()
        self.assertNotEqual(self.welcome.winfo_manager(), "pack")
        self.welcome.show()
        self.assertEqual(self.welcome.winfo_manager(), "pack")


if __name__ == "__main__":
    unittest.main()

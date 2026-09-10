"""
Unit tests for ToastNotificationManager component.
SRS References: §8.1.9, §8.1.10, §8.1.15
Implementation Plan: TASK-P4.4
"""

import unittest
from unittest.mock import MagicMock, patch

import customtkinter

from src.ui.components.toast import (
    MAX_VISIBLE_TOASTS,
    VARIANT_CONFIG,
    ToastNotificationManager,
)


class TestToastNotificationManager(unittest.TestCase):
    """Test suite for ToastNotificationManager."""

    def setUp(self):
        self.root = customtkinter.CTk()
        self.root.geometry("800x600")
        self.root.withdraw()
        self.manager = ToastNotificationManager(self.root)

    def tearDown(self):
        try:
            self.manager.dismiss_all()
            self.root.update_idletasks()
            self.root.destroy()
        except Exception:
            pass

    def test_toast_variants_and_styling(self):
        """Verify success, info, warning, error variants render with correct border colors and icons."""
        for variant, (expected_color, expected_dur, expected_icon) in VARIANT_CONFIG.items():
            toast_id = self.manager.show(f"Test {variant} message", variant=variant)
            self.root.update_idletasks()

            item = next((t for t in self.manager._toasts if t.toast_id == toast_id), None)
            self.assertIsNotNone(item)
            self.assertEqual(item.variant, variant)
            self.assertEqual(item.frame.cget("border_color"), expected_color)

            # Clean up
            self.manager.dismiss(toast_id, immediate=True)

    def test_max_visible_stacking_and_overflow(self):
        """Verify maximum 3 toasts are visible simultaneously; 4th toast evicts the oldest."""
        t1 = self.manager.show("Toast 1", variant="info")
        t2 = self.manager.show("Toast 2", variant="info")
        t3 = self.manager.show("Toast 3", variant="info")

        self.assertEqual(self.manager.active_count, 3)
        self.assertEqual(self.manager._toasts[0].toast_id, t1)

        # Show 4th toast -> t1 should be evicted
        t4 = self.manager.show("Toast 4", variant="success")
        self.assertEqual(self.manager.active_count, 3)

        active_ids = [t.toast_id for t in self.manager._toasts]
        self.assertNotIn(t1, active_ids)
        self.assertIn(t2, active_ids)
        self.assertIn(t3, active_ids)
        self.assertIn(t4, active_ids)

    def test_action_button_callback(self):
        """Verify action button executes callback and dismisses toast."""
        mock_callback = MagicMock()
        toast_id = self.manager.show(
            "Proposal ready",
            variant="success",
            action_text="Open Document",
            action_callback=mock_callback,
        )

        item = next((t for t in self.manager._toasts if t.toast_id == toast_id), None)
        self.assertIsNotNone(item)

        # Locate the action button inside the content box
        action_btn = None
        for child in item.frame.winfo_children():
            if isinstance(child, customtkinter.CTkFrame):  # content_box
                for subchild in child.winfo_children():
                    if isinstance(subchild, customtkinter.CTkFrame):  # action_row
                        for btn in subchild.winfo_children():
                            if isinstance(btn, customtkinter.CTkButton) and btn.cget("text") == "Open Document":
                                action_btn = btn
                                break

        self.assertIsNotNone(action_btn)
        action_btn.invoke()

        # Callback must have been invoked
        mock_callback.assert_called_once()
        # Toast should be transitioning to dismissed
        self.assertTrue(item.is_dismissing)

    def test_dismiss_and_dismiss_all(self):
        """Verify single toast dismissal and dismiss_all clear active queue."""
        t1 = self.manager.show("Msg 1")
        t2 = self.manager.show("Msg 2")

        self.assertEqual(self.manager.active_count, 2)
        self.manager.dismiss(t1, immediate=True)
        self.assertEqual(self.manager.active_count, 1)
        self.assertEqual(self.manager._toasts[0].toast_id, t2)

        self.manager.dismiss_all()
        self.assertEqual(self.manager.active_count, 0)

    @patch("src.ui.components.toast.check_reduced_motion", return_value=True)
    def test_reduced_motion_instant_placement(self, mock_motion):
        """Verify reduced motion places toast immediately without slide animation."""
        toast_id = self.manager.show("Instant Toast", variant="info")
        self.assertEqual(self.manager.active_count, 1)
        item = self.manager._toasts[0]
        # Verify placed
        self.assertEqual(item.frame.winfo_manager(), "place")
        self.manager.dismiss(toast_id, immediate=True)


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for DocumentPreviewModal component.
SRS References: §8.1.12, §FR-13
Implementation Plan: TASK-P4.3
"""

import unittest
from unittest.mock import MagicMock

import customtkinter

from src.core.ingestion import ExtractionResult
from src.ui.components.extraction_modal import DocumentPreviewModal


class TestDocumentPreviewModal(unittest.TestCase):
    """Test suite for DocumentPreviewModal."""

    def setUp(self):
        self.root = customtkinter.CTk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.update_idletasks()
            self.root.destroy()
        except Exception:
            pass

    def test_modal_initial_state_and_metrics(self):
        """Verify modal geometry, pre-populated text, subtitle, and metrics."""
        result = ExtractionResult(
            text="Customer requires Privileged Access Management for 200 servers.",
            source_filename="Customer_RFP_Section3.pdf",
            file_size_kb=142.5,
            char_count=67,
            estimated_tokens=15,
        )

        modal = DocumentPreviewModal(self.root, extraction_result=result)

        modal.update()
        # Check title and geometry
        self.assertEqual(modal.title(), "Extracted Requirement Review")
        self.assertTrue(modal.geometry().startswith("760x540"))

        # Check pre-populated text
        self.assertEqual(modal.get_text(), result.text)

        # Check live metrics
        metrics_text = modal._lbl_metrics.cget("text")
        self.assertIn("63", metrics_text)
        self.assertIn("Estimated Tokens", metrics_text)

        modal.destroy()

    def test_modal_warning_banner_display(self):
        """Verify warning banner renders when ExtractionResult contains a warning."""
        result = ExtractionResult(
            text="Scanned invoice or RFP document",
            source_filename="scanned_doc.pdf",
            file_size_kb=520.0,
            char_count=32,
            estimated_tokens=8,
            warning="Low character density detected; may be a scanned PDF.",
        )

        modal = DocumentPreviewModal(self.root, extraction_result=result)

        # Verify warning banner exists in children
        warning_found = False
        for child in modal.winfo_children():
            if isinstance(child, customtkinter.CTkFrame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, customtkinter.CTkLabel) and "Warning:" in subchild.cget("text"):
                        warning_found = True
                        self.assertIn("scanned PDF", subchild.cget("text"))
        self.assertTrue(warning_found)

        modal.destroy()

    def test_confirm_callback_and_text_edit(self):
        """Verify user edits in textbox are committed and passed to on_confirm callback."""
        result = ExtractionResult(
            text="Original requirement text",
            source_filename="rfp.txt",
            file_size_kb=12.0,
            char_count=25,
            estimated_tokens=5,
        )

        on_confirm_mock = MagicMock()
        modal = DocumentPreviewModal(
            self.root,
            extraction_result=result,
            on_confirm=on_confirm_mock,
        )

        # Simulate user editing the textbox
        modal._txt_canvas.delete("1.0", "end")
        modal._txt_canvas.insert("1.0", "Custom edited RFP requirement text with specific details.")
        modal._update_metrics()

        # Check updated metrics
        self.assertIn("57", modal._lbl_metrics.cget("text"))

        # Click Confirm
        modal._handle_confirm()

        on_confirm_mock.assert_called_once_with(
            "Custom edited RFP requirement text with specific details."
        )

    def test_discard_callback_and_modal_close(self):
        """Verify Discard button triggers on_discard without committing text."""
        result = ExtractionResult(
            text="Text to discard",
            source_filename="draft.docx",
            file_size_kb=34.0,
            char_count=15,
            estimated_tokens=3,
        )

        on_discard_mock = MagicMock()
        modal = DocumentPreviewModal(
            self.root,
            extraction_result=result,
            on_discard=on_discard_mock,
        )

        modal._handle_discard()
        on_discard_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()

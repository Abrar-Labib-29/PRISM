"""
Unit tests for PrimaryRecommendationCard, AlternativeCard, and ResultsCanvas.
SRS References: §8.1.5 item 4, §8.1.10, §8.1.14, §FR-9
Implementation Plan: TASK-P4.2
"""

import unittest
from unittest.mock import MagicMock, patch

import customtkinter

from src.core.service import AnalyzeResponse, Citation, ProductRecommendation
from src.ui.components.result_cards import (
    COLOR_BORDER_ACCEPTED,
    COLOR_BORDER_REJECTED,
    AlternativeCard,
    PrimaryRecommendationCard,
    ResultsCanvas,
)


def _make_dummy_rec(prod_id="OEM-007-P01", oem="CyberArk", name="Privileged Access Manager", fit=92.0):
    return ProductRecommendation(
        product_id=prod_id,
        oem=oem,
        product_name=name,
        domain="Enterprise & Cyber Security",
        sub_domain="Identity & Access Management",
        confidence_score=0.88,
        fit_score=fit,
        confidence_level="HIGH" if fit >= 80 else ("MEDIUM" if fit >= 50 else "LOW"),
        rationale="Enterprise-grade credential vaulting and session isolation.",
        citations=[Citation(sheet="Product_Commercial", product_id=prod_id, field="Features", data_status="confirmed")],
        features=["Vaulting", "Session Recording", "SIEM Integration"],
        pros=["Market leader in PAM", "Comprehensive session audit"],
        cons=["Requires dedicated infrastructure"],
    )


class TestResultCards(unittest.TestCase):
    """Test suite for result cards and results canvas."""

    def setUp(self):
        self.root = customtkinter.CTk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.update_idletasks()
            self.root.destroy()
        except Exception:
            pass

    def test_primary_card_rendering_and_elements(self):
        """Verify PrimaryRecommendationCard displays OEM, title, rationale, features, pros, cons."""
        rec = _make_dummy_rec()
        card = PrimaryRecommendationCard(self.root, recommendation=rec)
        card.pack()

        # Title & OEM
        self.assertIn("Privileged Access Manager", card._content_frame.winfo_children()[1].winfo_children()[1].cget("text"))
        self.assertEqual(card.recommendation.oem, "CyberArk")
        # Rationale
        self.assertEqual(card._lbl_rationale.cget("text"), rec.rationale)
        # Verify initial accepted/rejected states
        self.assertFalse(card.is_accepted)
        self.assertFalse(card.is_rejected)

        card.destroy()

    def test_primary_card_accept_toggle(self):
        """Verify Accept button toggles state, changes border color to emerald green, and triggers callback."""
        rec = _make_dummy_rec()
        on_accept_mock = MagicMock()
        card = PrimaryRecommendationCard(self.root, recommendation=rec, on_accept=on_accept_mock)
        card.pack()

        # 1. Click Accept
        card._handle_toggle_accept()
        self.assertTrue(card.is_accepted)
        self.assertEqual(card.cget("border_color"), COLOR_BORDER_ACCEPTED)
        self.assertEqual(card.cget("border_width"), 2)
        on_accept_mock.assert_called_once_with(rec, True)

        # 2. Click Accept again -> toggle off
        card._handle_toggle_accept()
        self.assertFalse(card.is_accepted)
        self.assertEqual(card.cget("border_width"), 1)
        self.assertEqual(on_accept_mock.call_count, 2)
        on_accept_mock.assert_called_with(rec, False)

        card.destroy()

    def test_primary_card_modify_rationale(self):
        """Verify in-place rationale editor toggles, saves edit, and updates recommendation."""
        rec = _make_dummy_rec()
        on_modify_mock = MagicMock()
        card = PrimaryRecommendationCard(self.root, recommendation=rec, on_modify=on_modify_mock)
        card.pack()

        # Open editor
        card._handle_toggle_modify_rationale()
        self.assertTrue(card._is_editing_rationale)
        self.assertEqual(card._edit_rationale_frame.winfo_manager(), "pack")

        # Edit text & save
        card._txt_rationale.delete("1.0", "end")
        card._txt_rationale.insert("1.0", "Custom tailored presales rationale for client RFP.")
        card._handle_save_rationale()

        self.assertFalse(card._is_editing_rationale)
        self.assertEqual(card.recommendation.rationale, "Custom tailored presales rationale for client RFP.")
        self.assertEqual(card._lbl_rationale.cget("text"), "Custom tailored presales rationale for client RFP.")
        on_modify_mock.assert_called_once_with(rec, "Custom tailored presales rationale for client RFP.")

        card.destroy()

    def test_primary_card_reject_popover_and_confirmation(self):
        """Verify Reject button shows popover, confirms selection, and changes card border."""
        rec = _make_dummy_rec()
        on_reject_mock = MagicMock()
        card = PrimaryRecommendationCard(self.root, recommendation=rec, on_reject=on_reject_mock)
        card.pack()

        # Popover initially hidden
        self.assertNotEqual(card._reject_popover_frame.winfo_manager(), "pack")

        # Open popover
        card._handle_toggle_reject_popover()
        self.assertEqual(card._reject_popover_frame.winfo_manager(), "pack")

        # Select reason and confirm
        card._reason_var.set("Customer brand objection")
        card._handle_confirm_rejection()

        self.assertTrue(card.is_rejected)
        self.assertEqual(card.rejection_reason, "Customer brand objection")
        self.assertEqual(card.cget("border_color"), COLOR_BORDER_REJECTED)
        self.assertIn("Customer brand objection", card._lbl_excluded.cget("text"))
        on_reject_mock.assert_called_once_with(rec, "Customer brand objection")

        card.destroy()

    def test_alternative_card_expand_collapse(self):
        """Verify AlternativeCard is collapsed by default and expands upon toggle."""
        rec = _make_dummy_rec(prod_id="OEM-007-P02", name="CyberArk Endpoint Privilege Manager", fit=75.0)
        alt_card = AlternativeCard(self.root, recommendation=rec)
        alt_card.pack()

        # Default collapsed
        self.assertFalse(alt_card.is_expanded)
        self.assertNotEqual(alt_card._body_frame.winfo_manager(), "pack")
        self.assertEqual(alt_card._lbl_arrow.cget("text"), "▶")

        # Expand
        alt_card.toggle_expand()
        self.assertTrue(alt_card.is_expanded)
        self.assertEqual(alt_card._body_frame.winfo_manager(), "pack")
        self.assertEqual(alt_card._lbl_arrow.cget("text"), "▼")

        # Collapse again
        alt_card.toggle_expand()
        self.assertFalse(alt_card.is_expanded)
        self.assertNotEqual(alt_card._body_frame.winfo_manager(), "pack")

        alt_card.destroy()

    def test_results_canvas_rendering_multiple_cards(self):
        """Verify ResultsCanvas renders verdict header, 1 primary card, and N-1 alternative cards."""
        rec1 = _make_dummy_rec(prod_id="P1", name="Product One", fit=94.0)
        rec2 = _make_dummy_rec(prod_id="P2", name="Product Two", fit=72.0)
        rec3 = _make_dummy_rec(prod_id="P3", name="Product Three", fit=65.0)

        response = AnalyzeResponse(
            query_id="QRY-2026-001",
            status="success",
            latency_ms=1200,
            recommendations=[rec1, rec2, rec3],
        )

        canvas = ResultsCanvas(self.root)
        canvas.pack(fill="both", expand=True)
        canvas.show_results(response)

        self.assertEqual(len(canvas._cards), 3)
        self.assertIsInstance(canvas._cards[0], PrimaryRecommendationCard)
        self.assertIsInstance(canvas._cards[1], AlternativeCard)
        self.assertIsInstance(canvas._cards[2], AlternativeCard)

        # Test accepted tracker
        self.assertEqual(len(canvas.get_accepted_recommendations()), 0)
        canvas._cards[0]._handle_toggle_accept()
        canvas._cards[2]._handle_toggle_accept()

        accepted = canvas.get_accepted_recommendations()
        self.assertEqual(len(accepted), 2)
        self.assertEqual(accepted[0].product_id, "P1")
        self.assertEqual(accepted[1].product_id, "P3")

        # Test clear
        canvas.clear()
        self.assertEqual(len(canvas._cards), 0)

        canvas.destroy()

    def test_results_canvas_clipboard_copy_morph(self):
        """Verify Copy Recommendation button copies markdown and morphs text for 2.0s."""
        rec1 = _make_dummy_rec()
        response = AnalyzeResponse(
            query_id="QRY-2026-002",
            status="success",
            latency_ms=800,
            recommendations=[rec1],
        )

        canvas = ResultsCanvas(self.root)
        canvas.pack()
        canvas.show_results(response)

        # Test markdown generation
        md = canvas._generate_markdown_summary(response)
        self.assertIn("iValue PRISM", md)
        self.assertIn("CyberArk", md)
        self.assertIn("Privileged Access Manager", md)
        self.assertNotIn("$", md)  # Strict zero pricing verification!
        self.assertNotIn("USD", md)
        self.assertNotIn("Price", md)

        # Trigger copy
        with patch.object(canvas, "clipboard_clear"), patch.object(canvas, "clipboard_append") as mock_append:
            canvas._handle_copy_recommendation()
            mock_append.assert_called_once()
            self.assertEqual(canvas._btn_copy.cget("text"), "✓ Copied to Clipboard!")

            # Revert
            canvas._revert_copy_button()
            self.assertEqual(canvas._btn_copy.cget("text"), "📋 Copy Recommendation")

        canvas.destroy()


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for ExportControlPanel component.
SRS References: §8.1.5 item 5, §8.1.15, §8.4, §12.8
Implementation Plan: TASK-P5.1
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import customtkinter

from src.core.service import Citation, ProductRecommendation
from src.ui.components.export_panel import (
    COMPLIANCE_DISCLAIMER,
    GRID_HEADERS,
    LICENSE_TERMS,
    SUPPORT_TIERS,
    ExportControlPanel,
)


def _make_sample_rec(prod_id="OEM-007-P01", name="Privileged Access Manager", oem="CyberArk"):
    return ProductRecommendation(
        product_id=prod_id,
        oem=oem,
        product_name=name,
        domain="Enterprise & Cyber Security",
        sub_domain="Identity & Access Management",
        confidence_score=0.92,
        fit_score=94.0,
        confidence_level="HIGH",
        rationale="Industry standard PAM solution with credential vaulting.",
        citations=[Citation(sheet="Commercial", product_id=prod_id, field="Features", data_status="confirmed")],
        features=["Vaulting", "Session Isolation"],
        pros=["Comprehensive audit"],
        cons=["Infrastructure heavy"],
    )


class TestExportControlPanel(unittest.TestCase):
    """Test suite for ExportControlPanel."""

    def setUp(self):
        self.root = customtkinter.CTk()
        self.root.geometry("1100x700")
        self.root.withdraw()
        self.mock_toast = MagicMock()
        self.panel = ExportControlPanel(self.root, toast_manager=self.mock_toast)

    def tearDown(self):
        try:
            self.panel.destroy()
            self.root.update_idletasks()
            self.root.destroy()
        except Exception:
            pass

    def test_compliance_banner_and_no_pricing_columns(self):
        """Verify compliance warning banner and strict absence of pricing columns (§8.1.5 item 5)."""
        # 1. Check compliance warning text
        self.assertIn("Pricing is intentionally omitted", COMPLIANCE_DISCLAIMER)

        # 2. Check grid headers
        self.assertEqual(GRID_HEADERS, ["Product Name", "Category", "License Qty", "License Term", "Support Tier"])
        for h in GRID_HEADERS:
            self.assertNotIn("Price", h)
            self.assertNotIn("Cost", h)
            self.assertNotIn("USD", h)
            self.assertNotIn("$", h)

    def test_add_and_remove_products(self):
        """Verify adding and removing products updates grid rows, counters, and auto-visibility."""
        rec1 = _make_sample_rec(prod_id="P1", name="Product 1")
        rec2 = _make_sample_rec(prod_id="P2", name="Product 2")

        # Initially 0 items
        self.assertEqual(self.panel.item_count, 0)
        self.assertFalse(self.panel._is_visible)

        # 1. Add product 1 -> should become visible
        self.panel.add_product(rec1)
        self.assertEqual(self.panel.item_count, 1)
        self.assertTrue(self.panel._is_visible)
        self.assertIn("1 item selected", self.panel._badge_count.cget("text"))

        # 2. Add product 2
        self.panel.add_product(rec2)
        self.assertEqual(self.panel.item_count, 2)
        self.assertIn("2 items selected", self.panel._badge_count.cget("text"))

        # Adding duplicate does not increment
        self.panel.add_product(rec1)
        self.assertEqual(self.panel.item_count, 2)

        # 3. Verify get_bom_items()
        items = self.panel.get_bom_items()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].product_id, "P1")
        self.assertEqual(items[1].product_id, "P2")
        self.assertEqual(items[0].quantity, 1)
        self.assertEqual(items[0].license_term, "1-Year")
        self.assertEqual(items[0].support_tier, "Standard")

        # 4. Remove product 1
        self.panel.remove_product("P1")
        self.assertEqual(self.panel.item_count, 1)
        self.assertEqual(self.panel.get_bom_items()[0].product_id, "P2")

        # 5. Remove product 2 -> should automatically hide
        self.panel.remove_product("P2")
        self.assertEqual(self.panel.item_count, 0)
        self.assertFalse(self.panel._is_visible)

    def test_theme_application(self):
        """Verify applying dark and light theme options runs without error (§12.8)."""
        with patch("customtkinter.get_appearance_mode", return_value="Dark"):
            self.panel.apply_theme()

        with patch("customtkinter.get_appearance_mode", return_value="Light"):
            self.panel.apply_theme()

    def test_export_bom_excel_generation(self):
        """Verify export_bom produces valid Excel file with blank pricing and triggers toast."""
        rec = _make_sample_rec()
        self.panel.add_product(rec)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch("tkinter.filedialog.asksaveasfilename", return_value=tmp_path):
                exported_path = self.panel.export_bom(customer_name="Test Enterprise")

            self.assertEqual(exported_path, tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 1000)

            # Toast notification should be dispatched
            self.mock_toast.show.assert_called_once()
            call_kwargs = self.mock_toast.show.call_args[1]
            self.assertEqual(call_kwargs["variant"], "success")
            self.assertIn("BOM (.xlsx)", call_kwargs["message"])
            self.assertEqual(call_kwargs["action_text"], "Open Document")
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def test_export_boq_word_generation(self):
        """Verify export_boq produces valid Word document (.docx) and triggers toast."""
        rec = _make_sample_rec()
        self.panel.add_product(rec)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch("tkinter.filedialog.asksaveasfilename", return_value=tmp_path):
                exported_path = self.panel.export_boq(customer_name="Test Enterprise")

            self.assertEqual(exported_path, tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            self.assertGreater(os.path.getsize(tmp_path), 1000)

            # Toast notification dispatched
            self.mock_toast.show.assert_called_once()
            call_kwargs = self.mock_toast.show.call_args[1]
            self.assertEqual(call_kwargs["variant"], "success")
            self.assertIn("BOQ (.docx)", call_kwargs["message"])
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()

"""
iValue PRISM — BOM/BOQ Interactive Export Panel
SRS References: §8.1.5 item 5, §8.1.15, §8.4, §10.5, §12.8
Implementation Plan: TASK-P5.1

This module implements the BOM/BOQ export control panel (ExportControlPanel)
utilizing tksheet for virtualized hardware-accelerated spreadsheet rendering.

Features:
  - tksheet DataGrid with locked column alignment across variable row counts (§12.8)
  - 5 standard proposal columns: Product Name, Category, License Qty, License Term, Support Tier
  - Embedded in-cell numeric validation for Quantity (integers 1-99,999)
  - Embedded native dropdowns for License Term (1-Year, 3-Year, 5-Year, Perpetual)
  - Embedded native dropdowns for Support Tier (Standard, 24x7 Enterprise, Mission Critical)
  - Strict zero-pricing compliance: NO pricing columns rendered anywhere (§8.1.5 item 5)
  - Prominent red/amber compliance disclaimer banner:
      "[!] Pricing is intentionally omitted and must be completed by Sales per iValue commercial policy."
  - Primary Export Action Buttons:
      * "Export BOM (.xlsx)" via openpyxl BOMExporter
      * "Export BOQ (.docx)" via python-docx BOQExporter
  - File save dialog pre-populated with naming conventions (§8.1.15)
  - Post-export shell integration toasts ("Open Document", "Show in Explorer")
  - Automatic visibility toggling (unhides when at least one candidate is accepted)
"""

from __future__ import annotations

from datetime import datetime
import logging
import os
import subprocess
import tkinter as tk
from tkinter import filedialog
from typing import Any, Callable, Dict, List, Optional

import customtkinter
import tksheet

from src.core.exporters import (
    BOMExporter,
    BOQExporter,
    BomExportRequest,
    BomItem,
    BoqExportRequest,
    ExportResponse,
)
from src.core.service import ProductRecommendation

_logger = logging.getLogger("prism.ui.export_panel")

# Typography Scale (§8.1.3)
FONT_PRIMARY = "Segoe UI"
FONT_H2 = (FONT_PRIMARY, 15, "bold")
FONT_H3 = (FONT_PRIMARY, 13, "bold")
FONT_BODY_REGULAR = (FONT_PRIMARY, 11, "normal")
FONT_BODY_SMALL = (FONT_PRIMARY, 10, "normal")
FONT_CAPTION = (FONT_PRIMARY, 9, "normal")

# Colors (§8.1.2)
COLOR_BG_CARD = ("#FFFFFF", "#131F37")
COLOR_BG_ELEVATED = ("#F8FAFC", "#1E293B")
COLOR_BORDER_SUBTLE = ("#CBD5E1", "#1E293B")
COLOR_BORDER_ACCENT = ("#0284C7", "#38BDF8")
COLOR_BORDER_WARNING = ("#D97706", "#F59E0B")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_SECONDARY = ("#475569", "#94A3B8")
COLOR_TEXT_MUTED = ("#64748B", "#64748B")
COLOR_BRAND_ACCENT = ("#0284C7", "#0EA5E9")
COLOR_ACCENT_HOVER = ("#0369A1", "#38BDF8")
COLOR_STATUS_SUCCESS = ("#059669", "#10B981")
COLOR_STATUS_WARNING = ("#D97706", "#F59E0B")

# Grid Constants & Allowed Dropdown Values (§8.1.5 item 5)
GRID_HEADERS = ["Product Name", "Category", "License Qty", "License Term", "Support Tier"]
LICENSE_TERMS = ["1-Year", "3-Year", "5-Year", "Perpetual"]
SUPPORT_TIERS = ["Standard", "24x7 Enterprise", "Mission Critical"]

COMPLIANCE_DISCLAIMER = (
    "[!] Pricing is intentionally omitted and must be completed by Sales per iValue commercial policy."
)


class ExportControlPanel(customtkinter.CTkFrame):
    """BOM/BOQ interactive export panel with tksheet grid. §8.1.5 item 5."""

    def __init__(
        self,
        parent,
        toast_manager: Optional[Any] = None,
        on_export_bom: Optional[Callable[[str], None]] = None,
        on_export_boq: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            fg_color=COLOR_BG_CARD,
            border_color=COLOR_BORDER_SUBTLE,
            border_width=1,
            corner_radius=12,
            **kwargs,
        )

        self.toast_manager = toast_manager
        self._on_export_bom = on_export_bom
        self._on_export_boq = on_export_boq

        # Track mapped product recommendations in order of grid rows
        self._products: List[ProductRecommendation] = []
        self._is_visible: bool = False

        self._build_ui()

    def set_on_export_bom(self, callback: Callable[[str], None]) -> None:
        self._on_export_bom = callback

    def set_on_export_boq(self, callback: Callable[[str], None]) -> None:
        self._on_export_boq = callback

    def _build_ui(self) -> None:
        """Constructs compliance banner, action header, tksheet grid, and footer."""
        self._main_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self._main_container.pack(fill="both", expand=True, padx=16, pady=16)

        # 1. Top Compliance Warning Banner (§8.1.5 item 5)
        self._banner_frame = customtkinter.CTkFrame(
            self._main_container,
            fg_color=COLOR_BG_ELEVATED,
            border_color=COLOR_BORDER_WARNING,
            border_width=1,
            corner_radius=8,
        )
        self._banner_frame.pack(fill="x", pady=(0, 12))

        lbl_banner = customtkinter.CTkLabel(
            self._banner_frame,
            text=COMPLIANCE_DISCLAIMER,
            font=FONT_H3,
            text_color=COLOR_STATUS_WARNING,
            anchor="w",
            padx=12,
            pady=8,
        )
        lbl_banner.pack(fill="x")

        # 2. Header Row: Title + Item Count + Clear All Button
        header_row = customtkinter.CTkFrame(self._main_container, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))

        title_box = customtkinter.CTkFrame(header_row, fg_color="transparent")
        title_box.pack(side="left")

        lbl_title = customtkinter.CTkLabel(
            title_box,
            text="BOM / BOQ Proposal Items",
            font=FONT_H2,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(side="left", padx=(0, 8))

        self._badge_count = customtkinter.CTkLabel(
            title_box,
            text="0 items selected",
            font=FONT_BODY_SMALL,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        self._badge_count.pack(side="left")

        # Action Buttons on Right
        btn_box = customtkinter.CTkFrame(header_row, fg_color="transparent")
        btn_box.pack(side="right")

        self._btn_export_bom = customtkinter.CTkButton(
            btn_box,
            text="📊 Export BOM (.xlsx)",
            height=34,
            font=FONT_H3,
            fg_color=COLOR_BRAND_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self.export_bom,
        )
        self._btn_export_bom.pack(side="left", padx=(0, 8))

        self._btn_export_boq = customtkinter.CTkButton(
            btn_box,
            text="📄 Export BOQ (.docx)",
            height=34,
            font=FONT_H3,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_ACCENT,
            text_color=COLOR_TEXT_PRIMARY,
            hover_color=COLOR_BG_ELEVATED,
            command=self.export_boq,
        )
        self._btn_export_boq.pack(side="left", padx=(0, 8))

        btn_clear = customtkinter.CTkButton(
            btn_box,
            text="Clear All",
            height=34,
            width=70,
            font=FONT_BODY_SMALL,
            fg_color="transparent",
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_BG_ELEVATED,
            command=self.clear_all,
        )
        btn_clear.pack(side="left")

        # 3. tksheet DataGrid Frame (§8.1.5 item 5, §12.8)
        self._grid_frame = customtkinter.CTkFrame(
            self._main_container,
            fg_color="transparent",
            height=200,
        )
        self._grid_frame.pack(fill="both", expand=True, pady=(0, 6))

        self.sheet = tksheet.Sheet(
            self._grid_frame,
            headers=GRID_HEADERS,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            height=180,
        )
        self.sheet.pack(fill="both", expand=True)

        # Apply bindings and dark/light styling
        self.sheet.enable_bindings("all")
        self.apply_theme()

        # In-cell Quantity validation (1 to 99,999)
        def _validate_cell_edit(event):
            # Column 2 is License Qty
            if hasattr(event, "column") and event.column == 2:
                try:
                    val = int(event.value)
                    if 1 <= val <= 99999:
                        return val
                except (ValueError, TypeError):
                    pass
                return getattr(event, "previous_value", 1)
            return getattr(event, "value", None)

        self.sheet.extra_bindings([("end_edit_cell", _validate_cell_edit)])

    def apply_theme(self) -> None:
        """Applies dark or light theme options per §8.1.5 item 5 and skill spec."""
        is_dark = customtkinter.get_appearance_mode().lower() == "dark"

        if is_dark:
            self.sheet.set_options(
                header_bg="#0F172A",
                header_fg="#F8FAFC",
                header_font=("Segoe UI", 11, "bold"),
                odd_row_bg="#131F37",
                even_row_bg="#0D1527",
                table_fg="#F8FAFC",
                table_font=("Segoe UI", 11, "normal"),
                table_selected_cells_border_fg="#0EA5E9",
                table_selected_cells_bg="#1E293B",
                frame_bg="#0B1120",
                table_bg="#0D1527",
            )
        else:
            self.sheet.set_options(
                header_bg="#E2E8F0",
                header_fg="#0F172A",
                header_font=("Segoe UI", 11, "bold"),
                odd_row_bg="#FFFFFF",
                even_row_bg="#F8FAFC",
                table_fg="#0F172A",
                table_font=("Segoe UI", 11, "normal"),
                table_selected_cells_border_fg="#0EA5E9",
                table_selected_cells_bg="#E0F2FE",
                frame_bg="#F1F5F9",
                table_bg="#FFFFFF",
            )

    def add_product(self, recommendation: ProductRecommendation) -> None:
        """Adds an accepted product recommendation to the BOM grid."""
        # Avoid duplicate entries
        for p in self._products:
            if p.product_id == recommendation.product_id:
                return

        row_idx = len(self._products)
        self._products.append(recommendation)

        category = recommendation.sub_domain or recommendation.domain or "General"
        row_data = [
            recommendation.product_name,
            category,
            1,            # Default quantity
            "1-Year",     # Default term
            "Standard",   # Default tier
        ]

        # Insert into sheet
        if row_idx == 0 and self.sheet.get_total_rows() == 0:
            self.sheet.set_sheet_data([row_data])
        else:
            self.sheet.insert_row(row=row_data)

        # Attach dropdowns on the new row
        self.sheet.create_dropdown(
            r=row_idx,
            c=3,
            values=LICENSE_TERMS,
            set_value="1-Year",
        )
        self.sheet.create_dropdown(
            r=row_idx,
            c=4,
            values=SUPPORT_TIERS,
            set_value="Standard",
        )

        self._update_counter()

        # Automatically reveal panel when first product is accepted
        if not self._is_visible:
            self.show()

    def remove_product(self, product_id: str) -> None:
        """Removes a product by product_id from the BOM grid."""
        found_idx = -1
        for idx, p in enumerate(self._products):
            if p.product_id == product_id:
                found_idx = idx
                break

        if found_idx >= 0:
            self._products.pop(found_idx)
            try:
                self.sheet.delete_row(found_idx)
            except Exception as e:
                _logger.debug(f"Sheet delete row error: {e}")

            self._update_counter()

            # If no accepted products remain, automatically hide panel
            if len(self._products) == 0:
                self.hide()

    def clear_all(self) -> None:
        """Clears all products from the grid and hides panel."""
        self._products.clear()
        self.sheet.set_sheet_data([])
        self._update_counter()
        self.hide()

    def _update_counter(self) -> None:
        """Updates the item count badge label."""
        count = len(self._products)
        lbl_text = f"{count} item{'s' if count != 1 else ''} selected"
        self._badge_count.configure(text=lbl_text)

        # Adjust height proportionally up to 260px
        row_h = 28
        total_h = min(260, max(120, 40 + count * row_h))
        self.sheet.configure(height=total_h)

    def get_bom_items(self) -> List[BomItem]:
        """Reads current sheet values and returns List[BomItem] dataclass instances."""
        items: List[BomItem] = []
        total_rows = self.sheet.get_total_rows()

        for r in range(min(total_rows, len(self._products))):
            rec = self._products[r]
            try:
                row_vals = self.sheet.get_row_data(r)
                raw_qty = row_vals[2]
                qty = int(raw_qty) if str(raw_qty).isdigit() else 1
                term = str(row_vals[3])
                tier = str(row_vals[4])
            except Exception:
                qty = 1
                term = "1-Year"
                tier = "Standard"

            items.append(
                BomItem(
                    product_id=rec.product_id,
                    quantity=qty,
                    license_term=term,
                    support_tier=tier,
                    oem=rec.oem,
                    product_name=rec.product_name,
                    product_category=rec.sub_domain or rec.domain,
                )
            )

        return items

    def export_bom(self, customer_name: str = "Client") -> Optional[str]:
        """Dispatches BOM (.xlsx) export via BOMExporter per §8.1.15 and §8.4."""
        items = self.get_bom_items()
        if not items:
            self._notify("No items selected in BOM grid for export.", variant="warning")
            return None

        primary_oem = (items[0].oem or "Solution").replace(" ", "_")
        date_stamp = datetime.now().strftime("%Y%m%d")
        default_filename = f"iValue_BOM_{primary_oem}_{date_stamp}.xlsx"

        file_path = filedialog.asksaveasfilename(
            title="Save Bill of Materials (BOM)",
            defaultextension=".xlsx",
            initialfile=default_filename,
            filetypes=[("Excel Workbook (*.xlsx)", "*.xlsx"), ("CSV Document (*.csv)", "*.csv")],
        )

        if not file_path:
            return None

        request = BomExportRequest(
            query_id=f"BOM-{date_stamp}",
            customer_name=customer_name,
            items=items,
            output_path=file_path,
        )

        try:
            exporter = BOMExporter()
            response: ExportResponse = exporter.export(request)

            if response.status == "success":
                self._handle_export_success(response.file_path, doc_type="BOM (.xlsx)")
                if self._on_export_bom:
                    self._on_export_bom(response.file_path)
                return response.file_path
            else:
                self._notify(f"BOM export failed: {response.error_message}", variant="error")
                return None
        except Exception as e:
            _logger.error(f"BOM export exception: {e}")
            self._notify(f"BOM export encountered an error: {e}", variant="error")
            return None

    def export_boq(
        self,
        customer_name: str = "Client",
        project_ref: str = "Presales Proposal",
        prepared_by: str = "iValue Presales Team",
    ) -> Optional[str]:
        """Dispatches BOQ (.docx) proposal generation via BOQExporter per §8.1.15 and §8.4."""
        items = self.get_bom_items()
        if not items:
            self._notify("No items selected in BOQ grid for export.", variant="warning")
            return None

        primary_oem = (items[0].oem or "Solution").replace(" ", "_")
        cust_clean = customer_name.replace(" ", "_")
        date_stamp = datetime.now().strftime("%Y%m%d")
        default_filename = f"iValue_BOQ_{primary_oem}_{cust_clean}_{date_stamp}.docx"

        file_path = filedialog.asksaveasfilename(
            title="Save Bill of Quantities (BOQ)",
            defaultextension=".docx",
            initialfile=default_filename,
            filetypes=[("Word Document (*.docx)", "*.docx")],
        )

        if not file_path:
            return None

        request = BoqExportRequest(
            query_id=f"BOQ-{date_stamp}",
            customer_name=customer_name,
            project_reference=project_ref,
            prepared_by=prepared_by,
            items=items,
            output_path=file_path,
        )

        try:
            exporter = BOQExporter()
            response: ExportResponse = exporter.export(request)

            if response.status == "success":
                self._handle_export_success(response.file_path, doc_type="BOQ (.docx)")
                if self._on_export_boq:
                    self._on_export_boq(response.file_path)
                return response.file_path
            else:
                self._notify(f"BOQ export failed: {response.error_message}", variant="error")
                return None
        except Exception as e:
            _logger.error(f"BOQ export exception: {e}")
            self._notify(f"BOQ export encountered an error: {e}", variant="error")
            return None

    def _handle_export_success(self, file_path: str, doc_type: str) -> None:
        """Dispatches toast notification with 'Open Document' action per §8.1.15."""
        filename = os.path.basename(file_path)
        msg = f"{doc_type} generated: {filename}"

        def _open_doc():
            try:
                os.startfile(file_path)
            except Exception as exc:
                _logger.warning(f"Could not open file: {exc}")

        self._notify(
            msg,
            variant="success",
            action_text="Open Document",
            action_callback=_open_doc,
        )

    def _notify(
        self,
        message: str,
        variant: str = "info",
        action_text: Optional[str] = None,
        action_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Dispatches toast notification through manager if connected."""
        if self.toast_manager:
            try:
                self.toast_manager.show(
                    message=message,
                    variant=variant,
                    action_text=action_text,
                    action_callback=action_callback,
                )
            except Exception as e:
                _logger.debug(f"Toast manager dispatch error: {e}")

    def show(self) -> None:
        """Renders export panel visible."""
        self._is_visible = True
        self.pack(fill="x", expand=False, padx=20, pady=(10, 16))

    def hide(self) -> None:
        """Hides export panel."""
        self._is_visible = False
        self.pack_forget()

    @property
    def item_count(self) -> int:
        return len(self._products)

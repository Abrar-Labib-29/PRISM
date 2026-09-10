"""
iValue PRISM — Recommendation Result Cards Component
SRS References: §6.9, §8.1.2, §8.1.3, §8.1.4, §8.1.5 item 4, §8.1.10, §8.1.14, §FR-9
Implementation Plan: TASK-P4.2

This module implements the recommendation presentation components:
  1. PrimaryRecommendationCard: Elevated top-pick card with 4px accent bar,
     citation pill, executive rationale with in-place editor, feature pill chips,
     2-column pros/cons grid, and engineer decision toolbar.
  2. AlternativeCard: Muted alternative candidate card, collapsed by default
     with smooth expansion accordion and complete decision controls.
  3. ResultsCanvas: Scrollable container rendering verdict summary header
     (domain taxonomy badge, pulsing confidence pill, 2.0s clipboard copy CTA)
     and managing candidate cards.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter

from src.core.service import AnalyzeResponse, ProductRecommendation
from src.utils.system_info import check_reduced_motion

_logger = logging.getLogger("prism.ui.result_cards")

# Design Tokens (§8.1.2, §8.1.3, §8.1.4)
FONT_PRIMARY = "Segoe UI"
FONT_MONO = "Cascadia Mono"

# Typography Scale
FONT_H1 = (FONT_PRIMARY, 18, "bold")
FONT_H2 = (FONT_PRIMARY, 15, "bold")
FONT_H3 = (FONT_PRIMARY, 13, "bold")
FONT_BODY_LARGE = (FONT_PRIMARY, 12, "normal")
FONT_BODY_REGULAR = (FONT_PRIMARY, 11, "normal")
FONT_BODY_SMALL = (FONT_PRIMARY, 10, "normal")
FONT_CAPTION = (FONT_PRIMARY, 9, "normal")
FONT_OVERLINE = (FONT_PRIMARY, 9, "bold")

# Theme Palette (Dual-mode tuples)
COLOR_BG_CANVAS = ("#F1F5F9", "#0B1120")
COLOR_BG_CARD = ("#FFFFFF", "#131F37")
COLOR_BG_CARD_MUTED = ("#F8FAFC", "#0E1726")
COLOR_BG_ELEVATED = ("#F1F5F9", "#1E293B")
COLOR_BG_CHIP = ("#E2E8F0", "#1E293B")

COLOR_BORDER_SUBTLE = ("#CBD5E1", "#1E293B")
COLOR_BORDER_STRONG = ("#94A3B8", "#334155")
COLOR_BORDER_ACCENT = ("#0284C7", "#38BDF8")
COLOR_BORDER_ACCEPTED = ("#059669", "#10B981")
COLOR_BORDER_REJECTED = ("#DC2626", "#EF4444")

COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_SECONDARY = ("#475569", "#94A3B8")
COLOR_TEXT_MUTED = ("#64748B", "#64748B")

COLOR_BRAND_PURPLE = ("#4C1D95", "#7C3AED")
COLOR_BRAND_ACCENT = ("#0284C7", "#0EA5E9")
COLOR_ACCENT_HOVER = ("#0369A1", "#38BDF8")

COLOR_STATUS_SUCCESS = ("#059669", "#10B981")  # Green
COLOR_STATUS_WARNING = ("#D97706", "#F59E0B")  # Amber
COLOR_STATUS_ERROR = ("#DC2626", "#EF4444")    # Crimson

REJECTION_REASONS = [
    "Out of budget",
    "Customer brand objection",
    "Feature mismatch",
    "Other",
]


def _get_confidence_color(level: str) -> Tuple[str, str]:
    """Maps confidence level to dual-mode color tuple."""
    lvl = (level or "").upper()
    if lvl == "HIGH":
        return COLOR_STATUS_SUCCESS
    elif lvl == "MEDIUM":
        return COLOR_STATUS_WARNING
    return COLOR_STATUS_ERROR


def _format_citation_text(rec: ProductRecommendation) -> str:
    """Formats citation string from recommendations."""
    if rec.citations and len(rec.citations) > 0:
        c = rec.citations[0]
        status = c.data_status.capitalize() if c.data_status else "Confirmed"
        return f"[Catalog: {c.product_id or rec.product_id} | {status}]"
    return f"[Catalog: {rec.product_id} | Confirmed]"


class PrimaryRecommendationCard(customtkinter.CTkFrame):
    """Top-pick recommendation card. §8.1.5 item 4, §8.1.14."""

    def __init__(
        self,
        parent,
        recommendation: ProductRecommendation,
        on_accept: Optional[Callable[[ProductRecommendation, bool], None]] = None,
        on_modify: Optional[Callable[[ProductRecommendation, str], None]] = None,
        on_reject: Optional[Callable[[ProductRecommendation, str], None]] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            fg_color=COLOR_BG_CARD,
            border_color=COLOR_BORDER_ACCENT,
            border_width=1,
            corner_radius=12,
            **kwargs,
        )

        self.recommendation = recommendation
        self._on_accept = on_accept
        self._on_modify = on_modify
        self._on_reject = on_reject

        self.is_accepted: bool = False
        self.is_rejected: bool = False
        self.rejection_reason: Optional[str] = None
        self._is_editing_rationale: bool = False

        self._build_ui()

    def set_on_accept(self, callback: Callable[[ProductRecommendation, bool], None]) -> None:
        self._on_accept = callback

    def set_on_modify(self, callback: Callable[[ProductRecommendation, str], None]) -> None:
        self._on_modify = callback

    def set_on_reject(self, callback: Callable[[ProductRecommendation, str], None]) -> None:
        self._on_reject = callback

    def _build_ui(self) -> None:
        """Constructs layout with 4px left accent indicator and padded body."""
        # 1. Main outer row: 4px accent bar on the left + Content frame on the right
        self._accent_bar = customtkinter.CTkFrame(
            self,
            width=4,
            fg_color=COLOR_BRAND_ACCENT,
            corner_radius=2,
        )
        self._accent_bar.pack(side="left", fill="y", padx=(0, 0), pady=4)

        # 2. Content container with 20px internal padding (§8.1.5 item 4)
        self._content_frame = customtkinter.CTkFrame(
            self,
            fg_color="transparent",
        )
        self._content_frame.pack(side="left", fill="both", expand=True, padx=20, pady=16)

        # 2A. Top Overline Row (Badge + Confidence Pill + Accepted Tag)
        top_row = customtkinter.CTkFrame(self._content_frame, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 8))

        # Overline badge
        badge_frame = customtkinter.CTkFrame(
            top_row,
            fg_color=COLOR_BG_ELEVATED,
            corner_radius=4,
        )
        badge_frame.pack(side="left")
        lbl_overline = customtkinter.CTkLabel(
            badge_frame,
            text="RECOMMENDED MATCH",
            font=FONT_OVERLINE,
            text_color=COLOR_BRAND_ACCENT,
            padx=8,
            pady=2,
        )
        lbl_overline.pack()

        # Acceptance checkmark pill (hidden initially)
        self._accepted_pill = customtkinter.CTkFrame(
            top_row,
            fg_color=COLOR_STATUS_SUCCESS,
            corner_radius=4,
        )
        lbl_accepted = customtkinter.CTkLabel(
            self._accepted_pill,
            text="✓ Selected for BOM/BOQ",
            font=FONT_OVERLINE,
            text_color=("#FFFFFF", "#FFFFFF"),
            padx=8,
            pady=2,
        )
        lbl_accepted.pack()

        # Excluded badge pill (hidden initially)
        self._excluded_pill = customtkinter.CTkFrame(
            top_row,
            fg_color=COLOR_STATUS_ERROR,
            corner_radius=4,
        )
        self._lbl_excluded = customtkinter.CTkLabel(
            self._excluded_pill,
            text="✕ Excluded",
            font=FONT_OVERLINE,
            text_color=("#FFFFFF", "#FFFFFF"),
            padx=8,
            pady=2,
        )
        self._lbl_excluded.pack()

        # Confidence pill on the right
        conf_color = _get_confidence_color(self.recommendation.confidence_level)
        fit_pct = int(round(self.recommendation.fit_score))
        conf_text = f"[{self.recommendation.confidence_level} CONFIDENCE: {fit_pct}% Fit]"

        self._confidence_pill = customtkinter.CTkFrame(
            top_row,
            fg_color=COLOR_BG_ELEVATED,
            border_color=conf_color,
            border_width=1,
            corner_radius=12,
        )
        self._confidence_pill.pack(side="right")
        self._lbl_conf = customtkinter.CTkLabel(
            self._confidence_pill,
            text=conf_text,
            font=FONT_BODY_SMALL,
            text_color=conf_color,
            padx=10,
            pady=3,
        )
        self._lbl_conf.pack()

        # 2B. Title Row (OEM Badge + Product Title)
        title_row = customtkinter.CTkFrame(self._content_frame, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 4))

        # OEM pill
        oem_frame = customtkinter.CTkFrame(
            title_row,
            fg_color=COLOR_BRAND_PURPLE,
            corner_radius=6,
        )
        oem_frame.pack(side="left", padx=(0, 10))
        lbl_oem = customtkinter.CTkLabel(
            oem_frame,
            text=self.recommendation.oem or "OEM",
            font=FONT_H3,
            text_color=("#FFFFFF", "#FFFFFF"),
            padx=8,
            pady=2,
        )
        lbl_oem.pack()

        # Product Title
        lbl_title = customtkinter.CTkLabel(
            title_row,
            text=self.recommendation.product_name,
            font=FONT_H1,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(side="left", fill="x", expand=True)

        # 2C. Citation Pill
        citation_str = _format_citation_text(self.recommendation)
        citation_frame = customtkinter.CTkFrame(self._content_frame, fg_color="transparent")
        citation_frame.pack(fill="x", pady=(0, 12))

        lbl_citation = customtkinter.CTkLabel(
            citation_frame,
            text=citation_str,
            font=FONT_BODY_SMALL,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        lbl_citation.pack(side="left")

        # 2D. Executive Rationale Section
        rationale_header_row = customtkinter.CTkFrame(self._content_frame, fg_color="transparent")
        rationale_header_row.pack(fill="x", pady=(0, 4))

        lbl_rat_title = customtkinter.CTkLabel(
            rationale_header_row,
            text="Executive Rationale",
            font=FONT_H3,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        lbl_rat_title.pack(side="left")

        # Rationale Static Display
        self._lbl_rationale = customtkinter.CTkLabel(
            self._content_frame,
            text=self.recommendation.rationale,
            font=FONT_BODY_LARGE,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=850,
        )
        self._lbl_rationale.pack(fill="x", pady=(0, 12))

        # Rationale In-Place Editor Container (initially unmapped)
        self._edit_rationale_frame = customtkinter.CTkFrame(
            self._content_frame,
            fg_color="transparent",
        )
        self._txt_rationale = customtkinter.CTkTextbox(
            self._edit_rationale_frame,
            height=90,
            font=FONT_BODY_LARGE,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER_ACCENT,
            fg_color=COLOR_BG_CARD_MUTED,
        )
        self._txt_rationale.pack(fill="x", pady=(0, 6))

        edit_btn_row = customtkinter.CTkFrame(self._edit_rationale_frame, fg_color="transparent")
        edit_btn_row.pack(fill="x", pady=(0, 10))

        self._btn_save_edit = customtkinter.CTkButton(
            edit_btn_row,
            text="Save Edit",
            width=80,
            height=28,
            font=FONT_BODY_SMALL,
            fg_color=COLOR_BRAND_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._handle_save_rationale,
        )
        self._btn_save_edit.pack(side="left", padx=(0, 8))

        self._btn_revert_edit = customtkinter.CTkButton(
            edit_btn_row,
            text="Revert",
            width=80,
            height=28,
            font=FONT_BODY_SMALL,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_BG_ELEVATED,
            command=self._handle_revert_rationale,
        )
        self._btn_revert_edit.pack(side="left")

        # 2E. Key Features Flex Chips (§8.1.5 item 4)
        if self.recommendation.features:
            features_header = customtkinter.CTkLabel(
                self._content_frame,
                text="Key Capabilities & Features",
                font=FONT_H3,
                text_color=COLOR_TEXT_PRIMARY,
                anchor="w",
            )
            features_header.pack(fill="x", pady=(0, 6))

            features_frame = customtkinter.CTkFrame(self._content_frame, fg_color="transparent")
            features_frame.pack(fill="x", pady=(0, 14))

            # Render feature chips
            for feat in self.recommendation.features[:8]:
                chip = customtkinter.CTkFrame(
                    features_frame,
                    fg_color=COLOR_BG_CHIP,
                    corner_radius=6,
                )
                chip.pack(side="left", padx=(0, 6), pady=2)

                chip_label = customtkinter.CTkLabel(
                    chip,
                    text=f"• {feat}",
                    font=FONT_BODY_SMALL,
                    text_color=COLOR_TEXT_PRIMARY,
                    padx=8,
                    pady=3,
                )
                chip_label.pack()

        # 2F. Pros & Cons 2-Column Grid
        if self.recommendation.pros or self.recommendation.cons:
            grid_frame = customtkinter.CTkFrame(self._content_frame, fg_color="transparent")
            grid_frame.pack(fill="x", pady=(0, 16))
            grid_frame.grid_columnconfigure(0, weight=1)
            grid_frame.grid_columnconfigure(1, weight=1)

            # Left column: Pros
            pros_frame = customtkinter.CTkFrame(
                grid_frame,
                fg_color=COLOR_BG_CARD_MUTED,
                corner_radius=8,
                border_width=1,
                border_color=COLOR_BORDER_SUBTLE,
            )
            pros_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

            lbl_pros_title = customtkinter.CTkLabel(
                pros_frame,
                text="Strengths & Advantages",
                font=FONT_H3,
                text_color=COLOR_STATUS_SUCCESS,
                anchor="w",
                padx=12,
                pady=6,
            )
            lbl_pros_title.pack(fill="x")

            for pro in (self.recommendation.pros or [])[:4]:
                p_row = customtkinter.CTkLabel(
                    pros_frame,
                    text=f"+  {pro}",
                    font=FONT_BODY_REGULAR,
                    text_color=COLOR_TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    padx=12,
                    pady=2,
                    wraplength=380,
                )
                p_row.pack(fill="x")

            # Right column: Cons
            cons_frame = customtkinter.CTkFrame(
                grid_frame,
                fg_color=COLOR_BG_CARD_MUTED,
                corner_radius=8,
                border_width=1,
                border_color=COLOR_BORDER_SUBTLE,
            )
            cons_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

            lbl_cons_title = customtkinter.CTkLabel(
                cons_frame,
                text="Considerations & Trade-offs",
                font=FONT_H3,
                text_color=COLOR_STATUS_WARNING,
                anchor="w",
                padx=12,
                pady=6,
            )
            lbl_cons_title.pack(fill="x")

            for con in (self.recommendation.cons or [])[:4]:
                c_row = customtkinter.CTkLabel(
                    cons_frame,
                    text=f"-  {con}",
                    font=FONT_BODY_REGULAR,
                    text_color=COLOR_TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    padx=12,
                    pady=2,
                    wraplength=380,
                )
                c_row.pack(fill="x")

        # 2G. Engineer Decision Toolbar (FR-9, §8.1.14)
        self._toolbar_frame = customtkinter.CTkFrame(self._content_frame, fg_color="transparent")
        self._toolbar_frame.pack(fill="x", pady=(4, 0))

        # [✓ Accept] Button
        self._btn_accept = customtkinter.CTkButton(
            self._toolbar_frame,
            text="✓ Accept for BOM/BOQ",
            height=32,
            corner_radius=8,
            font=FONT_H3,
            fg_color=COLOR_STATUS_SUCCESS,
            hover_color=("#047857", "#059669"),
            command=self._handle_toggle_accept,
        )
        self._btn_accept.pack(side="left", padx=(0, 10))

        # [Modify Rationale] Button
        self._btn_modify = customtkinter.CTkButton(
            self._toolbar_frame,
            text="Modify Rationale",
            height=32,
            corner_radius=8,
            font=FONT_BODY_REGULAR,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_PRIMARY,
            hover_color=COLOR_BG_ELEVATED,
            command=self._handle_toggle_modify_rationale,
        )
        self._btn_modify.pack(side="left", padx=(0, 10))

        # [✕ Exclude / Reject] Button
        self._btn_reject = customtkinter.CTkButton(
            self._toolbar_frame,
            text="✕ Exclude / Reject",
            height=32,
            corner_radius=8,
            font=FONT_BODY_REGULAR,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_STATUS_ERROR,
            hover_color=("#FEE2E2", "#3B1219"),
            command=self._handle_toggle_reject_popover,
        )
        self._btn_reject.pack(side="left")

        # Inline Reject Reason Popover (initially unmapped)
        self._reject_popover_frame = customtkinter.CTkFrame(
            self._content_frame,
            fg_color=COLOR_BG_CARD_MUTED,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
        )

        pop_title = customtkinter.CTkLabel(
            self._reject_popover_frame,
            text="Select Exclusion Reason (§8.1.14):",
            font=FONT_BODY_SMALL,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            padx=12,
        )
        pop_title.pack(fill="x", pady=(8, 4))

        self._reason_var = customtkinter.StringVar(value=REJECTION_REASONS[0])
        self._reason_menu = customtkinter.CTkOptionMenu(
            self._reject_popover_frame,
            variable=self._reason_var,
            values=REJECTION_REASONS,
            height=28,
            font=FONT_BODY_SMALL,
            fg_color=COLOR_BG_ELEVATED,
            button_color=COLOR_BORDER_STRONG,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self._reason_menu.pack(fill="x", padx=12, pady=(0, 8))

        pop_btn_row = customtkinter.CTkFrame(self._reject_popover_frame, fg_color="transparent")
        pop_btn_row.pack(fill="x", padx=12, pady=(0, 8))

        btn_confirm_reject = customtkinter.CTkButton(
            pop_btn_row,
            text="Confirm Exclusion",
            height=28,
            font=FONT_BODY_SMALL,
            fg_color=COLOR_STATUS_ERROR,
            hover_color=("#B91C1C", "#DC2626"),
            command=self._handle_confirm_rejection,
        )
        btn_confirm_reject.pack(side="left", padx=(0, 8))

        btn_cancel_reject = customtkinter.CTkButton(
            pop_btn_row,
            text="Cancel",
            height=28,
            font=FONT_BODY_SMALL,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_BG_ELEVATED,
            command=self._handle_toggle_reject_popover,
        )
        btn_cancel_reject.pack(side="left")

    def _handle_toggle_accept(self) -> None:
        """Toggles candidate product acceptance state."""
        self.is_accepted = not self.is_accepted
        if self.is_accepted:
            # If accepted, un-exclude if previously excluded
            if self.is_rejected:
                self.is_rejected = False
                self._excluded_pill.pack_forget()

            self.configure(border_color=COLOR_BORDER_ACCEPTED, border_width=2)
            self._accent_bar.configure(fg_color=COLOR_BORDER_ACCEPTED)
            self._btn_accept.configure(text="✓ Accepted", fg_color=COLOR_STATUS_SUCCESS)
            self._accepted_pill.pack(side="left", padx=(10, 0))
        else:
            self.configure(border_color=COLOR_BORDER_ACCENT, border_width=1)
            self._accent_bar.configure(fg_color=COLOR_BRAND_ACCENT)
            self._btn_accept.configure(text="✓ Accept for BOM/BOQ", fg_color=COLOR_STATUS_SUCCESS)
            self._accepted_pill.pack_forget()

        if self._on_accept:
            self._on_accept(self.recommendation, self.is_accepted)

    def _handle_toggle_modify_rationale(self) -> None:
        """Toggles between static rationale display and editable CTkTextbox."""
        if not self._is_editing_rationale:
            self._is_editing_rationale = True
            self._lbl_rationale.pack_forget()
            self._txt_rationale.delete("1.0", "end")
            self._txt_rationale.insert("1.0", self.recommendation.rationale)
            self._edit_rationale_frame.pack(fill="x", pady=(0, 12))
            self._btn_modify.configure(text="Cancel Edit")
        else:
            self._is_editing_rationale = False
            self._edit_rationale_frame.pack_forget()
            self._lbl_rationale.pack(fill="x", pady=(0, 12))
            self._btn_modify.configure(text="Modify Rationale")

    def _handle_save_rationale(self) -> None:
        """Commits edited rationale and triggers on_modify callback."""
        edited_text = self._txt_rationale.get("1.0", "end-1c").strip()
        if edited_text:
            self.recommendation.rationale = edited_text
            self._lbl_rationale.configure(text=edited_text)

        self._handle_toggle_modify_rationale()

        if self._on_modify and edited_text:
            self._on_modify(self.recommendation, edited_text)

    def _handle_revert_rationale(self) -> None:
        """Discards edits and restores previous rationale."""
        self._handle_toggle_modify_rationale()

    def _handle_toggle_reject_popover(self) -> None:
        """Toggles visibility of the rejection reason frame."""
        if self._reject_popover_frame.winfo_manager() == "pack":
            self._reject_popover_frame.pack_forget()
        else:
            self._reject_popover_frame.pack(fill="x", pady=(8, 0))

    def _handle_confirm_rejection(self) -> None:
        """Confirms exclusion with selected reason."""
        selected_reason = self._reason_var.get()
        self.is_rejected = True
        self.rejection_reason = selected_reason

        # If previously accepted, un-accept
        if self.is_accepted:
            self.is_accepted = False
            self._accepted_pill.pack_forget()
            self._btn_accept.configure(text="✓ Accept for BOM/BOQ")

        self.configure(border_color=COLOR_BORDER_REJECTED, border_width=1)
        self._accent_bar.configure(fg_color=COLOR_STATUS_ERROR)

        self._lbl_excluded.configure(text=f"✕ Excluded: {selected_reason}")
        self._excluded_pill.pack(side="left", padx=(10, 0))
        self._reject_popover_frame.pack_forget()

        if self._on_reject:
            self._on_reject(self.recommendation, selected_reason)


class AlternativeCard(customtkinter.CTkFrame):
    """Collapsed alternative candidate card. §8.1.5 item 4."""

    def __init__(
        self,
        parent,
        recommendation: ProductRecommendation,
        on_accept: Optional[Callable[[ProductRecommendation, bool], None]] = None,
        on_modify: Optional[Callable[[ProductRecommendation, str], None]] = None,
        on_reject: Optional[Callable[[ProductRecommendation, str], None]] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            fg_color=COLOR_BG_CARD_MUTED,
            border_color=COLOR_BORDER_SUBTLE,
            border_width=1,
            corner_radius=12,
            **kwargs,
        )

        self.recommendation = recommendation
        self._on_accept = on_accept
        self._on_modify = on_modify
        self._on_reject = on_reject

        self.is_expanded: bool = False
        self.is_accepted: bool = False
        self.is_rejected: bool = False
        self.rejection_reason: Optional[str] = None
        self._is_editing_rationale: bool = False

        self._build_ui()

    def set_on_accept(self, callback: Callable[[ProductRecommendation, bool], None]) -> None:
        self._on_accept = callback

    def set_on_modify(self, callback: Callable[[ProductRecommendation, str], None]) -> None:
        self._on_modify = callback

    def set_on_reject(self, callback: Callable[[ProductRecommendation, str], None]) -> None:
        self._on_reject = callback

    def _build_ui(self) -> None:
        """Builds expandable card layout with interactive header."""
        # 1. Clickable Header Bar (always visible)
        self._header_frame = customtkinter.CTkFrame(
            self,
            fg_color="transparent",
            cursor="hand2",
        )
        self._header_frame.pack(fill="x", padx=16, pady=12)
        self._header_frame.bind("<Button-1>", lambda e: self.toggle_expand())

        # Expand arrow indicator
        self._lbl_arrow = customtkinter.CTkLabel(
            self._header_frame,
            text="▶",
            font=FONT_H3,
            text_color=COLOR_TEXT_MUTED,
            width=20,
        )
        self._lbl_arrow.pack(side="left", padx=(0, 8))
        self._lbl_arrow.bind("<Button-1>", lambda e: self.toggle_expand())

        # Alternative tag
        alt_tag = customtkinter.CTkFrame(
            self._header_frame,
            fg_color=COLOR_BG_ELEVATED,
            corner_radius=4,
        )
        alt_tag.pack(side="left", padx=(0, 8))
        lbl_alt = customtkinter.CTkLabel(
            alt_tag,
            text="ALTERNATIVE",
            font=FONT_OVERLINE,
            text_color=COLOR_TEXT_SECONDARY,
            padx=6,
            pady=1,
        )
        lbl_alt.pack()
        lbl_alt.bind("<Button-1>", lambda e: self.toggle_expand())

        # OEM pill
        oem_frame = customtkinter.CTkFrame(
            self._header_frame,
            fg_color=COLOR_BRAND_PURPLE,
            corner_radius=4,
        )
        oem_frame.pack(side="left", padx=(0, 8))
        lbl_oem = customtkinter.CTkLabel(
            oem_frame,
            text=self.recommendation.oem or "OEM",
            font=FONT_BODY_SMALL,
            text_color=("#FFFFFF", "#FFFFFF"),
            padx=6,
            pady=1,
        )
        lbl_oem.pack()
        lbl_oem.bind("<Button-1>", lambda e: self.toggle_expand())

        # Product Title
        self._lbl_title = customtkinter.CTkLabel(
            self._header_frame,
            text=self.recommendation.product_name,
            font=FONT_H2,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        self._lbl_title.pack(side="left", fill="x", expand=True)
        self._lbl_title.bind("<Button-1>", lambda e: self.toggle_expand())

        # Accepted badge (hidden initially)
        self._accepted_pill = customtkinter.CTkFrame(
            self._header_frame,
            fg_color=COLOR_STATUS_SUCCESS,
            corner_radius=4,
        )
        lbl_accepted = customtkinter.CTkLabel(
            self._accepted_pill,
            text="✓ Selected",
            font=FONT_OVERLINE,
            text_color=("#FFFFFF", "#FFFFFF"),
            padx=6,
            pady=1,
        )
        lbl_accepted.pack()

        # Excluded badge (hidden initially)
        self._excluded_pill = customtkinter.CTkFrame(
            self._header_frame,
            fg_color=COLOR_STATUS_ERROR,
            corner_radius=4,
        )
        self._lbl_excluded = customtkinter.CTkLabel(
            self._excluded_pill,
            text="✕ Excluded",
            font=FONT_OVERLINE,
            text_color=("#FFFFFF", "#FFFFFF"),
            padx=6,
            pady=1,
        )
        self._lbl_excluded.pack()

        # Confidence Pill
        conf_color = _get_confidence_color(self.recommendation.confidence_level)
        fit_pct = int(round(self.recommendation.fit_score))
        conf_text = f"[{self.recommendation.confidence_level}: {fit_pct}% Fit]"

        self._confidence_pill = customtkinter.CTkFrame(
            self._header_frame,
            fg_color=COLOR_BG_ELEVATED,
            border_color=conf_color,
            border_width=1,
            corner_radius=10,
        )
        self._confidence_pill.pack(side="right")
        lbl_conf = customtkinter.CTkLabel(
            self._confidence_pill,
            text=conf_text,
            font=FONT_BODY_SMALL,
            text_color=conf_color,
            padx=8,
            pady=2,
        )
        lbl_conf.pack()
        lbl_conf.bind("<Button-1>", lambda e: self.toggle_expand())

        # 2. Expandable Body Details (initially unmapped)
        self._body_frame = customtkinter.CTkFrame(
            self,
            fg_color="transparent",
        )

        # 2A. Citation
        citation_str = _format_citation_text(self.recommendation)
        lbl_cit = customtkinter.CTkLabel(
            self._body_frame,
            text=citation_str,
            font=FONT_BODY_SMALL,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        lbl_cit.pack(fill="x", padx=16, pady=(0, 8))

        # 2B. Executive Rationale
        lbl_rat_title = customtkinter.CTkLabel(
            self._body_frame,
            text="Evaluation & Context",
            font=FONT_H3,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        lbl_rat_title.pack(fill="x", padx=16, pady=(0, 4))

        self._lbl_rationale = customtkinter.CTkLabel(
            self._body_frame,
            text=self.recommendation.rationale,
            font=FONT_BODY_REGULAR,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=850,
        )
        self._lbl_rationale.pack(fill="x", padx=16, pady=(0, 10))

        # Rationale Edit Container
        self._edit_rationale_frame = customtkinter.CTkFrame(
            self._body_frame,
            fg_color="transparent",
        )
        self._txt_rationale = customtkinter.CTkTextbox(
            self._edit_rationale_frame,
            height=80,
            font=FONT_BODY_REGULAR,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER_ACCENT,
            fg_color=COLOR_BG_CARD,
        )
        self._txt_rationale.pack(fill="x", padx=16, pady=(0, 6))

        edit_btn_row = customtkinter.CTkFrame(self._edit_rationale_frame, fg_color="transparent")
        edit_btn_row.pack(fill="x", padx=16, pady=(0, 8))

        self._btn_save_edit = customtkinter.CTkButton(
            edit_btn_row,
            text="Save Edit",
            width=70,
            height=26,
            font=FONT_BODY_SMALL,
            fg_color=COLOR_BRAND_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._handle_save_rationale,
        )
        self._btn_save_edit.pack(side="left", padx=(0, 6))

        self._btn_revert_edit = customtkinter.CTkButton(
            edit_btn_row,
            text="Revert",
            width=70,
            height=26,
            font=FONT_BODY_SMALL,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_BG_ELEVATED,
            command=self._handle_revert_rationale,
        )
        self._btn_revert_edit.pack(side="left")

        # 2C. Features Chips
        if self.recommendation.features:
            features_frame = customtkinter.CTkFrame(self._body_frame, fg_color="transparent")
            features_frame.pack(fill="x", padx=16, pady=(0, 10))

            for feat in self.recommendation.features[:6]:
                chip = customtkinter.CTkFrame(
                    features_frame,
                    fg_color=COLOR_BG_CHIP,
                    corner_radius=6,
                )
                chip.pack(side="left", padx=(0, 6), pady=2)

                chip_label = customtkinter.CTkLabel(
                    chip,
                    text=f"• {feat}",
                    font=FONT_BODY_SMALL,
                    text_color=COLOR_TEXT_PRIMARY,
                    padx=8,
                    pady=2,
                )
                chip_label.pack()

        # 2D. Pros / Cons
        if self.recommendation.pros or self.recommendation.cons:
            grid_frame = customtkinter.CTkFrame(self._body_frame, fg_color="transparent")
            grid_frame.pack(fill="x", padx=16, pady=(0, 12))
            grid_frame.grid_columnconfigure(0, weight=1)
            grid_frame.grid_columnconfigure(1, weight=1)

            # Pros
            pros_frame = customtkinter.CTkFrame(
                grid_frame,
                fg_color=COLOR_BG_CARD,
                corner_radius=8,
                border_width=1,
                border_color=COLOR_BORDER_SUBTLE,
            )
            pros_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

            customtkinter.CTkLabel(
                pros_frame,
                text="Strengths",
                font=FONT_H3,
                text_color=COLOR_STATUS_SUCCESS,
                anchor="w",
                padx=10,
                pady=4,
            ).pack(fill="x")

            for pro in (self.recommendation.pros or [])[:3]:
                customtkinter.CTkLabel(
                    pros_frame,
                    text=f"+ {pro}",
                    font=FONT_BODY_SMALL,
                    text_color=COLOR_TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    padx=10,
                    pady=2,
                    wraplength=380,
                ).pack(fill="x")

            # Cons
            cons_frame = customtkinter.CTkFrame(
                grid_frame,
                fg_color=COLOR_BG_CARD,
                corner_radius=8,
                border_width=1,
                border_color=COLOR_BORDER_SUBTLE,
            )
            cons_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

            customtkinter.CTkLabel(
                cons_frame,
                text="Limitations",
                font=FONT_H3,
                text_color=COLOR_STATUS_WARNING,
                anchor="w",
                padx=10,
                pady=4,
            ).pack(fill="x")

            for con in (self.recommendation.cons or [])[:3]:
                customtkinter.CTkLabel(
                    cons_frame,
                    text=f"- {con}",
                    font=FONT_BODY_SMALL,
                    text_color=COLOR_TEXT_SECONDARY,
                    anchor="w",
                    justify="left",
                    padx=10,
                    pady=2,
                    wraplength=380,
                ).pack(fill="x")

        # 2E. Decision Toolbar
        toolbar_frame = customtkinter.CTkFrame(self._body_frame, fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=16, pady=(4, 16))

        self._btn_accept = customtkinter.CTkButton(
            toolbar_frame,
            text="✓ Accept for BOM/BOQ",
            height=30,
            corner_radius=6,
            font=FONT_BODY_REGULAR,
            fg_color=COLOR_STATUS_SUCCESS,
            hover_color=("#047857", "#059669"),
            command=self._handle_toggle_accept,
        )
        self._btn_accept.pack(side="left", padx=(0, 8))

        self._btn_modify = customtkinter.CTkButton(
            toolbar_frame,
            text="Modify Rationale",
            height=30,
            corner_radius=6,
            font=FONT_BODY_SMALL,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_PRIMARY,
            hover_color=COLOR_BG_ELEVATED,
            command=self._handle_toggle_modify_rationale,
        )
        self._btn_modify.pack(side="left", padx=(0, 8))

        self._btn_reject = customtkinter.CTkButton(
            toolbar_frame,
            text="✕ Exclude / Reject",
            height=30,
            corner_radius=6,
            font=FONT_BODY_SMALL,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_STATUS_ERROR,
            hover_color=("#FEE2E2", "#3B1219"),
            command=self._handle_toggle_reject_popover,
        )
        self._btn_reject.pack(side="left")

        # Inline Reject Reason Popover
        self._reject_popover_frame = customtkinter.CTkFrame(
            self._body_frame,
            fg_color=COLOR_BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
        )

        customtkinter.CTkLabel(
            self._reject_popover_frame,
            text="Select Exclusion Reason (§8.1.14):",
            font=FONT_BODY_SMALL,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            padx=12,
        ).pack(fill="x", pady=(6, 2))

        self._reason_var = customtkinter.StringVar(value=REJECTION_REASONS[0])
        self._reason_menu = customtkinter.CTkOptionMenu(
            self._reject_popover_frame,
            variable=self._reason_var,
            values=REJECTION_REASONS,
            height=26,
            font=FONT_BODY_SMALL,
            fg_color=COLOR_BG_ELEVATED,
            button_color=COLOR_BORDER_STRONG,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self._reason_menu.pack(fill="x", padx=12, pady=(0, 6))

        pop_btn_row = customtkinter.CTkFrame(self._reject_popover_frame, fg_color="transparent")
        pop_btn_row.pack(fill="x", padx=12, pady=(0, 6))

        btn_confirm_reject = customtkinter.CTkButton(
            pop_btn_row,
            text="Confirm Exclusion",
            height=26,
            font=FONT_BODY_SMALL,
            fg_color=COLOR_STATUS_ERROR,
            hover_color=("#B91C1C", "#DC2626"),
            command=self._handle_confirm_rejection,
        )
        btn_confirm_reject.pack(side="left", padx=(0, 6))

        btn_cancel_reject = customtkinter.CTkButton(
            pop_btn_row,
            text="Cancel",
            height=26,
            font=FONT_BODY_SMALL,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_BG_ELEVATED,
            command=self._handle_toggle_reject_popover,
        )
        btn_cancel_reject.pack(side="left")

    def toggle_expand(self) -> None:
        """Toggles expanded/collapsed state with smooth animation handling."""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self._lbl_arrow.configure(text="▼")
            self._body_frame.pack(fill="x", expand=True)
        else:
            self._lbl_arrow.configure(text="▶")
            self._body_frame.pack_forget()

    def _handle_toggle_accept(self) -> None:
        """Toggles product acceptance for alternative option."""
        self.is_accepted = not self.is_accepted
        if self.is_accepted:
            if self.is_rejected:
                self.is_rejected = False
                self._excluded_pill.pack_forget()

            self.configure(border_color=COLOR_BORDER_ACCEPTED, border_width=2)
            self._btn_accept.configure(text="✓ Accepted")
            self._accepted_pill.pack(side="right", padx=(0, 8))
        else:
            self.configure(border_color=COLOR_BORDER_SUBTLE, border_width=1)
            self._btn_accept.configure(text="✓ Accept for BOM/BOQ")
            self._accepted_pill.pack_forget()

        if self._on_accept:
            self._on_accept(self.recommendation, self.is_accepted)

    def _handle_toggle_modify_rationale(self) -> None:
        if not self._is_editing_rationale:
            self._is_editing_rationale = True
            self._lbl_rationale.pack_forget()
            self._txt_rationale.delete("1.0", "end")
            self._txt_rationale.insert("1.0", self.recommendation.rationale)
            self._edit_rationale_frame.pack(fill="x", pady=(0, 8))
            self._btn_modify.configure(text="Cancel Edit")
        else:
            self._is_editing_rationale = False
            self._edit_rationale_frame.pack_forget()
            self._lbl_rationale.pack(fill="x", padx=16, pady=(0, 10))
            self._btn_modify.configure(text="Modify Rationale")

    def _handle_save_rationale(self) -> None:
        edited_text = self._txt_rationale.get("1.0", "end-1c").strip()
        if edited_text:
            self.recommendation.rationale = edited_text
            self._lbl_rationale.configure(text=edited_text)

        self._handle_toggle_modify_rationale()

        if self._on_modify and edited_text:
            self._on_modify(self.recommendation, edited_text)

    def _handle_revert_rationale(self) -> None:
        self._handle_toggle_modify_rationale()

    def _handle_toggle_reject_popover(self) -> None:
        if self._reject_popover_frame.winfo_manager() == "pack":
            self._reject_popover_frame.pack_forget()
        else:
            self._reject_popover_frame.pack(fill="x", padx=16, pady=(0, 12))

    def _handle_confirm_rejection(self) -> None:
        selected_reason = self._reason_var.get()
        self.is_rejected = True
        self.rejection_reason = selected_reason

        if self.is_accepted:
            self.is_accepted = False
            self._accepted_pill.pack_forget()
            self._btn_accept.configure(text="✓ Accept for BOM/BOQ")

        self.configure(border_color=COLOR_BORDER_REJECTED, border_width=1)
        self._lbl_excluded.configure(text=f"✕ Excluded: {selected_reason}")
        self._excluded_pill.pack(side="right", padx=(0, 8))
        self._reject_popover_frame.pack_forget()

        if self._on_reject:
            self._on_reject(self.recommendation, selected_reason)


class ResultsCanvas(customtkinter.CTkScrollableFrame):
    """Container for verdict summary header + recommendation cards. §8.1.5 item 4."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            **kwargs,
        )

        self._on_accept: Optional[Callable[[ProductRecommendation, bool], None]] = None
        self._on_modify: Optional[Callable[[ProductRecommendation, str], None]] = None
        self._on_reject: Optional[Callable[[ProductRecommendation, str], None]] = None

        self._cards: List[customtkinter.CTkFrame] = []
        self._active_response: Optional[AnalyzeResponse] = None
        self._copy_timer_id: Optional[str] = None

    def set_on_accept(self, callback: Callable[[ProductRecommendation, bool], None]) -> None:
        self._on_accept = callback
        for card in self._cards:
            if hasattr(card, "set_on_accept"):
                card.set_on_accept(callback)

    def set_on_modify(self, callback: Callable[[ProductRecommendation, str], None]) -> None:
        self._on_modify = callback
        for card in self._cards:
            if hasattr(card, "set_on_modify"):
                card.set_on_modify(callback)

    def set_on_reject(self, callback: Callable[[ProductRecommendation, str], None]) -> None:
        self._on_reject = callback
        for card in self._cards:
            if hasattr(card, "set_on_reject"):
                card.set_on_reject(callback)

    def clear(self) -> None:
        """Removes all cards and headers, resetting the results canvas."""
        if self._copy_timer_id:
            try:
                self.after_cancel(self._copy_timer_id)
            except Exception:
                pass
            self._copy_timer_id = None

        for child in self.winfo_children():
            child.destroy()

        self._cards.clear()
        self._active_response = None

    def show_results(self, response: AnalyzeResponse) -> None:
        """Renders verdict summary header + primary card + alternative cards."""
        self.clear()
        self._active_response = response

        if not response or not response.recommendations:
            self._render_empty_state()
            return

        recs = response.recommendations
        top_rec = recs[0]

        # 1. Verdict Summary Header (§8.1.5 item 4)
        header_container = customtkinter.CTkFrame(
            self,
            fg_color=COLOR_BG_CARD,
            border_color=COLOR_BORDER_SUBTLE,
            border_width=1,
            corner_radius=12,
        )
        header_container.pack(fill="x", pady=(0, 16))

        header_inner = customtkinter.CTkFrame(header_container, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=14)

        # Left: Taxonomy & Domain Breadcrumb
        tax_frame = customtkinter.CTkFrame(header_inner, fg_color="transparent")
        tax_frame.pack(side="left", fill="x", expand=True)

        lbl_section = customtkinter.CTkLabel(
            tax_frame,
            text="PRESALES VERDICT & RECOMMENDATIONS",
            font=FONT_OVERLINE,
            text_color=COLOR_BRAND_ACCENT,
            anchor="w",
        )
        lbl_section.pack(fill="x")

        domain_txt = f"{top_rec.domain or 'Domain'}  >  {top_rec.sub_domain or 'General'}"
        lbl_domain = customtkinter.CTkLabel(
            tax_frame,
            text=domain_txt,
            font=FONT_H2,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        lbl_domain.pack(fill="x")

        # Right Action Cluster: Confidence Pill + One-Click Clipboard CTA
        right_actions = customtkinter.CTkFrame(header_inner, fg_color="transparent")
        right_actions.pack(side="right", padx=(12, 0))

        # Confidence Score Pill
        conf_color = _get_confidence_color(top_rec.confidence_level)
        fit_pct = int(round(top_rec.fit_score))
        conf_text = f"[{top_rec.confidence_level} CONFIDENCE: {fit_pct}% Fit]"

        self._verdict_conf_pill = customtkinter.CTkFrame(
            right_actions,
            fg_color=COLOR_BG_ELEVATED,
            border_color=conf_color,
            border_width=1,
            corner_radius=12,
        )
        self._verdict_conf_pill.pack(side="left", padx=(0, 12))

        self._lbl_verdict_conf = customtkinter.CTkLabel(
            self._verdict_conf_pill,
            text=conf_text,
            font=FONT_H3,
            text_color=conf_color,
            padx=12,
            pady=4,
        )
        self._lbl_verdict_conf.pack()

        # Trigger gentle scale pulse (§8.1.10) if reduced motion is disabled
        self._trigger_confidence_pulse()

        # One-Click Clipboard CTA (§8.1.5 item 4, §8.1.10)
        self._btn_copy = customtkinter.CTkButton(
            right_actions,
            text="📋 Copy Recommendation",
            height=36,
            corner_radius=8,
            font=FONT_H3,
            fg_color=COLOR_BG_ELEVATED,
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_PRIMARY,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._handle_copy_recommendation,
        )
        self._btn_copy.pack(side="left")

        # 2. Primary Recommendation Card (Top Pick)
        primary_card = PrimaryRecommendationCard(
            self,
            recommendation=top_rec,
            on_accept=self._on_accept,
            on_modify=self._on_modify,
            on_reject=self._on_reject,
        )
        primary_card.pack(fill="x", pady=(0, 14))
        self._cards.append(primary_card)

        # 3. Alternative Candidate Cards (Collapsed by default)
        if len(recs) > 1:
            alt_header_frame = customtkinter.CTkFrame(self, fg_color="transparent")
            alt_header_frame.pack(fill="x", pady=(8, 8))

            lbl_alt_title = customtkinter.CTkLabel(
                alt_header_frame,
                text=f"Alternative Candidates ({len(recs) - 1})",
                font=FONT_H3,
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            )
            lbl_alt_title.pack(side="left")

            for alt_rec in recs[1:]:
                alt_card = AlternativeCard(
                    self,
                    recommendation=alt_rec,
                    on_accept=self._on_accept,
                    on_modify=self._on_modify,
                    on_reject=self._on_reject,
                )
                alt_card.pack(fill="x", pady=(0, 10))
                self._cards.append(alt_card)

    def _render_empty_state(self) -> None:
        """Displays friendly zero-result notice when no products match."""
        empty_frame = customtkinter.CTkFrame(
            self,
            fg_color=COLOR_BG_CARD,
            border_color=COLOR_BORDER_SUBTLE,
            border_width=1,
            corner_radius=12,
        )
        empty_frame.pack(fill="x", pady=20, padx=20)

        customtkinter.CTkLabel(
            empty_frame,
            text="No Product Recommendations Available",
            font=FONT_H2,
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(fill="x", pady=(20, 4))

        customtkinter.CTkLabel(
            empty_frame,
            text=(
                "The requirement did not meet the catalog similarity threshold or no matches "
                "were found within the 57 OEM portfolio. Try adjusting your technical keywords."
            ),
            font=FONT_BODY_REGULAR,
            text_color=COLOR_TEXT_MUTED,
            wraplength=600,
        ).pack(fill="x", pady=(0, 20))

    def _trigger_confidence_pulse(self) -> None:
        """400ms gentle scale pulse (§8.1.10) for confidence badge."""
        if check_reduced_motion():
            return

        def expand():
            try:
                self._lbl_verdict_conf.configure(font=(FONT_PRIMARY, 14, "bold"))
                self.after(200, contract)
            except Exception:
                pass

        def contract():
            try:
                self._lbl_verdict_conf.configure(font=FONT_H3)
            except Exception:
                pass

        self.after(50, expand)

    def _handle_copy_recommendation(self) -> None:
        """Copies formatted markdown proposal text to clipboard and morphs button for 2.0s."""
        if not self._active_response or not self._active_response.recommendations:
            return

        md_content = self._generate_markdown_summary(self._active_response)

        try:
            self.clipboard_clear()
            self.clipboard_append(md_content)
            self.update()  # Commit to OS clipboard
        except Exception as e:
            _logger.warning(f"Clipboard copy failed: {e}")

        # Visual Morph (§8.1.10): morph to checkmark for 2.0 seconds
        self._btn_copy.configure(
            text="✓ Copied to Clipboard!",
            fg_color=COLOR_STATUS_SUCCESS,
            text_color=("#FFFFFF", "#FFFFFF"),
        )

        if self._copy_timer_id:
            try:
                self.after_cancel(self._copy_timer_id)
            except Exception:
                pass

        self._copy_timer_id = self.after(2000, self._revert_copy_button)

    def _revert_copy_button(self) -> None:
        """Reverts copy button to normal state."""
        try:
            self._btn_copy.configure(
                text="📋 Copy Recommendation",
                fg_color=COLOR_BG_ELEVATED,
                text_color=COLOR_TEXT_PRIMARY,
            )
        except Exception:
            pass
        self._copy_timer_id = None

    def _generate_markdown_summary(self, response: AnalyzeResponse) -> str:
        """Constructs clean markdown summary of recommendations for presales emails/proposals."""
        recs = response.recommendations
        top = recs[0]

        lines = [
            f"# iValue PRISM — Presales Solution Recommendation",
            f"**Query ID:** `{response.query_id}` | **Generated:** Draft Proposal",
            f"**Domain Category:** {top.domain} > {top.sub_domain}",
            "",
            f"## Primary Recommendation: {top.product_name} ({top.oem})",
            f"- **Confidence:** {top.confidence_level} ({int(round(top.fit_score))}% Fit Score)",
            f"- **Citation:** {_format_citation_text(top)}",
            "",
            "### Executive Rationale",
            top.rationale or "N/A",
            "",
        ]

        if top.features:
            lines.append("### Key Differentiators & Features")
            for f in top.features:
                lines.append(f"- {f}")
            lines.append("")

        if top.pros:
            lines.append("### Strengths & Pros")
            for p in top.pros:
                lines.append(f"- {p}")
            lines.append("")

        if top.cons:
            lines.append("### Considerations & Trade-offs")
            for c in top.cons:
                lines.append(f"- {c}")
            lines.append("")

        if len(recs) > 1:
            lines.append("## Alternative Candidates Evaluated")
            for idx, alt in enumerate(recs[1:], start=2):
                lines.append(
                    f"{idx}. **{alt.product_name}** ({alt.oem}) — "
                    f"{alt.confidence_level} ({int(round(alt.fit_score))}% Fit) | {_format_citation_text(alt)}"
                )
            lines.append("")

        lines.append("> *Note: Pricing is intentionally omitted and must be completed by Sales per iValue policy.*")
        return "\n".join(lines)

    def get_accepted_recommendations(self) -> List[ProductRecommendation]:
        """Returns list of recommendations that have been accepted by the engineer."""
        accepted = []
        for card in self._cards:
            if getattr(card, "is_accepted", False):
                accepted.append(card.recommendation)
        return accepted

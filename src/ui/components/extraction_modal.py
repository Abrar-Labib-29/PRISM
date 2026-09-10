"""
iValue PRISM — Extracted Document Preview & Confirmation Modal
SRS References: §8.1.12, §FR-13
Implementation Plan: TASK-P4.3

This module implements the interactive review and edit modal (DocumentPreviewModal)
rendered before the retrieval pipeline begins when documents (.pdf, .docx, .txt)
are ingested.

Features:
  - 760×540px modal dialog centered over parent window
  - Modal grab (blocks background interaction until confirmed or discarded)
  - Header: "Extracted Requirement Review" with [✕] close button
  - Subtitle displaying source filename and file size in KB
  - Warning banner for scanned/image PDFs or encoding fallbacks
  - 360px editable CTkTextbox with Segoe UI 11pt
  - Live character and token metric counter updated dynamically on user edits
  - Action footer: "✕ Discard & Re-upload" (ghost) and "✓ Confirm & Analyze Requirement" (accent)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import customtkinter

from src.core.ingestion import ExtractionResult
from src.utils.config import estimate_tokens

_logger = logging.getLogger("prism.ui.extraction_modal")

# Typography Scale (§8.1.3)
FONT_PRIMARY = "Segoe UI"
FONT_H2 = (FONT_PRIMARY, 15, "bold")
FONT_H3 = (FONT_PRIMARY, 13, "bold")
FONT_BODY_REGULAR = (FONT_PRIMARY, 11, "normal")
FONT_BODY_SMALL = (FONT_PRIMARY, 10, "normal")
FONT_CAPTION = (FONT_PRIMARY, 9, "normal")

# Colors (§8.1.2)
COLOR_BG_MODAL = ("#FFFFFF", "#131F37")
COLOR_BG_INPUT = ("#F8FAFC", "#0D1527")
COLOR_BG_ELEVATED = ("#F1F5F9", "#1E293B")
COLOR_BORDER_SUBTLE = ("#CBD5E1", "#1E293B")
COLOR_BORDER_ACCENT = ("#0284C7", "#38BDF8")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_SECONDARY = ("#475569", "#94A3B8")
COLOR_TEXT_MUTED = ("#64748B", "#64748B")
COLOR_BRAND_ACCENT = ("#0284C7", "#0EA5E9")
COLOR_ACCENT_HOVER = ("#0369A1", "#38BDF8")
COLOR_STATUS_WARNING = ("#D97706", "#F59E0B")
COLOR_STATUS_ERROR = ("#DC2626", "#EF4444")


class DocumentPreviewModal(customtkinter.CTkToplevel):
    """Extracted text review & edit modal. §8.1.12."""

    def __init__(
        self,
        parent,
        extraction_result: ExtractionResult,
        on_confirm: Optional[Callable[[str], None]] = None,
        on_discard: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.parent = parent
        self.extraction_result = extraction_result
        self._on_confirm = on_confirm
        self._on_discard = on_discard

        # Window configuration (§8.1.12)
        self.title("Extracted Requirement Review")
        self.geometry("760x540")
        self.minsize(700, 480)
        self.configure(fg_color=COLOR_BG_MODAL)

        # Center over parent
        self._center_over_parent()

        # Modal behavior: block parent interaction
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._handle_discard)

        self._build_ui()

        # Grab focus and make modal
        try:
            self.grab_set()
            self.focus_set()
        except Exception as e:
            _logger.debug(f"grab_set failed in headless/test environment: {e}")

    def set_on_confirm(self, callback: Callable[[str], None]) -> None:
        """Sets the confirmation callback which receives the edited text."""
        self._on_confirm = callback

    def set_on_discard(self, callback: Callable[[], None]) -> None:
        """Sets the discard callback."""
        self._on_discard = callback

    def _center_over_parent(self) -> None:
        """Calculates coordinates to center 760×540 modal over the parent window."""
        try:
            self.parent.update_idletasks()
            p_x = self.parent.winfo_rootx()
            p_y = self.parent.winfo_rooty()
            p_w = self.parent.winfo_width()
            p_h = self.parent.winfo_height()

            modal_w = 760
            modal_h = 540

            pos_x = p_x + max(0, (p_w - modal_w) // 2)
            pos_y = p_y + max(0, (p_h - modal_h) // 2)
            self.geometry(f"{modal_w}x{modal_h}+{pos_x}+{pos_y}")
        except Exception:
            self.geometry("760x540")

    def _build_ui(self) -> None:
        """Constructs modal header, review canvas, metrics, and action footer."""
        # 1. Top Header Chrome
        header_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(16, 4))

        title_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)

        lbl_title = customtkinter.CTkLabel(
            title_frame,
            text="Extracted Requirement Review",
            font=FONT_H2,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x")

        # Subtitle
        filename = self.extraction_result.source_filename or "document"
        filesize_kb = self.extraction_result.file_size_kb or 0.0
        subtitle_text = (
            f"Extracted from {filename} (Size: {filesize_kb:.1f} KB). "
            f"Review and edit the parsed text before running catalog matching."
        )

        lbl_subtitle = customtkinter.CTkLabel(
            title_frame,
            text=subtitle_text,
            font=FONT_BODY_SMALL,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        lbl_subtitle.pack(fill="x", pady=(2, 0))

        # Close button [✕]
        btn_close = customtkinter.CTkButton(
            header_frame,
            text="✕",
            width=28,
            height=28,
            font=FONT_BODY_SMALL,
            fg_color="transparent",
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_BG_ELEVATED,
            command=self._handle_discard,
        )
        btn_close.pack(side="right")

        # Warning banner (if file had warnings e.g. scanned PDF or encoding fallback)
        if self.extraction_result.warning:
            warning_frame = customtkinter.CTkFrame(
                self,
                fg_color=COLOR_BG_ELEVATED,
                border_color=COLOR_STATUS_WARNING,
                border_width=1,
                corner_radius=6,
            )
            warning_frame.pack(fill="x", padx=20, pady=(4, 6))

            lbl_warn = customtkinter.CTkLabel(
                warning_frame,
                text=f"⚠ Warning: {self.extraction_result.warning}",
                font=FONT_CAPTION,
                text_color=COLOR_STATUS_WARNING,
                anchor="w",
                padx=10,
            )
            lbl_warn.pack(fill="x", pady=4)

        # 2. Interactive Review Canvas (CTkTextbox, height 360px, full width - 32px padding)
        self._txt_canvas = customtkinter.CTkTextbox(
            self,
            height=360,
            font=FONT_BODY_REGULAR,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            fg_color=COLOR_BG_INPUT,
            text_color=COLOR_TEXT_PRIMARY,
            wrap="word",
        )
        self._txt_canvas.pack(fill="both", expand=True, padx=20, pady=(6, 12))

        # Insert initial extracted text
        initial_text = self.extraction_result.text or ""
        self._txt_canvas.insert("1.0", initial_text)
        self._txt_canvas.bind("<KeyRelease>", self._update_metrics)

        # 3. Footer Action Bar & Live Metrics (§8.1.12)
        footer_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", padx=20, pady=(0, 16))

        # Live Metrics on the left
        self._lbl_metrics = customtkinter.CTkLabel(
            footer_frame,
            text="",
            font=FONT_BODY_SMALL,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        self._lbl_metrics.pack(side="left")
        self._update_metrics()

        # Action Buttons on the right
        btn_container = customtkinter.CTkFrame(footer_frame, fg_color="transparent")
        btn_container.pack(side="right")

        # "✕ Discard & Re-upload" (Ghost style, 36px height)
        self._btn_discard = customtkinter.CTkButton(
            btn_container,
            text="✕ Discard & Re-upload",
            height=36,
            font=FONT_BODY_REGULAR,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_BG_ELEVATED,
            command=self._handle_discard,
        )
        self._btn_discard.pack(side="left", padx=(0, 10))

        # "✓ Confirm & Analyze Requirement" (Accent style, 36px height)
        self._btn_confirm = customtkinter.CTkButton(
            btn_container,
            text="✓ Confirm & Analyze Requirement",
            height=36,
            font=FONT_H3,
            fg_color=COLOR_BRAND_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=("#FFFFFF", "#FFFFFF"),
            command=self._handle_confirm,
        )
        self._btn_confirm.pack(side="left")

    def _update_metrics(self, event: Optional[Any] = None) -> None:
        """Updates live character and token metric counter dynamically on typing."""
        current_text = self._txt_canvas.get("1.0", "end-1c")
        chars = len(current_text)
        tokens = estimate_tokens(current_text)
        self._lbl_metrics.configure(
            text=f"Extracted Characters: {chars:,}  |  Estimated Tokens: ~{tokens:,}"
        )

    def get_text(self) -> str:
        """Returns the current text in the review canvas."""
        return self._txt_canvas.get("1.0", "end-1c").strip()

    def _handle_confirm(self) -> None:
        """Commits the edited text, dispatches callback, and closes the modal."""
        edited_text = self.get_text()
        try:
            self.grab_release()
        except Exception:
            pass

        self.destroy()

        if self._on_confirm:
            self._on_confirm(edited_text)

    def _handle_discard(self) -> None:
        """Aborts extraction without action and closes the modal."""
        try:
            self.grab_release()
        except Exception:
            pass

        self.destroy()

        if self._on_discard:
            self._on_discard()

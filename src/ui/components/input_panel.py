"""
iValue PRISM — Customer Requirement & RFP Input Panel
SRS References: §6.9, §8.1.4, §8.1.5 item 2, §10.1, §10.7, §FR-1, §FR-1a, §FR-14
Implementation Plan: TASK-P3.5

This module implements the requirement input component (RequirementInputPanel) for iValue PRISM.
Features:
  - Header area with section title and native Windows file loader button
  - Multiline input textbox (140px height) with placeholder support and focus glow border
  - Live character & token estimation gauge with 3-tier color transitions (Green/Amber/Crimson)
  - Primary "Analyze Requirement" action button (42px) and conditional "Cancel" button
  - Keyboard accelerators: Ctrl+Enter (Analyze), Ctrl+O (Load RFP), Escape (Cancel)
  - Input validation for empty input (NEG-01, NEG-02), short text warning (NEG-03), and length limits (NEG-05)
"""

from __future__ import annotations

import logging
import os
import pathlib
import sys
import tkinter as tk
from tkinter import filedialog
from typing import Any, Callable, Dict, Optional, Tuple

import customtkinter

from src.utils.config import (
    MAX_INPUT_CHARS,
    NUM_CTX,
    SHORT_INPUT_THRESHOLD,
    estimate_tokens,
)

_logger = logging.getLogger("prism.ui.input_panel")

# UI Constants (§8.1.5 item 2)
TEXTBOX_HEIGHT = 140
CORNER_RADIUS = 8
PLACEHOLDER_TEXT = (
    "Type customer technical requirement, copy-paste RFP excerpt, or load document..."
)

# Brand Colors (§8.1.2)
COLOR_BG_CARD = ("#FFFFFF", "#131F37")
COLOR_BG_INPUT = ("#FFFFFF", "#0D1527")
COLOR_BORDER_SUBTLE = ("#CBD5E1", "#1E293B")
COLOR_BORDER_ACCENT = ("#0284C7", "#38BDF8")
COLOR_BORDER_ERROR = ("#DC2626", "#EF4444")
COLOR_BORDER_WARN = ("#D97706", "#F59E0B")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_SECONDARY = ("#475569", "#94A3B8")
COLOR_TEXT_MUTED = ("#64748B", "#64748B")
COLOR_BRAND_ACCENT = ("#0284C7", "#0EA5E9")
COLOR_ACCENT_HOVER = ("#0369A1", "#38BDF8")
COLOR_STATUS_ONLINE = ("#059669", "#10B981")  # Green (<8,000 chars)
COLOR_STATUS_WARNING = ("#D97706", "#F59E0B")  # Amber (8,000-10,000 chars)
COLOR_STATUS_ERROR = ("#DC2626", "#EF4444")  # Crimson (>10,000 chars)
COLOR_CANCEL_BG = ("#DC2626", "#EF4444")
COLOR_CANCEL_HOVER = ("#B91C1C", "#DC2626")


class RequirementInputPanel(customtkinter.CTkFrame):
    """
    Customer requirement input area (§8.1.5 item 2).
    Manages user input, document picker trigger, live token estimation, and action dispatch.
    """

    def __init__(self, parent: Any, **kwargs: Any) -> None:
        kwargs.setdefault("fg_color", COLOR_BG_CARD)
        kwargs.setdefault("border_color", COLOR_BORDER_SUBTLE)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("corner_radius", 12)
        super().__init__(parent, **kwargs)

        # State flags
        self._is_analyzing = False
        self._has_placeholder = True

        # Action callbacks
        self._on_analyze_callback: Optional[Callable[[str], None]] = None
        self._on_cancel_callback: Optional[Callable[[], None]] = None
        self._on_file_load_callback: Optional[Callable[[str], None]] = None

        self._build_ui()
        self._bind_keyboard_shortcuts()

    # =========================================================================
    # UI Construction
    # =========================================================================

    def _build_ui(self) -> None:
        """Constructs header, textbox, gauge bar, and action buttons."""
        self._content_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self._content_container.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Header Area: Title & Load RFP Button
        header_row = customtkinter.CTkFrame(self._content_container, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))

        title_lbl = customtkinter.CTkLabel(
            header_row,
            text="Customer Requirement & RFP Input",
            font=customtkinter.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        self._load_file_btn = customtkinter.CTkButton(
            header_row,
            text="📁  Load RFP (.pdf, .docx, .txt)",
            height=32,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER_ACCENT,
            fg_color="transparent",
            text_color=COLOR_TEXT_PRIMARY,
            hover_color=COLOR_BORDER_SUBTLE,
            font=customtkinter.CTkFont(family="Segoe UI", size=11, weight="normal"),
            command=self._on_load_file_clicked,
        )
        self._load_file_btn.pack(side="right")

        # 2. Input Textbox with Focus Border Frame
        self._textbox_border_frame = customtkinter.CTkFrame(
            self._content_container,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            corner_radius=CORNER_RADIUS,
        )
        self._textbox_border_frame.pack(fill="x", pady=(0, 8))

        self._textbox = customtkinter.CTkTextbox(
            self._textbox_border_frame,
            height=TEXTBOX_HEIGHT,
            corner_radius=CORNER_RADIUS,
            border_width=0,
            fg_color=COLOR_BG_INPUT,
            text_color=COLOR_TEXT_MUTED,
            font=customtkinter.CTkFont(family="Segoe UI", size=12, weight="normal"),
            wrap="word",
        )
        self._textbox.pack(fill="both", expand=True, padx=2, pady=2)

        # Insert initial placeholder
        self._textbox.insert("1.0", PLACEHOLDER_TEXT)
        self._has_placeholder = True

        # Textbox Focus & Input Events
        self._textbox.bind("<FocusIn>", self._on_focus_in)
        self._textbox.bind("<FocusOut>", self._on_focus_out)
        self._textbox.bind("<KeyRelease>", self._on_key_release)

        # 3. Footer Metadata Bar & Validation Feedback
        footer_row = customtkinter.CTkFrame(self._content_container, fg_color="transparent")
        footer_row.pack(fill="x", pady=(0, 12))

        # Live Token/Character Gauge Label (§8.1.5 item 2)
        self._gauge_label = customtkinter.CTkLabel(
            footer_row,
            text="Tokens: ~0 / 2,048   |   Characters: 0 / 10,000",
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="normal"),
            text_color=COLOR_STATUS_ONLINE,
            anchor="w",
        )
        self._gauge_label.pack(side="left")

        # Inline validation feedback message
        self._feedback_label = customtkinter.CTkLabel(
            footer_row,
            text="",
            font=customtkinter.CTkFont(family="Segoe UI", size=10, slant="italic"),
            text_color=COLOR_STATUS_ERROR,
            anchor="e",
        )
        self._feedback_label.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # 4. Action Buttons Area (Analyze vs Cancel)
        btn_row = customtkinter.CTkFrame(self._content_container, fg_color="transparent")
        btn_row.pack(fill="x")

        self._analyze_btn = customtkinter.CTkButton(
            btn_row,
            text="🔍  Analyze Requirement",
            height=42,
            corner_radius=8,
            font=customtkinter.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLOR_BRAND_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._handle_analyze_click,
        )
        self._analyze_btn.pack(side="right", padx=(8, 0))

        self._cancel_btn = customtkinter.CTkButton(
            btn_row,
            text="✕  Cancel Analysis",
            height=42,
            corner_radius=8,
            font=customtkinter.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLOR_CANCEL_BG,
            hover_color=COLOR_CANCEL_HOVER,
            command=self._handle_cancel_click,
        )
        # Cancel button is hidden initially
        self._cancel_btn.pack_forget()

    # =========================================================================
    # Keyboard Accelerators (§6.9)
    # =========================================================================

    def _bind_keyboard_shortcuts(self) -> None:
        """
        Configures keyboard accelerators:
        - Ctrl+Enter: Analyze requirement
        - Ctrl+O: Open file dialog
        - Escape: Cancel in-progress analysis
        """
        # Inside textbox
        self._textbox.bind("<Control-Return>", self._handle_ctrl_enter)
        self._textbox.bind("<Control-KP_Enter>", self._handle_ctrl_enter)
        self._textbox.bind("<Control-o>", self._handle_ctrl_o)
        self._textbox.bind("<Control-O>", self._handle_ctrl_o)
        self._textbox.bind("<Escape>", self._handle_escape)

        # Window-level bindings via toplevel
        try:
            top = self.winfo_toplevel()
            if top:
                top.bind("<Control-o>", self._handle_ctrl_o, add="+")
                top.bind("<Control-O>", self._handle_ctrl_o, add="+")
                top.bind("<Escape>", self._handle_escape, add="+")
        except Exception:
            pass

    def _handle_ctrl_enter(self, event: Any) -> str:
        """Handles Ctrl+Enter accelerator."""
        if not self._is_analyzing:
            self._handle_analyze_click()
        return "break"

    def _handle_ctrl_o(self, event: Any) -> str:
        """Handles Ctrl+O accelerator to open document picker."""
        if not self._is_analyzing:
            self._on_load_file_clicked()
        return "break"

    def _handle_escape(self, event: Any) -> None:
        """Handles Escape key to cancel in-progress inference."""
        if self._is_analyzing:
            self._handle_cancel_click()

    # =========================================================================
    # Placeholder & Focus Handlers
    # =========================================================================

    def _on_focus_in(self, event: Any) -> None:
        """Activates focus glow border and clears placeholder if active."""
        # 2px glow border in brand_accent (§8.1.5 item 2)
        self._textbox_border_frame.configure(border_width=2, border_color=COLOR_BORDER_ACCENT)

        if self._has_placeholder:
            self._textbox.delete("1.0", "end")
            self._textbox.configure(text_color=COLOR_TEXT_PRIMARY)
            self._has_placeholder = False

    def _on_focus_out(self, event: Any) -> None:
        """Reverts focus border and restores placeholder if empty."""
        self._textbox_border_frame.configure(border_width=1, border_color=COLOR_BORDER_SUBTLE)

        raw_text = self._textbox.get("1.0", "end-1c").strip()
        if not raw_text:
            self._textbox.delete("1.0", "end")
            self._textbox.configure(text_color=COLOR_TEXT_MUTED)
            self._textbox.insert("1.0", PLACEHOLDER_TEXT)
            self._has_placeholder = True

    def _on_key_release(self, event: Any = None) -> None:
        """Updates live gauge as user types."""
        self._update_gauge()

    # =========================================================================
    # Live Token & Character Gauge (§8.1.5 item 2)
    # =========================================================================

    def _update_gauge(self, *args: Any) -> None:
        """
        Live character & token gauge calculation.
        Green (<8,000 chars) -> Amber (8,000-10,000) -> Crimson (>10,000).
        Uses estimate_tokens() heuristic from config.py.
        """
        text = self.get_text()
        char_count = len(text)
        token_count = estimate_tokens(text) if char_count > 0 else 0

        # Gauge color transitions
        if char_count < 8000:
            color = COLOR_STATUS_ONLINE
            self._clear_feedback()
        elif char_count <= MAX_INPUT_CHARS:
            color = COLOR_STATUS_WARNING
            self._set_feedback("Warning: Approaching 10,000 character context limit.", COLOR_STATUS_WARNING)
        else:
            color = COLOR_STATUS_ERROR
            self._set_feedback("Error: Exceeds 10,000 character maximum limit.", COLOR_STATUS_ERROR)

        self._gauge_label.configure(
            text=f"Tokens: ~{token_count:,} / {NUM_CTX:,}   |   Characters: {char_count:,} / {MAX_INPUT_CHARS:,}",
            text_color=color,
        )

    # =========================================================================
    # Public Accessors & Modifiers
    # =========================================================================

    def get_text(self) -> str:
        """Returns currently entered requirement text without placeholder."""
        if self._has_placeholder:
            return ""
        return self._textbox.get("1.0", "end-1c").strip()

    def set_text(self, text: str) -> None:
        """Sets textbox content programmatically, resetting placeholder state."""
        self._textbox.delete("1.0", "end")
        clean_text = text.strip()

        if clean_text:
            self._textbox.configure(text_color=COLOR_TEXT_PRIMARY)
            self._textbox.insert("1.0", clean_text)
            self._has_placeholder = False
        else:
            self._textbox.configure(text_color=COLOR_TEXT_MUTED)
            self._textbox.insert("1.0", PLACEHOLDER_TEXT)
            self._has_placeholder = True

        self._update_gauge()

    def clear(self) -> None:
        """Clears requirement text and resets to placeholder."""
        self.set_text("")
        self._clear_feedback()

    def set_analyzing(self, is_analyzing: bool) -> None:
        """
        Toggles UI between normal and analyzing states (§10.7):
        - When True: Disables Analyze button, presents Cancel button, disables textbox.
        - When False: Restores Analyze button, hides Cancel button, enables textbox.
        """
        self._is_analyzing = is_analyzing

        if is_analyzing:
            # Hide analyze button and show cancel button
            self._analyze_btn.pack_forget()
            self._cancel_btn.pack(side="right", padx=(8, 0))
            self._load_file_btn.configure(state="disabled")
            self._textbox.configure(state="disabled")
            self._set_feedback("Analysis in progress...", COLOR_STATUS_ONLINE)
        else:
            # Restore analyze button and hide cancel button
            self._cancel_btn.pack_forget()
            self._analyze_btn.pack(side="right", padx=(8, 0))
            self._analyze_btn.configure(state="normal")
            self._load_file_btn.configure(state="normal")
            self._textbox.configure(state="normal")
            self._clear_feedback()

    # =========================================================================
    # Callbacks & Action Dispatch
    # =========================================================================

    def set_on_analyze(self, callback: Callable[[str], None]) -> None:
        """Sets callback invoked with requirement text when user initiates analysis."""
        self._on_analyze_callback = callback

    def set_on_cancel(self, callback: Callable[[], None]) -> None:
        """Sets callback invoked when user cancels active analysis."""
        self._on_cancel_callback = callback

    def set_on_file_load(self, callback: Callable[[str], None]) -> None:
        """Sets callback invoked with selected file path when file is picked."""
        self._on_file_load_callback = callback

    def _handle_analyze_click(self) -> None:
        """
        Validates input and dispatches requirement to registered callback.
        Enforces NEG-01, NEG-02 (empty input) and warns on NEG-03 (short input).
        """
        text = self.get_text()

        # 1. Empty input validation (NEG-01, NEG-02)
        if not text:
            self._set_feedback("Please enter a customer requirement before analyzing.", COLOR_STATUS_ERROR)
            self._flash_border_error()
            return

        # 2. Short input advisory warning (NEG-03)
        if len(text) < SHORT_INPUT_THRESHOLD:
            self._set_feedback(
                "Notice: Requirement is very brief. Provide more technical context for best accuracy.",
                COLOR_STATUS_WARNING,
            )

        # 3. Maximum character limit check (NEG-05)
        if len(text) > MAX_INPUT_CHARS:
            self._set_feedback("Input exceeds 10,000 character limit. Please shorten requirement.", COLOR_STATUS_ERROR)
            self._flash_border_error()
            return

        if self._on_analyze_callback:
            self._on_analyze_callback(text)

    def _handle_cancel_click(self) -> None:
        """Dispatches cancellation to listener."""
        _logger.info("User clicked 'Cancel Analysis'.")
        if self._on_cancel_callback:
            self._on_cancel_callback()

    def _on_load_file_clicked(self) -> None:
        """
        Opens native Windows file picker for document extraction (§8.1.5 item 2, §FR-1a).
        Filters: .pdf, .docx, .txt
        """
        _logger.debug("Opening file dialog for RFP document...")
        file_path = filedialog.askopenfilename(
            title="Select Customer Requirement / RFP Document",
            filetypes=[
                ("All Supported Documents", "*.pdf;*.docx;*.txt"),
                ("PDF Documents (*.pdf)", "*.pdf"),
                ("Word Documents (*.docx)", "*.docx"),
                ("Text Files (*.txt)", "*.txt"),
                ("All Files (*.*)", "*.*"),
            ],
        )

        if file_path:
            _logger.info(f"User selected file: {file_path}")
            if self._on_file_load_callback:
                self._on_file_load_callback(file_path)

    def _set_feedback(self, msg: str, color: Any) -> None:
        """Displays inline validation feedback message."""
        self._feedback_label.configure(text=msg, text_color=color)

    def _clear_feedback(self) -> None:
        """Clears inline feedback message."""
        self._feedback_label.configure(text="")

    def _flash_border_error(self) -> None:
        """Temporarily highlights textbox border in error color."""
        self._textbox_border_frame.configure(border_width=2, border_color=COLOR_BORDER_ERROR)
        self.after(
            1500,
            lambda: self._textbox_border_frame.configure(border_width=1, border_color=COLOR_BORDER_SUBTLE),
        )

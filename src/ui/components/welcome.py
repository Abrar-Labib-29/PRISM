"""
iValue PRISM — Welcome & Zero-State Guidance Component
SRS References: §8.1.8, §8.1.10
Implementation Plan: TASK-P4.5

This module implements the welcome zero-state view (WelcomeView) displayed on the
main canvas when an engineer opens PRISM before submitting any query.

Features:
  - Centered hero illustration: 64×64px refractive PRISM crystalline emblem
  - Heading: "Ready to formulate your next presales recommendation" (H1 Bold)
  - Subheading: "Enter a customer RFP excerpt above, or click one of the quick-start templates below to test the pipeline:" (Body Regular)
  - 3 Interactive Quick-Start Cards (1-Click Auto-Fill) with exact text from §8.1.8:
      1. PAM Requirement (CyberArk / BeyondTrust)
      2. NGFW Requirement (Palo Alto / Fortinet / Check Point)
      3. SIEM & Log Analytics (Splunk / IBM QRadar)
  - Interactive hover states and click handlers dispatching selected requirement
    string to the input panel without auto-triggering analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter

_logger = logging.getLogger("prism.ui.welcome")

# Typography Scale (§8.1.3)
FONT_PRIMARY = "Segoe UI"
FONT_H1 = (FONT_PRIMARY, 18, "bold")
FONT_H3 = (FONT_PRIMARY, 13, "bold")
FONT_BODY_REGULAR = (FONT_PRIMARY, 11, "normal")
FONT_BODY_SMALL = (FONT_PRIMARY, 10, "normal")
FONT_OVERLINE = (FONT_PRIMARY, 9, "bold")

# Theme Palette (§8.1.2)
COLOR_BG_CARD = ("#FFFFFF", "#131F37")
COLOR_BG_ELEVATED = ("#F8FAFC", "#1E293B")
COLOR_BG_CARD_HOVER = ("#F1F5F9", "#24324D")
COLOR_BORDER_SUBTLE = ("#CBD5E1", "#1E293B")
COLOR_BORDER_ACCENT = ("#0284C7", "#38BDF8")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_SECONDARY = ("#475569", "#94A3B8")
COLOR_TEXT_MUTED = ("#64748B", "#64748B")
COLOR_BRAND_ACCENT = ("#0284C7", "#0EA5E9")
COLOR_BRAND_PURPLE = ("#4C1D95", "#7C3AED")

# Verbatim Starter Templates from SRS §8.1.8
QUICK_START_TEMPLATES = [
    {
        "id": "pam",
        "category": "PAM Requirement",
        "title": "Privileged Access Management (PAM)",
        "badge_color": COLOR_BRAND_PURPLE,
        "text": (
            "Customer requires a privileged access management solution for 300 servers "
            "with session recording, credential rotation, and SIEM integration."
        ),
    },
    {
        "id": "ngfw",
        "category": "NGFW Requirement",
        "title": "Next-Gen Enterprise Firewall (NGFW)",
        "badge_color": COLOR_BRAND_ACCENT,
        "text": (
            "Need next-generation enterprise firewall hardware with deep packet SSL inspection, "
            "10 Gbps throughput, and branch SD-WAN support."
        ),
    },
    {
        "id": "siem",
        "category": "SIEM & Log Analytics",
        "title": "SIEM & Centralized Log Analytics",
        "badge_color": ("#059669", "#10B981"),
        "text": (
            "Centralized security logging and analytics platform required to ingest 5,000 EPS "
            "with automated MITRE ATT&CK incident correlation."
        ),
    },
]


class WelcomeView(customtkinter.CTkFrame):
    """Zero-state guidance shown before first query. §8.1.8."""

    def __init__(
        self,
        parent,
        on_template_select: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            fg_color="transparent",
            **kwargs,
        )

        self._on_template_select = on_template_select
        self._cards: List[customtkinter.CTkFrame] = []

        self._build_ui()

    def set_on_template_select(self, callback: Callable[[str], None]) -> None:
        """Registers callback receiving template text string."""
        self._on_template_select = callback

    def _build_ui(self) -> None:
        """Constructs centered zero-state hero graphics and starter cards."""
        # Container constrained to max 880px width for optimal ergonomics
        container = customtkinter.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=24, pady=20)

        # 1. Centered Hero Graphic: 64×64 PRISM Refractive Emblem (§8.1.8)
        hero_frame = customtkinter.CTkFrame(
            container,
            width=64,
            height=64,
            corner_radius=16,
            fg_color=COLOR_BG_ELEVATED,
            border_color=COLOR_BORDER_SUBTLE,
            border_width=1,
        )
        hero_frame.pack(pady=(12, 12))
        hero_frame.pack_propagate(False)

        hero_glyph = customtkinter.CTkLabel(
            hero_frame,
            text="▲",
            font=customtkinter.CTkFont(family=FONT_PRIMARY, size=32, weight="bold"),
            text_color=COLOR_BRAND_ACCENT,
        )
        hero_glyph.pack(expand=True)

        # 2. Heading: "Ready to formulate your next presales recommendation" (H1 Bold)
        lbl_heading = customtkinter.CTkLabel(
            container,
            text="Ready to formulate your next presales recommendation",
            font=FONT_H1,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="center",
        )
        lbl_heading.pack(fill="x", pady=(0, 6))

        # 3. Subheading (§8.1.8)
        lbl_subheading = customtkinter.CTkLabel(
            container,
            text="Enter a customer RFP excerpt above, or click one of the quick-start templates below to test the pipeline:",
            font=FONT_BODY_REGULAR,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="center",
            wraplength=720,
        )
        lbl_subheading.pack(fill="x", pady=(0, 24))

        # 4. Quick-Start Cards Container
        cards_frame = customtkinter.CTkFrame(container, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 10))

        for item in QUICK_START_TEMPLATES:
            card = self._create_template_card(cards_frame, item)
            card.pack(fill="x", pady=(0, 12))
            self._cards.append(card)

    def _create_template_card(
        self,
        parent: customtkinter.CTkFrame,
        template_data: Dict[str, Any],
    ) -> customtkinter.CTkFrame:
        """Builds an interactive 1-click auto-fill starter card."""
        card_frame = customtkinter.CTkFrame(
            parent,
            fg_color=COLOR_BG_CARD,
            border_color=COLOR_BORDER_SUBTLE,
            border_width=1,
            corner_radius=10,
            cursor="hand2",
        )

        inner = customtkinter.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        # Top row: Category Badge + Arrow hint
        top_row = customtkinter.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 4))

        badge_frame = customtkinter.CTkFrame(
            top_row,
            fg_color=template_data["badge_color"],
            corner_radius=4,
        )
        badge_frame.pack(side="left")

        lbl_badge = customtkinter.CTkLabel(
            badge_frame,
            text=template_data["category"],
            font=FONT_OVERLINE,
            text_color=("#FFFFFF", "#FFFFFF"),
            padx=8,
            pady=1,
        )
        lbl_badge.pack()

        lbl_hint = customtkinter.CTkLabel(
            top_row,
            text="Click to load requirement ↗",
            font=FONT_BODY_SMALL,
            text_color=COLOR_BRAND_ACCENT,
        )
        lbl_hint.pack(side="right")

        # Title
        lbl_title = customtkinter.CTkLabel(
            inner,
            text=template_data["title"],
            font=FONT_H3,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(2, 4))

        # Text excerpt
        lbl_text = customtkinter.CTkLabel(
            inner,
            text=template_data["text"],
            font=FONT_BODY_REGULAR,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        lbl_text.pack(fill="x")

        # Bind click handlers to card and all child widgets
        template_text = template_data["text"]

        def _on_click(event=None):
            self._handle_card_click(template_text)

        def _on_enter(event=None):
            card_frame.configure(
                fg_color=COLOR_BG_CARD_HOVER,
                border_color=COLOR_BORDER_ACCENT,
            )

        def _on_leave(event=None):
            card_frame.configure(
                fg_color=COLOR_BG_CARD,
                border_color=COLOR_BORDER_SUBTLE,
            )

        # Attach hover and click to all descendants
        widgets_to_bind = [card_frame, inner, top_row, badge_frame, lbl_badge, lbl_hint, lbl_title, lbl_text]
        for w in widgets_to_bind:
            w.bind("<Button-1>", _on_click)
            w.bind("<Enter>", _on_enter)
            w.bind("<Leave>", _on_leave)

        return card_frame

    def _handle_card_click(self, template_text: str) -> None:
        """Dispatches template text to callback without triggering analysis."""
        if self._on_template_select:
            self._on_template_select(template_text)

    def show(self) -> None:
        """Makes the welcome guidance visible."""
        self.pack(fill="both", expand=True, padx=20, pady=20)

    def hide(self) -> None:
        """Hides the welcome guidance when results/stepper take over."""
        self.pack_forget()

"""
iValue PRISM — Token Stream Terminal & Pipeline Stepper
SRS References: §8.1.5 item 3, §8.1.10
Implementation Plan: TASK-P4.1

This module implements the inference progress visualization and streaming token terminal
(TokenStreamTerminal) for iValue PRISM.
Features:
  - Progress shimmer bar (CTkProgressBar, 6px height, 3px radius) with reduced-motion compliance
  - 3-stage checklist stepper ([✓], [⟳], [·], [✕]) with timing and status transitions
  - Live token streaming terminal: dark console (#0A0F1D) with Cascadia Mono 11pt,
    500ms blinking sky blue caret (#38BDF8), and smooth auto-scrolling
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import customtkinter

from src.utils.system_info import check_reduced_motion

_logger = logging.getLogger("prism.ui.stream_box")

# Colors (§8.1.2)
COLOR_BG_CARD = ("#FFFFFF", "#131F37")
COLOR_BORDER_SUBTLE = ("#CBD5E1", "#1E293B")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_SECONDARY = ("#475569", "#94A3B8")
COLOR_TEXT_MUTED = ("#64748B", "#64748B")
COLOR_BRAND_ACCENT = ("#0284C7", "#0EA5E9")
COLOR_STATUS_SUCCESS = ("#059669", "#10B981")
COLOR_STATUS_ERROR = ("#DC2626", "#EF4444")
COLOR_TERMINAL_BG = "#0A0F1D"
COLOR_TERMINAL_TEXT = "#F8FAFC"
COLOR_CARET = "#38BDF8"

# Stepper Phases (§8.1.5 item 3)
DEFAULT_PHASES: Dict[int, str] = {
    1: "Phase 1: Semantic Embedding & Catalog Scan (~2s)",
    2: "Phase 2: Metadata Filtering & Context Assembly (~0.5s)",
    3: "Phase 3: Phi-4-mini Grounded Generation (~35s)",
}


class TokenStreamTerminal(customtkinter.CTkFrame):
    """
    Live token streaming display and pipeline stepper (§8.1.5 item 3).
    Displays 3-phase execution checklist, animated shimmer bar, and real-time LLM token terminal.
    """

    def __init__(self, parent: Any, **kwargs: Any) -> None:
        kwargs.setdefault("fg_color", COLOR_BG_CARD)
        kwargs.setdefault("border_color", COLOR_BORDER_SUBTLE)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("corner_radius", 12)
        super().__init__(parent, **kwargs)

        self._full_text = ""
        self._is_streaming = False
        self._caret_visible = False
        self._caret_rendered = False
        self._caret_timer: Optional[str] = None
        self._step_labels: Dict[int, customtkinter.CTkLabel] = {}
        self._step_statuses: Dict[int, str] = {1: "pending", 2: "pending", 3: "pending"}

        self._build_ui()
        self.reset()

    # =========================================================================
    # UI Construction
    # =========================================================================

    def _build_ui(self) -> None:
        """Constructs progress bar, 3-phase checklist stepper, and token terminal."""
        container = customtkinter.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Progress Shimmer Bar (§8.1.5 item 3: 6px height, 3px radius)
        self._progress_bar = customtkinter.CTkProgressBar(
            container,
            height=6,
            corner_radius=3,
            fg_color=COLOR_BORDER_SUBTLE,
            progress_color=COLOR_BRAND_ACCENT,
        )
        self._progress_bar.pack(fill="x", pady=(0, 14))

        # 2. Stage Checklist Stepper (3 Phases)
        stepper_frame = customtkinter.CTkFrame(container, fg_color="transparent")
        stepper_frame.pack(fill="x", pady=(0, 12))

        mono_font = customtkinter.CTkFont(family="Cascadia Mono", size=11, weight="normal")
        for step_idx in range(1, 4):
            lbl = customtkinter.CTkLabel(
                stepper_frame,
                text=f"[·] {DEFAULT_PHASES[step_idx]}",
                font=mono_font,
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
                justify="left",
            )
            lbl.pack(fill="x", pady=2)
            self._step_labels[step_idx] = lbl

        # 3. Live Token Stream Terminal (90px expandable, #0A0F1D, Cascadia Mono 11pt)
        terminal_card = customtkinter.CTkFrame(
            container,
            fg_color=COLOR_TERMINAL_BG,
            border_color=COLOR_BORDER_SUBTLE,
            border_width=1,
            corner_radius=8,
        )
        terminal_card.pack(fill="both", expand=True)

        self._textbox = customtkinter.CTkTextbox(
            terminal_card,
            height=90,
            corner_radius=8,
            border_width=0,
            fg_color=COLOR_TERMINAL_BG,
            text_color=COLOR_TERMINAL_TEXT,
            font=customtkinter.CTkFont(family="Cascadia Mono", size=11, weight="normal"),
            wrap="word",
        )
        self._textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self._textbox.configure(state="disabled")

    # =========================================================================
    # Stepper & Progress Management
    # =========================================================================

    def set_step(self, step: int, status: str = "active", label: Optional[str] = None) -> None:
        """
        Updates stepper phase per §8.1.5 item 3.
        Statuses:
          - 'pending': [·] text in text_muted
          - 'active': [⟳] text in brand_accent
          - 'completed': [✓] text in status_success
          - 'error': [✕] text in status_error
        """
        if step not in self._step_labels:
            _logger.debug(f"Unknown step index {step} provided to set_step.")
            return

        base_label = label or DEFAULT_PHASES.get(step, f"Phase {step}")
        self._step_statuses[step] = status

        if status == "active":
            prefix = "[⟳]"
            color = COLOR_BRAND_ACCENT
            # Auto-complete preceding steps
            for prev_step in range(1, step):
                if self._step_statuses.get(prev_step) != "completed":
                    self.set_step(prev_step, "completed")
            # Ensure shimmer animation is active
            self._start_progress_animation()

            if step == 3:
                self._start_streaming()

        elif status == "completed":
            prefix = "[✓]"
            color = COLOR_STATUS_SUCCESS
            if step == 3:
                self._stop_streaming()
                self._stop_progress_animation(complete=True)

        elif status == "error":
            prefix = "[✕]"
            color = COLOR_STATUS_ERROR
            self._stop_streaming()
            self._stop_progress_animation(complete=False)

        else:  # pending
            prefix = "[·]"
            color = COLOR_TEXT_MUTED

        lbl_widget = self._step_labels[step]
        lbl_widget.configure(text=f"{prefix} {base_label}", text_color=color)

    def _start_progress_animation(self) -> None:
        """Starts indeterminate progress animation respecting reduced motion (§8.1.10)."""
        try:
            if check_reduced_motion():
                # Accessible mode: static progress value without continuous shimmer
                active_steps = [s for s, st in self._step_statuses.items() if st in ("active", "completed")]
                progress = max(0.2, len(active_steps) / 3.0)
                self._progress_bar.set(progress)
            else:
                self._progress_bar.configure(mode="indeterminate")
                self._progress_bar.start()
        except Exception as e:
            _logger.debug(f"Progress bar start exception: {e}")

    def _stop_progress_animation(self, complete: bool = False) -> None:
        """Stops progress bar animation and sets final state."""
        try:
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate")
            self._progress_bar.set(1.0 if complete else 0.0)
        except Exception as e:
            _logger.debug(f"Progress bar stop exception: {e}")

    # =========================================================================
    # Token Streaming & Blinking Caret
    # =========================================================================

    def append_token(self, token: str) -> None:
        """
        Appends a single token chunk to the terminal display with smooth auto-scroll (§8.1.5 item 3).
        """
        if not self._is_streaming:
            self._start_streaming()

        self._full_text += token

        try:
            self._textbox.configure(state="normal")
            # Remove trailing caret character if rendered
            if self._caret_rendered:
                self._textbox.delete("end-2c", "end-1c")
                self._caret_rendered = False

            # Insert new token
            self._textbox.insert("end", token)

            # Re-append caret if active
            if self._caret_visible and self._is_streaming:
                self._textbox.insert("end", "▋")
                self._caret_rendered = True

            # Smooth auto-scroll to the latest tokens
            self._textbox.see("end")
            self._textbox.configure(state="disabled")
        except Exception as e:
            _logger.debug(f"Error appending token: {e}")

    def _start_streaming(self) -> None:
        """Initializes token stream state and caret timer."""
        self._is_streaming = True
        self._caret_visible = True
        self._schedule_caret_toggle()

    def _stop_streaming(self) -> None:
        """Finalizes token streaming and removes caret."""
        self._is_streaming = False
        if self._caret_timer:
            try:
                self.after_cancel(self._caret_timer)
            except Exception:
                pass
            self._caret_timer = None

        try:
            self._textbox.configure(state="normal")
            if self._caret_rendered:
                self._textbox.delete("end-2c", "end-1c")
                self._caret_rendered = False
            self._textbox.configure(state="disabled")
        except Exception:
            pass

    def _schedule_caret_toggle(self) -> None:
        """Schedules the 500ms caret blinking interval (§8.1.5 item 3)."""
        if self._caret_timer:
            try:
                self.after_cancel(self._caret_timer)
            except Exception:
                pass
        self._caret_timer = self.after(500, self._toggle_caret)

    def _toggle_caret(self) -> None:
        """Toggles the terminal blinking caret every 500ms."""
        if not self._is_streaming:
            return

        self._caret_visible = not self._caret_visible

        try:
            if self.winfo_exists():
                self._textbox.configure(state="normal")
                if self._caret_rendered:
                    self._textbox.delete("end-2c", "end-1c")
                    self._caret_rendered = False

                if self._caret_visible:
                    self._textbox.insert("end", "▋")
                    self._caret_rendered = True

                self._textbox.see("end")
                self._textbox.configure(state="disabled")
                self._schedule_caret_toggle()
        except Exception:
            pass

    # =========================================================================
    # Lifecycle & Control API
    # =========================================================================

    def reset(self) -> None:
        """Clears terminal, resets stepper phases, and halts animations."""
        self._stop_streaming()
        self._stop_progress_animation(complete=False)

        self._full_text = ""
        self._caret_rendered = False

        try:
            self._textbox.configure(state="normal")
            self._textbox.delete("1.0", "end")
            self._textbox.configure(state="disabled")
        except Exception:
            pass

        # Reset stepper to pending
        for step_idx in range(1, 4):
            self.set_step(step_idx, "pending")

    def show(self) -> None:
        """Presents the stream terminal widget."""
        self.pack(fill="x", pady=(0, 16))

    def hide(self) -> None:
        """Hides the stream terminal widget."""
        self.pack_forget()

    def get_text(self) -> str:
        """Returns accumulated stream text."""
        return self._full_text

    def destroy(self) -> None:
        """Cleanly cancels scheduled timers prior to destruction."""
        if self._caret_timer:
            try:
                self.after_cancel(self._caret_timer)
            except Exception:
                pass
            self._caret_timer = None
        super().destroy()

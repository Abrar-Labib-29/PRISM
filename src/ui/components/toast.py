"""
iValue PRISM — Toast Notification System
SRS References: §8.1.9, §8.1.10, §8.1.15
Implementation Plan: TASK-P4.4

This module implements the non-blocking sliding toast notification manager (ToastNotificationManager).
Features:
  - Anchored to bottom-right corner with 16px margins
  - Fixed 340px width, min 48px height, 8px radius, 1px elevation border
  - 4 Semantic variants:
      * 'success': Green (#10B981), 4.0s auto-dismiss
      * 'info': Sky Blue (#38BDF8), 4.0s auto-dismiss
      * 'warning': Amber (#F59E0B), 6.0s auto-dismiss
      * 'error': Crimson (#EF4444), persistent until manually closed
  - Stacking behavior: Maximum 3 simultaneous toasts; older toasts pushed upward;
    exceeding 3 auto-dismisses the oldest toast.
  - Slide-in from right (180ms) and slide-out (120ms), with reduced-motion accessibility bypass.
  - Optional action buttons (e.g. 'Open Document', 'Show in Explorer').
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter

from src.utils.system_info import check_reduced_motion

_logger = logging.getLogger("prism.ui.toast")

# Typography
FONT_PRIMARY = "Segoe UI"
FONT_BODY = (FONT_PRIMARY, 11, "normal")
FONT_BOLD = (FONT_PRIMARY, 11, "bold")
FONT_SMALL = (FONT_PRIMARY, 10, "normal")

# Colors (§8.1.2)
COLOR_BG_CARD = ("#FFFFFF", "#131F37")
COLOR_BG_ELEVATED = ("#F1F5F9", "#1E293B")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_SECONDARY = ("#475569", "#94A3B8")
COLOR_TEXT_MUTED = ("#64748B", "#64748B")

# Variant Tokens: (color_tuple, default_duration_ms, icon)
VARIANT_CONFIG = {
    "success": (("#059669", "#10B981"), 4000, "✓"),
    "info":    (("#0284C7", "#38BDF8"), 4000, "ℹ"),
    "warning": (("#D97706", "#F59E0B"), 6000, "⚠"),
    "error":   (("#DC2626", "#EF4444"), None, "✕"),
}

MAX_VISIBLE_TOASTS = 3
TOAST_WIDTH = 340
MARGIN_RIGHT = 16
MARGIN_BOTTOM = 16
TOAST_GAP = 8


class ToastItem:
    """Represents a single active toast instance."""

    def __init__(
        self,
        toast_id: str,
        frame: customtkinter.CTkFrame,
        variant: str,
        height: int,
        timer_id: Optional[str] = None,
    ):
        self.toast_id = toast_id
        self.frame = frame
        self.variant = variant
        self.height = height
        self.timer_id = timer_id
        self.target_y_offset: int = 0
        self.is_dismissing: bool = False


class ToastNotificationManager:
    """Sliding toast notification system. §8.1.9."""

    def __init__(self, parent):
        self.parent = parent
        self._toasts: List[ToastItem] = []
        self._id_counter: int = 0

    def show(
        self,
        message: str,
        variant: str = "info",
        duration_ms: Optional[int] = None,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable[[], None]] = None,
    ) -> str:
        """
        Shows a toast notification.
        Variants: 'success' (green, 4s), 'info' (blue, 4s), 'warning' (amber, 6s), 'error' (red, persistent).
        Position: bottom-right, 16px margin. Width: 340px.
        Stacking: max 3 visible, oldest auto-dismissed.
        Motion: slide in from right (180ms), fade out (120ms). Skip if reduced-motion.
        """
        self._id_counter += 1
        toast_id = f"toast_{self._id_counter}_{uuid.uuid4().hex[:6]}"

        var_key = variant.lower() if variant.lower() in VARIANT_CONFIG else "info"
        color_tuple, default_dur, icon_sym = VARIANT_CONFIG[var_key]

        actual_duration = duration_ms if duration_ms is not None else default_dur

        # Enforce max visible limit (§8.1.9: max 3 visible, oldest auto-dismissed)
        while len(self._toasts) >= MAX_VISIBLE_TOASTS:
            oldest = self._toasts[0]
            self.dismiss(oldest.toast_id, immediate=True)

        # 1. Build toast widget frame
        toast_frame = customtkinter.CTkFrame(
            self.parent,
            width=TOAST_WIDTH,
            fg_color=COLOR_BG_CARD,
            border_width=1,
            border_color=color_tuple,
            corner_radius=8,
        )

        # Left 4px semantic color bar
        accent_strip = customtkinter.CTkFrame(
            toast_frame,
            width=4,
            fg_color=color_tuple,
            corner_radius=2,
        )
        accent_strip.pack(side="left", fill="y", padx=(0, 8), pady=2)

        # Content container
        content_box = customtkinter.CTkFrame(toast_frame, fg_color="transparent")
        content_box.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        # Top row: icon + message + close button
        top_row = customtkinter.CTkFrame(content_box, fg_color="transparent")
        top_row.pack(fill="x")

        lbl_icon = customtkinter.CTkLabel(
            top_row,
            text=icon_sym,
            font=FONT_BOLD,
            text_color=color_tuple,
            width=18,
            anchor="nw",
        )
        lbl_icon.pack(side="left", anchor="nw", padx=(0, 6))

        lbl_msg = customtkinter.CTkLabel(
            top_row,
            text=message,
            font=FONT_BODY,
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=230,
        )
        lbl_msg.pack(side="left", fill="x", expand=True)

        btn_close = customtkinter.CTkButton(
            top_row,
            text="✕",
            width=20,
            height=20,
            font=FONT_SMALL,
            fg_color="transparent",
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_BG_ELEVATED,
            command=lambda tid=toast_id: self.dismiss(tid),
        )
        btn_close.pack(side="right", anchor="ne", padx=(4, 0))

        # Optional action button (§8.1.15)
        if action_text and action_callback:
            action_row = customtkinter.CTkFrame(content_box, fg_color="transparent")
            action_row.pack(fill="x", pady=(6, 0))

            def _on_action():
                try:
                    action_callback()
                finally:
                    self.dismiss(toast_id)

            btn_action = customtkinter.CTkButton(
                action_row,
                text=action_text,
                height=26,
                font=FONT_SMALL,
                fg_color=COLOR_BG_ELEVATED,
                hover_color=color_tuple,
                border_width=1,
                border_color=color_tuple,
                text_color=COLOR_TEXT_PRIMARY,
                command=_on_action,
            )
            btn_action.pack(side="left", padx=(24, 0))

        # Calculate estimated height
        toast_frame.update_idletasks()
        req_height = max(48, toast_frame.winfo_reqheight())

        # Auto-dismiss timer if duration is specified
        timer_id = None
        if actual_duration and actual_duration > 0:
            timer_id = self.parent.after(actual_duration, lambda tid=toast_id: self.dismiss(tid))

        toast_item = ToastItem(
            toast_id=toast_id,
            frame=toast_frame,
            variant=var_key,
            height=req_height,
            timer_id=timer_id,
        )
        self._toasts.append(toast_item)

        # 2. Position & Animate
        self._reposition_all(new_item=toast_item)
        return toast_id

    def dismiss(self, toast_id: str, immediate: bool = False) -> None:
        """Dismisses a single toast by ID."""
        target_item = None
        for item in self._toasts:
            if item.toast_id == toast_id:
                target_item = item
                break

        if not target_item or target_item.is_dismissing:
            return

        target_item.is_dismissing = True

        # Cancel auto-dismiss timer
        if target_item.timer_id:
            try:
                self.parent.after_cancel(target_item.timer_id)
            except Exception:
                pass
            target_item.timer_id = None

        if immediate or check_reduced_motion():
            self._remove_toast_item(target_item)
        else:
            self._animate_slide_out(target_item)

    def dismiss_all(self) -> None:
        """Dismisses all active toasts immediately."""
        to_dismiss = list(self._toasts)
        for item in to_dismiss:
            self.dismiss(item.toast_id, immediate=True)

    def _remove_toast_item(self, item: ToastItem) -> None:
        """Destroys widget and removes from tracked active list."""
        try:
            item.frame.place_forget()
            item.frame.destroy()
        except Exception:
            pass

        if item in self._toasts:
            self._toasts.remove(item)

        self._reposition_all()

    def _reposition_all(self, new_item: Optional[ToastItem] = None) -> None:
        """Recalculates positions and stacks toasts from bottom upward."""
        # Calculate Y offsets from bottom
        current_y_offset = MARGIN_BOTTOM

        # Reversed order: index 0 of loop is the newest toast (at bottom)
        for item in reversed(self._toasts):
            item.target_y_offset = current_y_offset
            current_y_offset += item.height + TOAST_GAP

            if item != new_item:
                # Update position for existing toasts
                item.frame.place(
                    relx=1.0,
                    rely=1.0,
                    x=-MARGIN_RIGHT,
                    y=-item.target_y_offset,
                    anchor="se",
                )

        # Animate new toast slide-in
        if new_item:
            if check_reduced_motion():
                new_item.frame.place(
                    relx=1.0,
                    rely=1.0,
                    x=-MARGIN_RIGHT,
                    y=-new_item.target_y_offset,
                    anchor="se",
                )
            else:
                self._animate_slide_in(new_item)

    def _animate_slide_in(self, item: ToastItem) -> None:
        """Slides in toast horizontally from the right over 180ms (§8.1.9)."""
        steps = 6
        step_interval = 30  # 6 * 30ms = 180ms
        start_x = TOAST_WIDTH + MARGIN_RIGHT
        end_x = -MARGIN_RIGHT

        def _step(current_step: int):
            if item.is_dismissing or item not in self._toasts:
                return

            # Ease-out ratio
            t = current_step / steps
            ease_ratio = 1 - (1 - t) * (1 - t)
            cur_x = int(start_x + (end_x - start_x) * ease_ratio)

            item.frame.place(
                relx=1.0,
                rely=1.0,
                x=cur_x,
                y=-item.target_y_offset,
                anchor="se",
            )

            if current_step < steps:
                self.parent.after(step_interval, lambda: _step(current_step + 1))

        _step(1)

    def _animate_slide_out(self, item: ToastItem) -> None:
        """Slides out toast horizontally to the right over 120ms (§8.1.9)."""
        steps = 4
        step_interval = 30  # 4 * 30ms = 120ms
        start_x = -MARGIN_RIGHT
        end_x = TOAST_WIDTH + MARGIN_RIGHT

        def _step(current_step: int):
            t = current_step / steps
            ease_ratio = t * t  # Ease-in
            cur_x = int(start_x + (end_x - start_x) * ease_ratio)

            try:
                item.frame.place(
                    relx=1.0,
                    rely=1.0,
                    x=cur_x,
                    y=-item.target_y_offset,
                    anchor="se",
                )
            except Exception:
                pass

            if current_step < steps:
                self.parent.after(step_interval, lambda: _step(current_step + 1))
            else:
                self._remove_toast_item(item)

        _step(1)

    @property
    def active_count(self) -> int:
        """Returns the number of active visible toasts."""
        return len(self._toasts)

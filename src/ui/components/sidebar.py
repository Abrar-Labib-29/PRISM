"""
iValue PRISM — Sidebar Control Center
SRS References: §8.1.1, §8.1.4, §8.1.5 item 1, §8.1.13, §10.7, §11.4
Implementation Plan: TASK-P3.4

This module implements the left navigation sidebar (SidebarView) for iValue PRISM.
Features:
  - Fixed 280px width with brand header lockup (40x40 logo, H2 title, v3.4 badge pill)
  - Live system health status panel (hardware vector dot for Ollama, model badge, catalog count, live RAM bar)
  - Interactive Session History Reel (FIFO list of up to 20 SessionSnapshot instances)
  - Utility action toolbar (New Query, Clear Workspace, Re-index Catalog)
  - Dynamic Theme Mode Switcher ([Dark | Light | System] CTkSegmentedButton with live persistence)
"""

from __future__ import annotations

import logging
import os
import pathlib
import sys
import tkinter as tk
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import customtkinter
from PIL import Image

if TYPE_CHECKING:
    from src.core.service import PrismService, SystemHealthResponse

from src.utils.config import APP_VERSION, ConfigManager, SessionSnapshot
from src.utils.system_info import get_ram_usage_mb

_logger = logging.getLogger("prism.ui.sidebar")

# Dimensions & Layout Constants (§8.1.4, §8.1.6)
SIDEBAR_WIDTH = 280
MAX_SESSIONS = 20

# Color Tokens from iValue Brand Architecture (§8.1.2)
COLOR_BG_SIDEBAR = ("#E2E8F0", "#0F172A")
COLOR_BG_CARD = ("#FFFFFF", "#131F37")
COLOR_BORDER_SUBTLE = ("#CBD5E1", "#1E293B")
COLOR_BORDER_ACCENT = ("#0284C7", "#38BDF8")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_SECONDARY = ("#475569", "#94A3B8")
COLOR_TEXT_MUTED = ("#64748B", "#64748B")
COLOR_BRAND_PURPLE = ("#4C1D95", "#7C3AED")
COLOR_BRAND_ACCENT = ("#0284C7", "#0EA5E9")
COLOR_ACCENT_HOVER = ("#0369A1", "#38BDF8")
COLOR_STATUS_ONLINE = "#10B981"
COLOR_STATUS_OFFLINE = "#EF4444"
COLOR_STATUS_WARNING = "#F59E0B"
COLOR_ITEM_HOVER = ("#CBD5E1", "#1E293B")


def _get_asset_path(relative_path: str) -> pathlib.Path:
    """Resolves asset path for development mode and PyInstaller frozen bundle."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return pathlib.Path(base_path) / relative_path
    return pathlib.Path(__file__).resolve().parent.parent.parent.parent / relative_path


class SidebarView(customtkinter.CTkFrame):
    """
    Left navigation and system control center (§8.1.5 item 1).
    Fixed width of 280px spanning full vertical viewport height.
    """

    def __init__(
        self,
        parent: Any,
        service: Optional[PrismService] = None,
        config: Optional[ConfigManager] = None,
        **kwargs: Any,
    ) -> None:
        # Enforce fixed 280px width
        kwargs["width"] = SIDEBAR_WIDTH
        kwargs["corner_radius"] = 0
        kwargs["fg_color"] = COLOR_BG_SIDEBAR
        kwargs["border_width"] = 0
        super().__init__(parent, **kwargs)

        self._service = service
        self.config_manager = config or ConfigManager()

        # Session history FIFO storage (up to 20 volatile snapshots)
        self._sessions: List[SessionSnapshot] = []

        # Action callbacks
        self._on_session_restore_callback: Optional[Callable[[SessionSnapshot], None]] = None
        self._on_new_query_callback: Optional[Callable[[], None]] = None
        self._on_clear_workspace_callback: Optional[Callable[[], None]] = None
        self._on_reindex_callback: Optional[Callable[[], None]] = None

        # Lock layout geometry propagation
        self.pack_propagate(False)
        self.grid_propagate(False)

        # Build UI Sections
        self._build_header()
        self._build_status_panel()
        self._build_utility_actions()
        self._build_session_reel()
        self._build_theme_switcher()

        # Initial health status refresh
        self.refresh_health()

    # =========================================================================
    # Header Lockup (§8.1.5 item 1)
    # =========================================================================

    def _build_header(self) -> None:
        """Constructs 40x40 PRISM logo + 'iValue PRISM' H2 + v3.4 badge pill."""
        header_container = customtkinter.CTkFrame(
            self,
            fg_color="transparent",
            height=60,
        )
        header_container.pack(fill="x", padx=16, pady=(16, 12))
        header_container.pack_propagate(False)

        # Left lockup: 40x40 logo + text
        left_box = customtkinter.CTkFrame(header_container, fg_color="transparent")
        left_box.pack(side="left", fill="both", expand=True)

        # 40x40 Brand Logo Graphic or refractive glyph fallback
        logo_path = _get_asset_path("assets/branding/ivalue_prism_logo.png")
        if not logo_path.exists():
            logo_path = _get_asset_path("assets/branding/ivalue_prism_logo.jpg")
        logo_loaded = False

        if logo_path.exists():
            try:
                pil_img = Image.open(logo_path)
                self._logo_img = customtkinter.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(36, 36),
                )
                logo_lbl = customtkinter.CTkLabel(
                    left_box,
                    image=self._logo_img,
                    text="",
                )
                logo_lbl.pack(side="left", padx=(0, 8))
                logo_loaded = True
            except Exception as e:
                _logger.debug(f"Could not load sidebar logo image: {e}")

        if not logo_loaded:
            # Fallback stylized refractive glyph
            glyph_lbl = customtkinter.CTkLabel(
                left_box,
                text="▲",
                font=customtkinter.CTkFont(family="Segoe UI", size=24, weight="bold"),
                text_color=COLOR_BRAND_ACCENT,
            )
            glyph_lbl.pack(side="left", padx=(0, 8))

        # Title Label: H2 Semi-Bold ("Segoe UI", 15, "bold")
        title_lbl = customtkinter.CTkLabel(
            left_box,
            text="iValue PRISM",
            font=customtkinter.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        title_lbl.pack(side="left", pady=2)

        # Version badge pill: v3.4 with 4px corner radius and Purple background
        version_pill = customtkinter.CTkFrame(
            header_container,
            fg_color=COLOR_BRAND_PURPLE,
            corner_radius=4,
            height=20,
        )
        version_pill.pack(side="right", pady=10)
        version_lbl = customtkinter.CTkLabel(
            version_pill,
            text=f"v{APP_VERSION}",
            font=customtkinter.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color="#F8FAFC",
            padx=6,
            pady=1,
        )
        version_lbl.pack()

    # =========================================================================
    # Live System Status Panel (§8.1.5 item 1, §11.4)
    # =========================================================================

    def _build_status_panel(self) -> None:
        """Constructs live system health status card with hardware-accelerated vector indicator."""
        self._status_card = customtkinter.CTkFrame(
            self,
            fg_color=COLOR_BG_CARD,
            border_color=COLOR_BORDER_SUBTLE,
            border_width=1,
            corner_radius=8,
        )
        self._status_card.pack(fill="x", padx=16, pady=(0, 12))

        # 1. Ollama status line with 8x8px hardware vector circle
        ollama_row = customtkinter.CTkFrame(self._status_card, fg_color="transparent")
        ollama_row.pack(fill="x", padx=12, pady=(10, 4))

        # Native Canvas for 8x8px vector circle indicator
        card_bg = self._get_current_card_bg()
        self._dot_canvas = tk.Canvas(
            ollama_row,
            width=10,
            height=10,
            bg=card_bg,
            highlightthickness=0,
            bd=0,
        )
        self._dot_canvas.pack(side="left", padx=(0, 6), pady=2)
        self._status_dot = self._dot_canvas.create_oval(
            1, 1, 9, 9, fill=COLOR_STATUS_ONLINE, outline=""
        )

        self._ollama_label = customtkinter.CTkLabel(
            ollama_row,
            text="Ollama Online :11434",
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="normal"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        self._ollama_label.pack(side="left", fill="x", expand=True)

        # Embedded "Start Daemon" button (shown only when offline)
        self._start_daemon_btn = customtkinter.CTkButton(
            self._status_card,
            text="Start Daemon",
            height=24,
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=COLOR_BRAND_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._on_start_daemon_clicked,
        )

        # 2. Model Badge pill
        model_row = customtkinter.CTkFrame(self._status_card, fg_color="transparent")
        model_row.pack(fill="x", padx=12, pady=2)

        self._model_badge = customtkinter.CTkLabel(
            model_row,
            text="phi4-mini (3.8B Q4_K_M)",
            font=customtkinter.CTkFont(family="Cascadia Mono", size=10, weight="normal"),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        self._model_badge.pack(side="left")

        # 3. Index Status (Catalog count)
        index_row = customtkinter.CTkFrame(self._status_card, fg_color="transparent")
        index_row.pack(fill="x", padx=12, pady=2)

        self._index_label = customtkinter.CTkLabel(
            index_row,
            text="✓ 139 Catalog Products Active",
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="normal"),
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        self._index_label.pack(side="left")

        # 4. Live Process RAM Meter
        ram_row = customtkinter.CTkFrame(self._status_card, fg_color="transparent")
        ram_row.pack(fill="x", padx=12, pady=(4, 10))

        self._ram_label = customtkinter.CTkLabel(
            ram_row,
            text="RAM: -- MB (Safe)",
            font=customtkinter.CTkFont(family="Segoe UI", size=9, weight="normal"),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        self._ram_label.pack(fill="x", pady=(0, 2))

        self._ram_bar = customtkinter.CTkProgressBar(
            ram_row,
            height=4,
            corner_radius=2,
            fg_color=COLOR_BORDER_SUBTLE,
            progress_color=COLOR_STATUS_ONLINE,
        )
        self._ram_bar.pack(fill="x")
        self._ram_bar.set(0.08)

    # =========================================================================
    # Utility Actions (§8.1.5 item 1)
    # =========================================================================

    def _build_utility_actions(self) -> None:
        """Constructs 'New Query', 'Clear Workspace', and 'Re-index Catalog' actions."""
        actions_container = customtkinter.CTkFrame(self, fg_color="transparent")
        actions_container.pack(fill="x", padx=16, pady=(0, 10))

        # 1. Primary "New Query" button (+ accent prefix, 36px height)
        self._new_query_btn = customtkinter.CTkButton(
            actions_container,
            text="+  New Query",
            height=36,
            corner_radius=8,
            font=customtkinter.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLOR_BRAND_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._handle_new_query,
        )
        self._new_query_btn.pack(fill="x", pady=(0, 6))

        # Secondary action links row
        sub_row = customtkinter.CTkFrame(actions_container, fg_color="transparent")
        sub_row.pack(fill="x")

        # Clear Workspace
        self._clear_btn = customtkinter.CTkButton(
            sub_row,
            text="⌫ Clear",
            height=28,
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="normal"),
            fg_color="transparent",
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_ITEM_HOVER,
            command=self._handle_clear_workspace,
        )
        self._clear_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        # Re-index Catalog
        self._reindex_btn = customtkinter.CTkButton(
            sub_row,
            text="↻ Re-index",
            height=28,
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="normal"),
            fg_color="transparent",
            text_color=COLOR_TEXT_SECONDARY,
            hover_color=COLOR_ITEM_HOVER,
            command=self._handle_reindex,
        )
        self._reindex_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

    # =========================================================================
    # Session History Reel (§8.1.5 item 1)
    # =========================================================================

    def _build_session_reel(self) -> None:
        """Constructs scrollable FIFO list of up to 20 recent SessionSnapshot records."""
        reel_header = customtkinter.CTkFrame(self, fg_color="transparent")
        reel_header.pack(fill="x", padx=16, pady=(4, 4))

        self._reel_title = customtkinter.CTkLabel(
            reel_header,
            text="Recent Sessions",
            font=customtkinter.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        self._reel_title.pack(side="left")

        self._reel_count = customtkinter.CTkLabel(
            reel_header,
            text="(0/20)",
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="normal"),
            text_color=COLOR_TEXT_MUTED,
            anchor="e",
        )
        self._reel_count.pack(side="right")

        # Scrollable container for session items
        self._history_scroll = customtkinter.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
        )
        self._history_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # Initial zero state
        self._empty_label = customtkinter.CTkLabel(
            self._history_scroll,
            text="No recent sessions",
            font=customtkinter.CTkFont(family="Segoe UI", size=10, slant="italic"),
            text_color=COLOR_TEXT_MUTED,
        )
        self._empty_label.pack(pady=20)

    # =========================================================================
    # Theme Switcher Control (§8.1.13)
    # =========================================================================

    def _build_theme_switcher(self) -> None:
        """Constructs bottom-anchored CTkSegmentedButton [Dark | Light | System]."""
        bottom_container = customtkinter.CTkFrame(
            self,
            fg_color="transparent",
            height=50,
        )
        bottom_container.pack(side="bottom", fill="x", padx=16, pady=12)
        bottom_container.pack_propagate(False)

        current_mode = self.config_manager.get("appearance_mode", "dark").capitalize()
        if current_mode not in ["Dark", "Light", "System"]:
            current_mode = "Dark"

        self._theme_segmented = customtkinter.CTkSegmentedButton(
            bottom_container,
            values=["Dark", "Light", "System"],
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="normal"),
            height=28,
            command=self._on_theme_change,
        )
        self._theme_segmented.pack(fill="x", pady=2)
        self._theme_segmented.set(current_mode)

    # =========================================================================
    # Public API & State Updaters
    # =========================================================================

    def set_service(self, service: PrismService) -> None:
        """Attaches PrismService and refreshes system indicators."""
        self._service = service
        self.refresh_health()

    def update_health(self, health: SystemHealthResponse) -> None:
        """
        Updates live status indicators from SystemHealthResponse (§11.4).
        """
        # 1. Ollama status
        is_online = health.ollama_status == "online"
        dot_color = COLOR_STATUS_ONLINE if is_online else COLOR_STATUS_OFFLINE
        status_text = "Ollama Online :11434" if is_online else "Ollama [OFFLINE]"

        try:
            self._dot_canvas.itemconfig(self._status_dot, fill=dot_color)
            self._ollama_label.configure(text=status_text)
        except Exception:
            pass

        # Show or hide "Start Daemon" button
        if is_online:
            self._start_daemon_btn.pack_forget()
        else:
            self._start_daemon_btn.pack(fill="x", padx=12, pady=(0, 6))

        # 2. Model Badge
        model_name = health.model_loaded or "phi4-mini"
        self._model_badge.configure(text=f"{model_name} (3.8B Q4_K_M)")

        # 3. Index Status
        idx_count = health.embedding_index_count
        self._index_label.configure(text=f"✓ {idx_count} Catalog Products Active")

        # 4. RAM Meter
        self._update_ram_meter(health.ram_usage_mb)

    def refresh_health(self) -> None:
        """Pulls current diagnostics from service or psutil and refreshes UI."""
        if self._service and hasattr(self._service, "get_health"):
            try:
                health = self._service.get_health()
                self.update_health(health)
                return
            except Exception as e:
                _logger.debug(f"Could not retrieve service health: {e}")

        # Fallback diagnostics when service is not attached yet
        ram_mb = get_ram_usage_mb()
        self._update_ram_meter(ram_mb)

    def add_session(self, snapshot: SessionSnapshot) -> None:
        """
        Adds a new SessionSnapshot to the volatile FIFO history reel (§8.1.5 item 1).
        Enforces MAX_SESSIONS = 20 constraint.
        """
        # Avoid duplicate consecutive query IDs
        self._sessions = [s for s in self._sessions if s.query_id != snapshot.query_id]

        # Insert at top (newest first)
        self._sessions.insert(0, snapshot)

        # Enforce FIFO capacity of 20
        if len(self._sessions) > MAX_SESSIONS:
            self._sessions = self._sessions[:MAX_SESSIONS]

        self._render_session_history()

    def set_on_session_restore(self, callback: Callable[[SessionSnapshot], None]) -> None:
        """Registers listener for user selecting a session history entry."""
        self._on_session_restore_callback = callback

    def set_on_new_query(self, callback: Callable[[], None]) -> None:
        """Registers listener for 'New Query' button."""
        self._on_new_query_callback = callback

    def set_on_clear_workspace(self, callback: Callable[[], None]) -> None:
        """Registers listener for 'Clear Workspace' button."""
        self._on_clear_workspace_callback = callback

    def set_on_reindex(self, callback: Callable[[], None]) -> None:
        """Registers listener for 'Re-index Catalog' button."""
        self._on_reindex_callback = callback

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _get_current_card_bg(self) -> str:
        """Returns hex color of card surface based on active appearance mode."""
        mode = customtkinter.get_appearance_mode()
        return COLOR_BG_CARD[1] if mode == "Dark" else COLOR_BG_CARD[0]

    def _update_canvas_bg(self) -> None:
        """Synchronizes canvas background with current theme mode."""
        try:
            bg_color = self._get_current_card_bg()
            self._dot_canvas.configure(bg=bg_color)
        except Exception:
            pass

    def _update_ram_meter(self, ram_mb: float) -> None:
        """Updates live RAM text and progress bar indicator (§8.1.5 item 1)."""
        if ram_mb < 500.0:
            status_text = "Safe"
            progress_color = COLOR_STATUS_ONLINE
        elif ram_mb < 1000.0:
            status_text = "Moderate"
            progress_color = COLOR_STATUS_WARNING
        else:
            status_text = "High"
            progress_color = COLOR_STATUS_OFFLINE

        self._ram_label.configure(text=f"RAM: {ram_mb:.0f} MB ({status_text})")
        progress_val = min(1.0, max(0.05, ram_mb / 1024.0))
        self._ram_bar.set(progress_val)
        self._ram_bar.configure(progress_color=progress_color)

    def _render_session_history(self) -> None:
        """Rebuilds session history reel widgets from in-memory list."""
        # Clean existing children
        for widget in self._history_scroll.winfo_children():
            widget.destroy()

        count = len(self._sessions)
        self._reel_count.configure(text=f"({count}/{MAX_SESSIONS})")

        if not self._sessions:
            self._empty_label = customtkinter.CTkLabel(
                self._history_scroll,
                text="No recent sessions",
                font=customtkinter.CTkFont(family="Segoe UI", size=10, slant="italic"),
                text_color=COLOR_TEXT_MUTED,
            )
            self._empty_label.pack(pady=20)
            return

        for snapshot in self._sessions:
            self._create_session_item(snapshot)

    def _create_session_item(self, snapshot: SessionSnapshot) -> None:
        """Constructs single clickable session item card with 1-line query preview and timestamp."""
        # Extract 1-line truncated preview
        req_clean = snapshot.requirement_text.replace("\n", " ").strip()
        preview = req_clean[:24] + "..." if len(req_clean) > 24 else req_clean
        if not preview:
            preview = f"Query {snapshot.query_id[:8]}"

        # Short timestamp extraction (HH:MM or MM-DD HH:MM)
        ts_str = snapshot.timestamp
        if "T" in ts_str:
            time_part = ts_str.split("T")[1][:5]
        else:
            time_part = ts_str[-8:-3] if len(ts_str) >= 8 else ts_str

        # Item Card Button
        item_btn = customtkinter.CTkButton(
            self._history_scroll,
            text=f"{preview}   ·   {time_part}",
            height=30,
            corner_radius=6,
            font=customtkinter.CTkFont(family="Segoe UI", size=10, weight="normal"),
            fg_color="transparent",
            text_color=COLOR_TEXT_PRIMARY,
            hover_color=COLOR_ITEM_HOVER,
            anchor="w",
            command=lambda s=snapshot: self._handle_session_click(s),
        )
        item_btn.pack(fill="x", pady=1)

    def _handle_session_click(self, snapshot: SessionSnapshot) -> None:
        """Dispatches session click to registered listener."""
        _logger.debug(f"Session selected: {snapshot.query_id}")
        if self._on_session_restore_callback:
            try:
                self._on_session_restore_callback(snapshot)
            except Exception as e:
                _logger.error(f"Error invoking session restore callback: {e}", exc_info=True)

    def _handle_new_query(self) -> None:
        """Dispatches New Query action."""
        if self._on_new_query_callback:
            self._on_new_query_callback()

    def _handle_clear_workspace(self) -> None:
        """Dispatches Clear Workspace action."""
        if self._on_clear_workspace_callback:
            self._on_clear_workspace_callback()

    def _handle_reindex(self) -> None:
        """Dispatches Re-index Catalog action."""
        if self._on_reindex_callback:
            self._on_reindex_callback()

    def _on_start_daemon_clicked(self) -> None:
        """Attempts to start the Ollama background daemon."""
        _logger.info("User clicked 'Start Daemon' button.")
        if self._service and hasattr(self._service, "ollama_mgr"):
            try:
                import threading
                threading.Thread(
                    target=self._start_daemon_bg,
                    name="StartOllamaThread",
                    daemon=True,
                ).start()
            except Exception as e:
                _logger.warning(f"Failed to launch start daemon thread: {e}")

    def _start_daemon_bg(self) -> None:
        """Background daemon launcher thread."""
        try:
            if self._service:
                self._service.ollama_mgr.auto_start()
            self.after(1000, self.refresh_health)
        except Exception as e:
            _logger.warning(f"Error during auto_start: {e}")

    def _on_theme_change(self, mode: str) -> None:
        """
        Dynamically switches application appearance mode without restart (§8.1.13).
        Persists preference to %APPDATA%/iValue_PRISM/config.json.
        """
        mode_lower = mode.lower()
        _logger.info(f"Theme mode toggled to '{mode_lower}'. Applying dynamically...")
        customtkinter.set_appearance_mode(mode_lower)
        self.config_manager.set("appearance_mode", mode_lower)
        self._update_canvas_bg()

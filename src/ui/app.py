"""
iValue PRISM — Main Application Window (PRISMApp)
SRS References: §8.1.1, §8.1.6, §9.8, §9.9, §10.6, §10.7
Implementation Plan: TASK-P3.3

This module implements the root desktop window (PRISMApp) for iValue PRISM.
It manages the primary layout chrome, window state persistence, screen boundary validation,
asynchronous message queue polling, and thread-safe worker lifecycle orchestration.
"""
from __future__ import annotations

import logging
import os
import pathlib
import queue
import re
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

import customtkinter

if TYPE_CHECKING:
    from src.core.service import PrismService
    from src.core.worker import WorkerThread

from src.utils.config import (
    APP_VERSION,
    ConfigManager,
    QUEUE_POLL_INTERVAL_MS,
)

_logger = logging.getLogger("prism.ui.app")

# Default Window Constants (§8.1.1, §8.1.6)
WINDOW_TITLE = f"iValue PRISM — Presales Recommendation & Intelligence System [v{APP_VERSION}]"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 820
MIN_WIDTH = 1024
MIN_HEIGHT = 640
SIDEBAR_WIDTH = 280

# Theme token colors (§8.1.2)
COLOR_BG_CANVAS = ("#F1F5F9", "#0B1120")
COLOR_BG_SIDEBAR = ("#E2E8F0", "#0F172A")


def _get_asset_path(relative_path: str) -> pathlib.Path:
    """Resolves asset path for both development mode and PyInstaller frozen bundle."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return pathlib.Path(base_path) / relative_path
    return pathlib.Path(__file__).resolve().parent.parent.parent / relative_path


class PRISMApp(customtkinter.CTk):
    """
    Root application window for iValue PRISM (§8.1.1, §8.1.6).
    Enforces the single-root desktop architecture, owns the primary UI event loop,
    dispatches background worker tasks, and drains the thread-safe queue.Queue.
    """

    def __init__(
        self,
        service: Optional[PrismService] = None,
        config: Optional[ConfigManager] = None,
    ) -> None:
        super().__init__()

        self.config_manager = config or ConfigManager()
        self._service: Optional[Any] = service
        self._ui_queue: queue.Queue = queue.Queue()
        self._worker: Optional[Any] = None
        if self._service:
            from src.core.worker import WorkerThread
            self._worker = WorkerThread(self._service, self._ui_queue)

        self._poll_job_id: Optional[str] = None
        self._poll_interval_ms: int = QUEUE_POLL_INTERVAL_MS

        self._configure_window()
        self._setup_layout()
        self._restore_geometry()
        self._bind_events()
        self._start_queue_poll()

    @property
    def service(self) -> Optional[Any]:
        """Provides access to the core PrismService façade."""
        return self._service

    @property
    def worker(self) -> Optional[Any]:
        """Provides access to the background WorkerThread dispatcher."""
        return self._worker

    @property
    def ui_queue(self) -> queue.Queue:
        """Provides access to the main thread UI message queue."""
        return self._ui_queue

    def set_service(self, service: Any) -> None:
        """
        Attaches the initialized PrismService façade post-splash and instantiates the WorkerThread.
        """
        self._service = service
        if not self._worker:
            from src.core.worker import WorkerThread
            self._worker = WorkerThread(self._service, self._ui_queue)
        _logger.info("PrismService façade attached to PRISMApp.")

    def _configure_window(self) -> None:
        """Sets application window chrome, title, and branding icon (§8.1.1, §8.1.6)."""
        self.title(WINDOW_TITLE)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)

        # Set window icon if available
        icon_path = _get_asset_path("assets/branding/ivalue_prism.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception as e:
                _logger.debug(f"Could not load iconbitmap '{icon_path}': {e}")

    def _setup_layout(self) -> None:
        """
        Constructs root 2-column grid layout (§8.1.4):
        - Column 0: Fixed 280px sidebar container
        - Column 1: Flexible main canvas workspace with 24px outer padding
        """
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_WIDTH)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left navigation & control sidebar container (§8.1.4, §8.1.5 item 1)
        self.sidebar_frame = customtkinter.CTkFrame(
            self,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=COLOR_BG_SIDEBAR,
            border_width=0,
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        # Right main canvas workspace container (§8.1.4, §8.1.5 items 2-5)
        self.main_canvas_frame = customtkinter.CTkFrame(
            self,
            corner_radius=0,
            fg_color=COLOR_BG_CANVAS,
            border_width=0,
        )
        self.main_canvas_frame.grid(row=0, column=1, sticky="nsew", padx=24, pady=24)

    def _validate_window_position(
        self,
        x: Optional[int],
        y: Optional[int],
        w: int,
        h: int,
    ) -> Tuple[int, int, bool]:
        """
        Boundary validator for disconnected secondary monitors and display changes (§10.6).
        Inspects (x, y) against visible screen dimensions. If outside viewport, resets to center.
        Returns: (x, y, is_valid)
        """
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
        except Exception:
            screen_w = 1920
            screen_h = 1080

        # If coordinates are unset or None, center on primary display
        if x is None or y is None:
            cx = max(0, (screen_w - w) // 2)
            cy = max(0, (screen_h - h) // 2)
            return cx, cy, True

        # Validation per §10.6: window must have at least 100px visible on the monitor
        if x < -w + 100 or x > screen_w - 100 or y < 0 or y > screen_h - 100:
            _logger.warning(
                f"WARN: Stored window coordinates ({x}, {y}) off-screen. "
                f"Re-centered window to primary monitor ({screen_w}x{screen_h})."
            )
            cx = max(0, (screen_w - w) // 2)
            cy = max(0, (screen_h - h) // 2)
            return cx, cy, False

        return x, y, True

    def _restore_geometry(self) -> None:
        """
        Restores window geometry and maximization state from ConfigManager (§8.1.6).
        Enforces minimum bounds (1024x640) and boundary self-healing (§10.6).
        """
        geom_config = self.config_manager.get(
            "window_geometry", [DEFAULT_WIDTH, DEFAULT_HEIGHT, None, None, False]
        )

        w = DEFAULT_WIDTH
        h = DEFAULT_HEIGHT
        x = None
        y = None
        is_maximized = False

        if isinstance(geom_config, list) and len(geom_config) >= 2:
            try:
                w = max(MIN_WIDTH, int(geom_config[0]))
                h = max(MIN_HEIGHT, int(geom_config[1]))
                if len(geom_config) >= 4 and geom_config[2] is not None and geom_config[3] is not None:
                    x = int(geom_config[2])
                    y = int(geom_config[3])
                if len(geom_config) >= 5:
                    is_maximized = bool(geom_config[4])
            except (ValueError, TypeError) as e:
                _logger.warning(f"Error parsing saved window geometry: {e}. Using defaults.")
                w = DEFAULT_WIDTH
                h = DEFAULT_HEIGHT

        # Bound check against screen size if display is smaller than default (e.g. 1280x720 or 1366x768)
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            if screen_w > 0 and w > screen_w:
                w = max(MIN_WIDTH, screen_w)
            if screen_h > 0 and h > screen_h:
                h = max(MIN_HEIGHT, screen_h)
        except Exception:
            pass

        # Self-heal off-screen coordinates
        valid_x, valid_y, _ = self._validate_window_position(x, y, w, h)
        self.geometry(f"{w}x{h}+{valid_x}+{valid_y}")

        if is_maximized:
            try:
                # Windows maximized state via state('zoomed')
                self.after(100, lambda: self.state("zoomed"))
            except Exception as e:
                _logger.debug(f"Could not apply maximized state: {e}")

    def _save_geometry(self) -> None:
        """
        Extracts current window coordinates, dimensions, and state, persisting them to config.json (§8.1.6).
        """
        try:
            is_maximized = False
            try:
                is_maximized = (self.state() == "zoomed")
            except Exception:
                pass

            w = getattr(self, "_current_width", DEFAULT_WIDTH)
            h = getattr(self, "_current_height", DEFAULT_HEIGHT)
            x = self.winfo_x()
            y = self.winfo_y()

            geom_str = self.geometry()
            # Format: 'WIDTHxHEIGHT+X+Y' (supports negative offsets)
            match = re.match(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", geom_str)
            if match:
                gw = int(match.group(1))
                gh = int(match.group(2))
                gx = int(match.group(3))
                gy = int(match.group(4))
                if gw >= MIN_WIDTH and gh >= MIN_HEIGHT:
                    w, h, x, y = gw, gh, gx, gy

            w = max(MIN_WIDTH, int(w))
            h = max(MIN_HEIGHT, int(h))
            self.config_manager.set("window_geometry", [w, h, x, y, is_maximized])
            _logger.debug(f"Saved window geometry: [{w}, {h}, {x}, {y}, {is_maximized}]")
        except Exception as e:
            _logger.warning(f"Failed to save window geometry: {e}")

    def _bind_events(self) -> None:
        """Binds window protocol handlers."""
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _start_queue_poll(self) -> None:
        """Initiates the periodic queue polling loop (§9.8 item 4)."""
        self._poll_job_id = self.after(self._poll_interval_ms, self._process_queue)

    def _process_queue(self) -> None:
        """
        Polls ui_queue every 50ms on the main UI thread.
        Drains all pending messages and routes them to appropriate handlers (§9.8, §9.10 item 4).
        """
        while True:
            try:
                msg = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            except Exception as e:
                _logger.error(f"Error accessing UI queue: {e}")
                break

            try:
                self._handle_queue_message(msg)
            except Exception as e:
                _logger.error(f"Error handling UI queue message: {e}", exc_info=True)

        # Reschedule next polling cycle if window is still active
        try:
            if self.winfo_exists():
                self._poll_job_id = self.after(self._poll_interval_ms, self._process_queue)
        except Exception:
            pass

    def _handle_queue_message(self, msg: Dict[str, Any]) -> None:
        """
        Routes standardized dictionary envelope messages (§9.10 item 4).
        """
        msg_type = msg.get("type")

        if msg_type == "STATUS_STEP":
            self._on_status_step(msg.get("step", 1), msg.get("label", ""))
        elif msg_type == "STREAM_TOKEN":
            self._on_stream_token(msg.get("token", ""))
        elif msg_type == "STREAM_COMPLETE":
            self._on_stream_complete(msg.get("full_text", ""))
        elif msg_type == "ANALYSIS_SUCCESS":
            self._on_analysis_success(msg.get("payload"))
        elif msg_type == "ANALYSIS_ERROR":
            self._on_analysis_error(msg.get("error_type", "GENERAL"), msg.get("message", ""))
        elif msg_type == "ANALYSIS_CANCELLED":
            self._on_analysis_cancelled()
        else:
            _logger.debug(f"Received unhandled queue message type: {msg_type}")

    # =========================================================================
    # Queue Handler Stubs (Hooked by child components in P3.4, P3.5, P4.x)
    # =========================================================================

    def _on_status_step(self, step: int, label: str) -> None:
        """Handles RAG pipeline progress step updates."""
        _logger.debug(f"Queue [STATUS_STEP]: step={step}, label='{label}'")

    def _on_stream_token(self, token: str) -> None:
        """Handles incoming streamed tokens from Ollama LLM."""
        pass

    def _on_stream_complete(self, full_text: str) -> None:
        """Handles completion of LLM token stream."""
        _logger.debug(f"Queue [STREAM_COMPLETE]: length={len(full_text)}")

    def _on_analysis_success(self, payload: Any) -> None:
        """Handles successful analysis response payload."""
        _logger.info("Queue [ANALYSIS_SUCCESS]: Analysis response received successfully.")

    def _on_analysis_error(self, error_type: str, message: str) -> None:
        """Handles analysis error notifications."""
        _logger.warning(f"Queue [ANALYSIS_ERROR]: type={error_type}, msg='{message}'")

    def _on_analysis_cancelled(self) -> None:
        """Handles worker cancellation notification."""
        _logger.info("Queue [ANALYSIS_CANCELLED]: Pipeline run was cancelled.")

    # =========================================================================
    # Graceful Shutdown Protocol (§9.8 item 6)
    # =========================================================================

    def _on_close(self) -> None:
        """
        Executes graceful shutdown protocol per §9.8 item 6:
        1. Cancels any active queue polling job.
        2. Signals active worker thread cancellation and joins up to 3.0s.
        3. Saves current window coordinates and dimensions to config.json.
        4. Destroys the main window and terminates the Tk event loop.
        """
        _logger.info("PRISMApp shutdown initiated...")

        # 1. Cancel queue polling
        if self._poll_job_id:
            try:
                self.after_cancel(self._poll_job_id)
            except Exception:
                pass
            self._poll_job_id = None

        # 2. Preempt and join worker thread if active
        if self._worker and self._worker.is_running:
            _logger.info("Active worker thread detected on close; signaling cancellation...")
            try:
                self._worker.cancel()
            except Exception as e:
                _logger.warning(f"Error during worker cancellation on close: {e}")

        # 3. Persist window geometry
        self._save_geometry()

        # 4. Quit mainloop and destroy window
        try:
            self.quit()
            self.destroy()
            _logger.info("PRISMApp window destroyed cleanly.")
        except Exception as e:
            _logger.warning(f"Error destroying window: {e}")

    def destroy(self) -> None:
        """Cleanly cancels scheduled polling jobs prior to window destruction."""
        if self._poll_job_id:
            try:
                self.after_cancel(self._poll_job_id)
            except Exception:
                pass
            self._poll_job_id = None
        super().destroy()

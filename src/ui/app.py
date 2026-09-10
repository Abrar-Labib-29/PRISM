"""
iValue PRISM — Main Application Window (PRISMApp)
SRS References: §8.1.1, §8.1.4, §8.1.5, §8.1.6, §8.1.8, §8.1.9, §8.1.10, §8.1.12, §8.1.14, §8.1.15, §9.8, §9.9, §10.6, §10.7
Implementation Plan: TASK-P3.3, TASK-P3.4, TASK-P4.1, TASK-P4.2, TASK-P4.3, TASK-P4.4, TASK-P5.1

This module implements the root desktop window (PRISMApp) for iValue PRISM.
It coordinates:
  - Single-root desktop architecture and layout chrome (§8.1.1, §8.1.4)
  - Left navigation & system control center (SidebarView) (§8.1.5 item 1)
  - Requirement & RFP input area (RequirementInputPanel) (§8.1.5 item 2)
  - Zero-state guidance templates (WelcomeView) (§8.1.8)
  - Live token streaming terminal & pipeline stepper (TokenStreamTerminal) (§8.1.5 item 3)
  - Results verdict & recommendation cards (ResultsCanvas) (§8.1.5 item 4)
  - Interactive tksheet BOM/BOQ export panel (ExportControlPanel) (§8.1.5 item 5)
  - Sliding non-blocking toast notification manager (ToastNotificationManager) (§8.1.9)
  - Extracted document review & edit modal (DocumentPreviewModal) (§8.1.12)
  - Window state persistence & boundary self-healing (§8.1.6, §10.6)
  - Asynchronous message queue polling and thread-safe worker lifecycle (§9.8, §9.9)
"""
from __future__ import annotations

import logging
import os
import pathlib
import queue
import re
import sys
import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import customtkinter

if TYPE_CHECKING:
    from src.core.service import PrismService
    from src.core.worker import WorkerThread

from src.core.service import AnalyzeRequest, AnalyzeResponse, ProductRecommendation
from src.ui.components.export_panel import ExportControlPanel
from src.ui.components.input_panel import RequirementInputPanel
from src.ui.components.result_cards import ResultsCanvas
from src.ui.components.sidebar import SessionSnapshot, SidebarView
from src.ui.components.stream_box import TokenStreamTerminal
from src.ui.components.toast import ToastNotificationManager
from src.ui.components.welcome import WelcomeView
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
    mounts child components, dispatches background worker tasks, and drains the
    thread-safe queue.Queue.
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
        self._build_components()
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
        Attaches the initialized PrismService façade post-splash and wires the WorkerThread and Sidebar.
        """
        self._service = service
        if not self._worker:
            from src.core.worker import WorkerThread
            self._worker = WorkerThread(self._service, self._ui_queue)
        else:
            self._worker._service = service

        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar._service = service
            self.sidebar.refresh_health()

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

    def _build_components(self) -> None:
        """
        Instantiates and wires all primary UI subcomponents into root containers (§8.1.5):
        - SidebarView in sidebar_frame
        - ToastNotificationManager on root
        - RequirementInputPanel on top of main_canvas_frame
        - Dynamic workspace area (WelcomeView, TokenStreamTerminal, ResultsCanvas)
        - ExportControlPanel at bottom of main_canvas_frame
        """
        # 1. Toast Notification Manager anchored to root window (§8.1.9)
        self.toast_mgr = ToastNotificationManager(self)

        # 2. Navigation & System Control Sidebar (§8.1.5 item 1)
        self.sidebar = SidebarView(
            self.sidebar_frame,
            service=self._service,
            config=self.config_manager,
        )
        self.sidebar.pack(fill="both", expand=True)
        self.sidebar.set_on_new_query(self._on_new_query)
        self.sidebar.set_on_clear_workspace(self._on_clear_workspace)
        self.sidebar.set_on_session_restore(self._on_session_restore)
        self.sidebar.set_on_reindex(self._on_reindex)

        # 3. Requirement & RFP Input Panel (§8.1.5 item 2)
        self.input_panel = RequirementInputPanel(self.main_canvas_frame)
        self.input_panel.pack(fill="x", pady=(0, 16))
        self.input_panel.set_on_analyze(self._on_start_analysis)
        self.input_panel.set_on_cancel(self._on_cancel_analysis)
        self.input_panel.set_on_file_load(self._on_file_loaded)

        # 4. Dynamic Middle Workspace (Zero-state / Stream Box / Results Canvas)
        self.workspace_frame = customtkinter.CTkFrame(self.main_canvas_frame, fg_color="transparent")
        self.workspace_frame.pack(fill="both", expand=True)

        # Zero-State Guidance View (§8.1.8)
        self.welcome_view = WelcomeView(
            self.workspace_frame,
            on_template_select=self._on_template_selected,
        )
        self.welcome_view.pack(fill="both", expand=True)

        # Live Token Streaming & Stepper Terminal (§8.1.5 item 3)
        self.stream_box = TokenStreamTerminal(self.workspace_frame)
        # Hidden initially; shown during active analysis

        # Results Canvas (Verdict header + recommendation cards) (§8.1.5 item 4)
        self.results_canvas = ResultsCanvas(self.workspace_frame)
        self.results_canvas.set_on_accept(self._on_card_accept_toggle)
        self.results_canvas.set_on_modify(self._on_card_modify)
        self.results_canvas.set_on_reject(self._on_card_reject)
        # Hidden initially; shown on analysis success

        # 5. Interactive tksheet BOM/BOQ Export Panel (§8.1.5 item 5)
        self.export_panel = ExportControlPanel(
            self.main_canvas_frame,
            toast_manager=self.toast_mgr,
            on_export_bom=self._on_bom_exported,
            on_export_boq=self._on_boq_exported,
        )
        # Starts hidden by default until at least one candidate is accepted

    # =========================================================================
    # User Action Callbacks & Component Orchestration
    # =========================================================================

    def _on_template_selected(self, template_text: str) -> None:
        """Pours starter template text directly into requirement input box (§8.1.8)."""
        self.input_panel.set_text(template_text)

    def _on_start_analysis(self, requirement_text: str) -> None:
        """Dispatches engineer requirement to background WorkerThread pipeline (§9.8, §9.9)."""
        if not self._service:
            self.toast_mgr.show("Core RAG service not ready or initialized.", variant="error")
            self.input_panel.set_analyzing(False)
            return

        if not self._worker:
            from src.core.worker import WorkerThread
            self._worker = WorkerThread(self._service, self._ui_queue)

        if self._worker.is_running:
            self.toast_mgr.show("An analysis operation is already in progress.", variant="warning")
            return

        # Update UI state for analysis execution
        self.input_panel.set_analyzing(True)
        self.welcome_view.pack_forget()
        self.results_canvas.pack_forget()
        self.stream_box.reset()
        self.stream_box.show()
        self.stream_box.set_step(1, "running")

        req = AnalyzeRequest(query_text=requirement_text)
        self._worker.start_analysis(req)

    def _on_cancel_analysis(self) -> None:
        """Preempts running pipeline thread upon engineer request (§9.9)."""
        if self._worker and self._worker.is_running:
            self._worker.cancel()

        self.input_panel.set_analyzing(False)
        self.stream_box.reset()
        self.stream_box.hide()
        if not self.results_canvas.winfo_ismapped():
            self.welcome_view.pack(fill="both", expand=True)

        self.toast_mgr.show("Analysis run cancelled.", variant="info")

    def _on_file_loaded(self, file_path: str) -> None:
        """Extracts text from uploaded RFP document and presents preview modal (§8.1.12)."""
        try:
            from src.core.ingestion import DocumentParser
            parser = DocumentParser()
            result = parser.parse_file(file_path)
            if not result.success:
                self.toast_mgr.show(f"Document extraction failed: {result.error_message}", variant="error")
                return

            from src.ui.components.extraction_modal import DocumentPreviewModal
            DocumentPreviewModal(
                self,
                extraction_result=result,
                on_confirm=lambda text: self.input_panel.set_text(text),
            )
        except Exception as e:
            _logger.error(f"Error opening document preview modal: {e}", exc_info=True)
            self.toast_mgr.show(f"Failed to open document: {e}", variant="error")

    def _on_card_accept_toggle(self, rec: ProductRecommendation, is_accepted: bool) -> None:
        """Syncs candidate recommendation acceptance state with BOM/BOQ export grid (§8.1.5 item 5)."""
        if is_accepted:
            self.export_panel.add_product(rec)
            self.toast_mgr.show(f"Added '{rec.product_name}' to export proposal.", variant="info")
        else:
            self.export_panel.remove_product(rec.product_id)
            self.toast_mgr.show(f"Removed '{rec.product_name}' from export proposal.", variant="info")

    def _on_card_modify(self, rec: ProductRecommendation, new_rationale: str) -> None:
        """Logs rationale update made by engineer in-place (§8.1.14)."""
        _logger.debug(f"Rationale modified for {rec.product_id}")

    def _on_card_reject(self, rec: ProductRecommendation, reason: str) -> None:
        """Handles candidate exclusion/rejection (§8.1.14)."""
        self.export_panel.remove_product(rec.product_id)
        self.toast_mgr.show(f"Excluded '{rec.product_name}': {reason}", variant="warning")

    def _on_bom_exported(self, file_path: str) -> None:
        """Handles successful BOM export event."""
        _logger.info(f"BOM exported successfully to: {file_path}")

    def _on_boq_exported(self, file_path: str) -> None:
        """Handles successful BOQ export event."""
        _logger.info(f"BOQ exported successfully to: {file_path}")

    def _on_new_query(self) -> None:
        """Resets input and workspace for a fresh requirement (§8.1.5 item 1)."""
        self.input_panel.clear()
        self.stream_box.reset()
        self.stream_box.hide()
        self.results_canvas.clear()
        self.results_canvas.pack_forget()
        self.welcome_view.pack(fill="both", expand=True)

    def _on_clear_workspace(self) -> None:
        """Fully clears all requirement, results, and export panel state (§8.1.5 item 1)."""
        self.input_panel.clear()
        self.stream_box.reset()
        self.stream_box.hide()
        self.results_canvas.clear()
        self.results_canvas.pack_forget()
        self.export_panel.clear_all()
        self.welcome_view.pack(fill="both", expand=True)
        self.toast_mgr.show("Workspace cleared.", variant="info")

    def _on_session_restore(self, snapshot: SessionSnapshot) -> None:
        """Restores past session requirement and recommendation cards from sidebar reel (§8.1.5 item 1)."""
        self.input_panel.set_text(snapshot.requirement_text)
        self.welcome_view.pack_forget()
        self.stream_box.reset()
        self.stream_box.hide()
        if snapshot.response:
            self.results_canvas.show_results(snapshot.response)
            self.results_canvas.pack(fill="both", expand=True)
        self.toast_mgr.show(f"Session {snapshot.query_id[:8]} restored.", variant="info")

    def _on_reindex(self) -> None:
        """Dispatches catalog re-indexing in background (§8.1.5 item 1)."""
        self.toast_mgr.show("Refreshing catalog index...", variant="info")
        if self._service and hasattr(self._service, "retriever"):
            def _reindex_worker():
                try:
                    self._service.retriever.reload_index()
                    self.after(0, lambda: self.toast_mgr.show("Catalog index refreshed successfully.", variant="success"))
                    self.after(0, self.sidebar.refresh_health)
                except Exception as exc:
                    self.after(0, lambda: self.toast_mgr.show(f"Re-index failed: {exc}", variant="error"))
            threading.Thread(target=_reindex_worker, daemon=True).start()

    # =========================================================================
    # Geometry & Window State Persistence
    # =========================================================================

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

        # Bound check against screen size if display is smaller than default
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
    # Queue Handlers
    # =========================================================================

    def _on_status_step(self, step: int, label: str) -> None:
        """Handles RAG pipeline progress step updates."""
        _logger.debug(f"Queue [STATUS_STEP]: step={step}, label='{label}'")
        if hasattr(self, "stream_box") and self.stream_box:
            for s in range(1, step):
                self.stream_box.set_step(s, "completed")
            self.stream_box.set_step(step, "running")

    def _on_stream_token(self, token: str) -> None:
        """Handles incoming streamed tokens from Ollama LLM."""
        if hasattr(self, "stream_box") and self.stream_box:
            self.stream_box.append_token(token)

    def _on_stream_complete(self, full_text: str) -> None:
        """Handles completion of LLM token stream."""
        _logger.debug(f"Queue [STREAM_COMPLETE]: length={len(full_text)}")
        if hasattr(self, "stream_box") and self.stream_box:
            self.stream_box.set_step(3, "completed")

    def _on_analysis_success(self, payload: Any) -> None:
        """Handles successful analysis response payload."""
        _logger.info("Queue [ANALYSIS_SUCCESS]: Analysis response received successfully.")
        if hasattr(self, "input_panel") and self.input_panel:
            self.input_panel.set_analyzing(False)

        if hasattr(self, "stream_box") and self.stream_box:
            for s in range(1, 4):
                self.stream_box.set_step(s, "completed")
            self.stream_box.hide()

        if hasattr(self, "welcome_view") and self.welcome_view:
            self.welcome_view.pack_forget()

        if hasattr(self, "results_canvas") and self.results_canvas and isinstance(payload, AnalyzeResponse):
            self.results_canvas.show_results(payload)
            self.results_canvas.pack(fill="both", expand=True)

            if payload.recommendations:
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.add_session(
                        query_id=payload.query_id,
                        query_text=self.input_panel.get_text(),
                        response=payload,
                    )
                if hasattr(self, "toast_mgr") and self.toast_mgr:
                    self.toast_mgr.show(
                        f"Identified {len(payload.recommendations)} candidate recommendation(s).",
                        variant="success",
                    )
            else:
                if hasattr(self, "toast_mgr") and self.toast_mgr:
                    self.toast_mgr.show(
                        "No catalog products met the requirement criteria.",
                        variant="warning",
                    )

    def _on_analysis_error(self, error_type: str, message: str) -> None:
        """Handles analysis error notifications."""
        _logger.warning(f"Queue [ANALYSIS_ERROR]: type={error_type}, msg='{message}'")
        if hasattr(self, "input_panel") and self.input_panel:
            self.input_panel.set_analyzing(False)
        if hasattr(self, "stream_box") and self.stream_box:
            self.stream_box.hide()
        if hasattr(self, "results_canvas") and hasattr(self, "welcome_view"):
            if not self.results_canvas.winfo_ismapped():
                self.welcome_view.pack(fill="both", expand=True)
        if hasattr(self, "toast_mgr") and self.toast_mgr:
            self.toast_mgr.show(f"Analysis Error: {message}", variant="error")

    def _on_analysis_cancelled(self) -> None:
        """Handles worker cancellation notification."""
        _logger.info("Queue [ANALYSIS_CANCELLED]: Pipeline run was cancelled.")
        if hasattr(self, "input_panel") and self.input_panel:
            self.input_panel.set_analyzing(False)
        if hasattr(self, "stream_box") and self.stream_box:
            self.stream_box.hide()
        if hasattr(self, "results_canvas") and hasattr(self, "welcome_view"):
            if not self.results_canvas.winfo_ismapped():
                self.welcome_view.pack(fill="both", expand=True)
        if hasattr(self, "toast_mgr") and self.toast_mgr:
            self.toast_mgr.show("Pipeline cancelled.", variant="info")

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

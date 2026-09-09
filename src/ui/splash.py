"""
iValue PRISM — Cold-Start Splash Screen & Model Preloader (Phase B)
SRS References: §8.1.7, §8.1.7a, §9.7, §9.9, §12.7 (STR-10)
Implementation Plan: TASK-P3.2

This module implements the Phase B in-process splash preloader window.
It hands off immediately from the Phase A PyInstaller C-bootloader splash
(pyi_splash.close()) and presents a 4-line live initialization checklist
with timing benchmarks before executing a 300ms cross-fade to the main app.
"""

import logging
import pathlib
import sys
import time
from typing import Callable, Dict, Optional

import customtkinter
from PIL import Image

_logger = logging.getLogger("prism.ui.splash")

# Step labels and defaults per SRS §8.1.7
DEFAULT_STEPS: Dict[int, str] = {
    1: "Python desktop runtime initialized",
    2: "Semantic vector index mounted (139 OEM products)",
    3: "Sentence-transformers embedding model loaded",
    4: "Verifying Ollama daemon & warming Phi-4-mini neural model",
}

SPLASH_WIDTH = 480
SPLASH_HEIGHT = 340
BACKGROUND_COLOR = "#0B1120"
BORDER_COLOR = "#1E293B"
ACCENT_COLOR = "#0EA5E9"
SUCCESS_COLOR = "#10B981"
PENDING_COLOR = "#64748B"
TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"


def _get_asset_path(relative_path: str) -> pathlib.Path:
    """Resolves asset path for both dev environment and PyInstaller bundle."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return pathlib.Path(base_path) / relative_path
    return pathlib.Path(__file__).resolve().parent.parent.parent / relative_path


class SplashPreloader(customtkinter.CTkToplevel):
    """
    Phase B in-process splash preloader window (§8.1.7, §8.1.7a).
    Provides visual feedback while neural models, indexes, and daemons warm up.
    """

    def __init__(self, master=None) -> None:
        # Phase A → Phase B Handoff per §8.1.7a
        # Must be called immediately to dismiss the static C-bootloader splash
        try:
            import pyi_splash
            pyi_splash.update_text("Initializing PRISM Core Engine...")
            pyi_splash.close()
            _logger.info("Successfully handed off from pyi_splash C-bootloader.")
        except ImportError:
            pass  # Not running inside a packaged PyInstaller binary (dev mode)
        except Exception as e:
            _logger.warning(f"pyi_splash.close() encountered: {e}")

        super().__init__(master)

        self._is_closing = False
        self._checklist_labels: Dict[int, customtkinter.CTkLabel] = {}

        self._configure_window()
        self._build_ui()

    def _configure_window(self) -> None:
        """Configures borderless, centered, modal-like splash window geometry."""
        self.overrideredirect(True)
        self.configure(fg_color=BACKGROUND_COLOR)

        # Center on primary display
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        pos_x = (screen_width - SPLASH_WIDTH) // 2
        pos_y = (screen_height - SPLASH_HEIGHT) // 2
        self.geometry(f"{SPLASH_WIDTH}x{SPLASH_HEIGHT}+{pos_x}+{pos_y}")

        # Ensure splash stays on top of other windows
        self.attributes("-topmost", True)

    def _build_ui(self) -> None:
        """Constructs splash UI elements: logo, title, progress bar, and checklist."""
        # Outer container card with subtle border
        self._container = customtkinter.CTkFrame(
            self,
            width=SPLASH_WIDTH,
            height=SPLASH_HEIGHT,
            fg_color=BACKGROUND_COLOR,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=12,
        )
        self._container.pack(fill="both", expand=True, padx=0, pady=0)
        self._container.pack_propagate(False)

        # 1. 96x96 Logo graphic (or text fallback)
        logo_path = _get_asset_path("assets/branding/ivalue_prism_logo.jpg")
        logo_loaded = False

        if logo_path.exists():
            try:
                pil_img = Image.open(logo_path)
                logo_ctk = customtkinter.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(96, 96),
                )
                self._logo_label = customtkinter.CTkLabel(
                    self._container,
                    image=logo_ctk,
                    text="",
                )
                self._logo_label.pack(pady=(16, 4))
                logo_loaded = True
            except Exception as exc:
                _logger.warning(f"Could not load branding logo at {logo_path}: {exc}")

        if not logo_loaded:
            # Styled refractive glyph fallback
            self._logo_label = customtkinter.CTkLabel(
                self._container,
                text="▲",
                font=customtkinter.CTkFont(family="Segoe UI", size=54, weight="bold"),
                text_color=ACCENT_COLOR,
            )
            self._logo_label.pack(pady=(16, 4))

        # 2. Title & Subtitle (§8.1.3 Display 24pt Bold, Body Regular 11pt)
        self._title_label = customtkinter.CTkLabel(
            self._container,
            text="iValue PRISM",
            font=customtkinter.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        self._title_label.pack(pady=(0, 2))

        self._subtitle_label = customtkinter.CTkLabel(
            self._container,
            text="Presales Recommendation & Intelligence System",
            font=customtkinter.CTkFont(family="Segoe UI", size=11, weight="normal"),
            text_color=TEXT_SECONDARY,
        )
        self._subtitle_label.pack(pady=(0, 12))

        # 3. Indeterminate progress bar (#0EA5E9)
        self._progress_bar = customtkinter.CTkProgressBar(
            self._container,
            mode="indeterminate",
            width=360,
            height=4,
            corner_radius=2,
            fg_color="#1E293B",
            progress_color=ACCENT_COLOR,
        )
        self._progress_bar.pack(pady=(0, 14))
        self._progress_bar.start()

        # 4. 4-line initialization checklist container
        self._checklist_frame = customtkinter.CTkFrame(
            self._container,
            fg_color="transparent",
            width=380,
        )
        self._checklist_frame.pack(fill="x", padx=48, pady=(0, 10))

        # Render 4 pending items initially
        mono_font = customtkinter.CTkFont(family="Cascadia Mono", size=10, weight="normal")
        for step_idx in range(1, 5):
            lbl_text = f"[·] {DEFAULT_STEPS[step_idx]}..."
            lbl = customtkinter.CTkLabel(
                self._checklist_frame,
                text=lbl_text,
                font=mono_font,
                text_color=PENDING_COLOR,
                anchor="w",
                justify="left",
            )
            lbl.pack(fill="x", pady=1)
            self._checklist_labels[step_idx] = lbl

    def update_step(self, step: int, label: Optional[str] = None, elapsed: float = 0.0) -> None:
        """
        Updates checklist item to in-progress or completed checkmark with timing (§8.1.7).
        - If elapsed >= 0: Marks completed '[✓] {label} ({elapsed:.1f}s)' in green.
        - If elapsed < 0:  Marks in-progress '[⟳] {label}...' in sky blue.
        """
        if step not in self._checklist_labels:
            _logger.debug(f"Unknown step index {step} provided to update_step.")
            return

        target_label = label or DEFAULT_STEPS.get(step, f"Step {step}")
        lbl_widget = self._checklist_labels[step]

        if elapsed >= 0.0:
            formatted_text = f"[✓] {target_label} ({elapsed:.1f}s)"
            lbl_widget.configure(text=formatted_text, text_color=SUCCESS_COLOR)
        else:
            formatted_text = f"[⟳] {target_label}..."
            lbl_widget.configure(text=formatted_text, text_color=ACCENT_COLOR)

        self.update_idletasks()

    def finish(self, callback: Optional[Callable[[], None]] = None) -> None:
        """
        Executes 300ms cross-fade animation, destroys splash window,
        and invokes completion callback (§8.1.7).
        """
        if self._is_closing:
            return
        self._is_closing = True

        try:
            self._progress_bar.stop()
        except Exception:
            pass

        # Check accessibility preference for reduced motion
        reduced_motion = False
        try:
            from src.utils.system_info import check_reduced_motion
            reduced_motion = check_reduced_motion()
        except Exception:
            pass

        if reduced_motion:
            _logger.info("Reduced motion active: skipping 300ms cross-fade.")
            self._cleanup(callback)
            return

        # 300ms cross-fade: 10 steps of 30ms decreasing alpha from 1.0 to 0.0
        total_steps = 10
        step_interval_ms = 30  # 10 * 30ms = 300ms total
        for i in range(1, total_steps + 1):
            alpha = max(0.0, 1.0 - (i / total_steps))
            if i < total_steps:
                self.after(i * step_interval_ms, lambda a=alpha: self._set_alpha(a))
            else:
                self.after(total_steps * step_interval_ms, lambda: self._cleanup(callback))

    def _set_alpha(self, alpha: float) -> None:
        """Safely updates window alpha during cross-fade."""
        try:
            if self.winfo_exists():
                self.attributes("-alpha", alpha)
        except Exception:
            pass

    def _cleanup(self, callback: Optional[Callable[[], None]]) -> None:
        """Destroys splash window and triggers main application callback."""
        try:
            if self.winfo_exists():
                self.destroy()
        except Exception as e:
            _logger.warning(f"Error destroying splash window: {e}")

        if callback:
            try:
                callback()
            except Exception as e:
                _logger.error(f"Error executing splash finish callback: {e}", exc_info=True)

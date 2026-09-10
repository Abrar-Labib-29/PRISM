"""
iValue PRISM — Application Entry Point
SRS References: §8.1.1, §8.1.7, §8.1.7a, §9.7, §9.8, §9.9, §10.6, §10.7, §12.7 (STR-10)
Implementation Plan: TASK-P3.3

1. Windows AppUserModelID registration (§8.1.1)
2. Single-instance named mutex guard (§10.7)
3. CustomTkinter theme & appearance configuration (§8.1.2, §8.1.13)
4. Phase B Splash preloader & background initialization handoff (§8.1.7)
5. PRISMApp main window lifecycle and graceful exit (§8.1.1, §9.8)
"""

import logging
import os
import pathlib
import sys
import threading
import time

import customtkinter

from src.ui.app import PRISMApp
from src.ui.splash import DEFAULT_STEPS, SplashPreloader
from src.utils.config import ConfigManager
from src.utils.system_info import release_single_instance, verify_single_instance

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger("prism.main")

APP_USER_MODEL_ID = "iValue.PRISM.PresalesDesktop.v3"


def _get_asset_path(relative_path: str) -> pathlib.Path:
    """Resolves asset path for both development mode and PyInstaller frozen bundle."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return pathlib.Path(base_path) / relative_path
    return pathlib.Path(__file__).resolve().parent / relative_path


def _register_app_user_model_id() -> None:
    """Registers explicit Windows AppUserModelID for taskbar pinning and grouping (§8.1.1)."""
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
            _logger.info(f"Registered Windows AppUserModelID: '{APP_USER_MODEL_ID}'")
        except Exception as e:
            _logger.debug(f"Could not register AppUserModelID: {e}")


def main() -> None:
    """Application main entry point."""
    # Native C-bootloader splash handoff (§8.1.7a, STR-10)
    try:
        import pyi_splash
        pyi_splash.update_text("Initializing PRISM Core Engine...")
        pyi_splash.close()
    except ImportError:
        pass

    _logger.info("Starting iValue PRISM Desktop Application...")

    # 1. Register AppUserModelID (§8.1.1)
    _register_app_user_model_id()

    # 2. Single-Instance Named Mutex Guard (§10.7, INT-14)
    if not verify_single_instance():
        _logger.warning("Another instance of iValue PRISM is already running. Terminating.")
        try:
            import tkinter.messagebox as msgbox
            msgbox.showwarning(
                "iValue PRISM Already Running",
                "Another instance of iValue PRISM is already running on this workstation.\n\n"
                "Only one instance is permitted at a time to prevent resource contention.",
            )
        except Exception:
            pass
        sys.exit(0)

    try:
        # 3. Load user configuration & apply appearance mode and color theme (§8.1.2, §8.1.13)
        config = ConfigManager()
        appearance_mode = config.get("appearance_mode", "dark")
        customtkinter.set_appearance_mode(appearance_mode)

        theme_path = _get_asset_path("themes/ivalue_prism.json")
        if theme_path.exists():
            customtkinter.set_default_color_theme(str(theme_path))
            _logger.info(f"Loaded CustomTkinter theme from: {theme_path}")
        else:
            _logger.warning(f"Theme file not found at '{theme_path}', using default theme.")

        # 4. Single-Root Architecture: Instantiate hidden PRISMApp first
        app = PRISMApp(service=None, config=config)
        app.withdraw()

        # Fast dev/testing bypass option
        if "--no-splash" in sys.argv:
            _logger.info("Bypassing splash screen (--no-splash detected)...")
            from src.core.service import PrismService
            service = PrismService()
            app.set_service(service)
            app.deiconify()
            app.lift()
            app.focus_force()
            app.mainloop()
            return

        # 5. Phase B Splash Preloader parented to root CTk window (§8.1.7)
        splash = SplashPreloader(master=app)

        # 6. Background thread for model loading and RAG pipeline initialization
        def _background_init() -> None:
            try:
                # Step 1: Runtime initialized
                t_start = time.time()
                time.sleep(0.05)  # Ensure splash UI is rendered
                app.after(
                    0,
                    splash.update_step,
                    1,
                    DEFAULT_STEPS[1],
                    round(time.time() - t_start, 2),
                )

                # Step 2: Semantic vector index & Core Service loading
                t_retriever = time.time()
                app.after(
                    0,
                    splash.update_step,
                    2,
                    "Mounting semantic vector index (139 OEM products)...",
                    -1.0,
                )

                # Instantiating PrismService loads embeddings, metadata, and initializes managers
                from src.core.service import PrismService
                service = PrismService()
                retriever_elapsed = round(max(0.1, time.time() - t_retriever), 2)
                app.after(
                    0,
                    splash.update_step,
                    2,
                    DEFAULT_STEPS[2],
                    retriever_elapsed,
                )

                # Step 3: Sentence-transformers embedding model loaded
                app.after(
                    0,
                    splash.update_step,
                    3,
                    DEFAULT_STEPS[3],
                    0.1,
                )

                # Step 4: Verifying Ollama daemon & model
                app.after(
                    0,
                    splash.update_step,
                    4,
                    DEFAULT_STEPS[4],
                    0.1,
                )

                # Smooth transition to main app window post-splash
                def _on_splash_done() -> None:
                    _logger.info("Splash preloader finished. Presenting main application window.")
                    app.set_service(service)
                    app.deiconify()
                    app.lift()
                    app.focus_force()

                # Trigger 300ms cross-fade and destruction of splash
                app.after(100, lambda: splash.finish(callback=_on_splash_done))

            except Exception as e:
                _logger.critical(f"CRITICAL: Application startup initialization failed: {e}", exc_info=True)

                def _show_fatal_startup_error() -> None:
                    try:
                        import tkinter.messagebox as msgbox
                        msgbox.showerror(
                            "iValue PRISM — Startup Failure",
                            f"iValue PRISM failed to start:\n\n{e}\n\nPlease check the application logs.",
                        )
                    except Exception:
                        pass
                    try:
                        splash.destroy()
                    except Exception:
                        pass
                    try:
                        app.destroy()
                    except Exception:
                        pass
                    release_single_instance()
                    sys.exit(1)

                app.after(0, _show_fatal_startup_error)

        init_thread = threading.Thread(
            target=_background_init,
            name="PrismStartupThread",
            daemon=True,
        )
        init_thread.start()

        # 7. Start Tk main event loop
        app.mainloop()

    finally:
        # Mutex handle release on exit (§10.7)
        release_single_instance()
        _logger.info("iValue PRISM exited.")


if __name__ == "__main__":
    main()

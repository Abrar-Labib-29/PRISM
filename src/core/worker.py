"""
iValue PRISM — Background Worker Thread & Queue Dispatcher
SRS References: §9.8, §9.9, §10.6, §10.7, §9.10 item 4
Implementation Plan: TASK-P2.1

This module implements the asynchronous execution bridge between the desktop UI
and the synchronous PrismService pipeline.
All heavy operations (document extraction, vector embedding, similarity search,
Ollama token streaming, safety validation) execute on background daemon threads.
State and token updates are passed to the UI thread via a thread-safe queue.Queue.
"""

import logging
import queue
import threading
import time
from typing import Any, Dict, Optional

from src.core.service import AnalyzeRequest, AnalyzeResponse, PrismService

_logger = logging.getLogger("prism.worker")

# 3-Step Stepper Labels per §9.10 & §9.8
STEP_1_LABEL = "Scanning catalog & embedding requirement..."
STEP_2_LABEL = "Applying taxonomy filters & assembling context budget..."
STEP_3_LABEL = "Streaming grounded recommendation from Phi-4-mini..."
PREEMPTION_LABEL = "Cancelling active analysis..."


class WorkerThread:
    """
    Background daemon thread dispatcher for RAG pipeline execution (§9.8, §9.9).
    Guarantees that compute-intensive operations never block the main UI thread.
    """

    def __init__(self, service: PrismService, ui_queue: queue.Queue) -> None:
        """
        Initializes dispatcher with service contract and destination UI queue.
        """
        self._service = service
        self._queue = ui_queue
        self._cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """Returns True if a worker daemon is currently active."""
        with self._lock:
            return self._is_running and (self._thread is not None and self._thread.is_alive())

    def start_analysis(self, request: AnalyzeRequest) -> None:
        """
        Dispatches a new analysis on a background daemon thread (§9.8 items 1-2).
        If a thread is already running, preempts it per §9.8 item 5 (H-6):
          1. Sets cancel_event
          2. Emits status notice to UI queue
          3. Joins running thread up to 2.0s
          4. Resets cancellation state
          5. Starts new daemon thread
        """
        thread_to_join = None
        with self._lock:
            if self._thread and self._thread.is_alive():
                _logger.info("Active worker thread detected. Triggering preemption flow (H-6)...")
                self._cancel_event.set()
                self._queue.put({
                    "type": "STATUS_STEP",
                    "step": 1,
                    "label": PREEMPTION_LABEL,
                })
                thread_to_join = self._thread

        if thread_to_join:
            thread_to_join.join(timeout=2.0)
            if thread_to_join.is_alive():
                _logger.warning("Previous worker did not terminate within 2.0s join timeout; proceeding.")

        with self._lock:
            # Reset cancellation state for new execution
            self._cancel_event.clear()
            self._is_running = True

            self._thread = threading.Thread(
                target=self._run,
                args=(request,),
                name="PrismWorkerThread",
                daemon=True,  # Crucial: daemon=True prevents process hang on window exit
            )
            self._thread.start()
            _logger.info(f"Dispatched new worker thread: {self._thread.name}")

    def cancel(self) -> None:
        """
        Sets cancel_event and waits up to 2.0s for the running thread to terminate cleanly (§10.7).
        """
        thread_to_join = None
        with self._lock:
            if not (self._thread and self._thread.is_alive()):
                self._is_running = False
                return

            _logger.info("Cancellation requested by user. Signaling worker thread...")
            self._cancel_event.set()
            thread_to_join = self._thread

        if thread_to_join:
            thread_to_join.join(timeout=2.0)

        with self._lock:
            self._is_running = False
            _logger.info("Worker thread cancelled and joined.")

    def _run(self, request: AnalyzeRequest) -> None:
        """
        Worker thread main entry point.
        Wrapped in a global try/except block per §10.6 to prevent silent thread death.
        Emits standardized dictionary envelope messages (§9.10 item 4):
          - {"type": "STATUS_STEP", "step": 1|2|3, "label": "..."}
          - {"type": "STREAM_TOKEN", "token": "..."}
          - {"type": "STREAM_COMPLETE", "full_text": "..."}
          - {"type": "ANALYSIS_SUCCESS", "payload": AnalyzeResponse}
          - {"type": "ANALYSIS_ERROR", "error_type": "TIMEOUT"|"OOM"|"NETWORK"|"GENERAL", "message": "..."}
          - {"type": "ANALYSIS_CANCELLED"}
        """
        full_tokens: list[str] = []

        try:
            # Step 1: Catalog Scan & Embedding
            if self._cancel_event.is_set():
                self._post_cancelled()
                return

            self._queue.put({
                "type": "STATUS_STEP",
                "step": 1,
                "label": STEP_1_LABEL,
            })

            # Step 2: Context Assembly & Filtering
            if self._cancel_event.is_set():
                self._post_cancelled()
                return

            self._queue.put({
                "type": "STATUS_STEP",
                "step": 2,
                "label": STEP_2_LABEL,
            })

            # Step 3: LLM Inference & Generation
            if self._cancel_event.is_set():
                self._post_cancelled()
                return

            self._queue.put({
                "type": "STATUS_STEP",
                "step": 3,
                "label": STEP_3_LABEL,
            })

            def _token_callback(token_str: str) -> None:
                """Pushes streaming token chunks to UI queue."""
                if not self._cancel_event.is_set():
                    full_tokens.append(token_str)
                    self._queue.put({
                        "type": "STREAM_TOKEN",
                        "token": token_str,
                    })

            # Execute full pipeline through PrismService façade
            response: AnalyzeResponse = self._service.analyze(
                req=request,
                token_stream_callback=_token_callback,
                cancel_event=self._cancel_event,
            )

            # Check if user cancelled during analysis
            if self._cancel_event.is_set() or (
                response.status == "error" and "cancelled" in (response.error_message or "").lower()
            ):
                self._post_cancelled()
                return

            # Check for error status in response
            if response.status == "error":
                err_msg = response.error_message or "An unexpected error occurred during analysis."
                err_type = self._classify_error(err_msg)
                self._queue.put({
                    "type": "ANALYSIS_ERROR",
                    "error_type": err_type,
                    "message": err_msg,
                })
                return

            # Completed generation stream notification
            full_text = "".join(full_tokens)
            if not full_text and response.recommendations:
                full_text = response.recommendations[0].rationale

            self._queue.put({
                "type": "STREAM_COMPLETE",
                "full_text": full_text,
            })

            # Emit final success payload (works for both 'success' and 'zero_results')
            self._queue.put({
                "type": "ANALYSIS_SUCCESS",
                "payload": response,
            })

        except TimeoutError as te:
            _logger.error(f"Worker thread generation timeout: {te}")
            self._queue.put({
                "type": "ANALYSIS_ERROR",
                "error_type": "TIMEOUT",
                "message": f"Generation timed out: {te}",
            })

        except MemoryError as me:
            _logger.critical(f"Worker thread out-of-memory: {me}")
            self._queue.put({
                "type": "ANALYSIS_ERROR",
                "error_type": "OOM",
                "message": "System exhausted available memory during recommendation inference.",
            })

        except Exception as exc:
            _logger.error(f"Unhandled exception in worker thread: {exc}", exc_info=True)
            err_type = self._classify_error(str(exc))
            self._queue.put({
                "type": "ANALYSIS_ERROR",
                "error_type": err_type,
                "message": str(exc),
            })

        finally:
            with self._lock:
                self._is_running = False

    def _post_cancelled(self) -> None:
        """Posts cancellation notice to the UI queue."""
        _logger.info("Worker thread posting ANALYSIS_CANCELLED to UI queue.")
        self._queue.put({"type": "ANALYSIS_CANCELLED"})

    @staticmethod
    def _classify_error(error_text: str) -> str:
        """Maps error message contents to standard error categories (§9.10)."""
        lower = error_text.lower()
        if "timeout" in lower or "timed out" in lower:
            return "TIMEOUT"
        if "memory" in lower or "oom" in lower or "ram" in lower:
            return "OOM"
        if "connection" in lower or "network" in lower or "offline" in lower or "refused" in lower:
            return "NETWORK"
        return "GENERAL"

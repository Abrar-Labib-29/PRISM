"""
iValue PRISM — Structured JSONL Query Logger and Application Logging Module
SRS References: §11.1, §11.3, §11.4
Implementation Plan: TASK-P1.2

This module provides the QueryLogger class for persistent, append-only JSONL logging
of all queries, recommendations, latency metrics, and user feedback actions.
It also configures Python stdlib logging for application events and error tracking.
"""

from datetime import datetime, timezone
import json
import logging
import os
import threading
from typing import Any, Dict, Optional
import uuid

from src.utils.config import FALLBACK_LOG_PATH, PRIMARY_LOG_PATH

# Maximum log file size before rotation (50 MB per §11.1)
MAX_LOG_SIZE_BYTES: int = 50 * 1024 * 1024


def generate_query_id() -> str:
    """Generates a query ID matching format req-xxxxx (§11.1)."""
    return f"req-{uuid.uuid4().hex[:5]}"


def setup_stdlib_logging(log_dir: Optional[str] = None, force: bool = False) -> None:
    """
    Configures Python stdlib logging to write to:
      - prism_app.log (INFO+)
      - prism_error.log (ERROR+)
    Per §11.1, §11.4 and Locked Decision #7.
    """
    root_logger = logging.getLogger("prism")
    root_logger.setLevel(logging.DEBUG)

    if root_logger.handlers and not force and log_dir is None:
        return

    # If re-configuring, close and remove existing file handlers
    if force or (log_dir is not None and root_logger.handlers):
        for h in list(root_logger.handlers):
            h.close()
            root_logger.removeHandler(h)

    if not log_dir:
        # Resolve log_dir based on PRIMARY_LOG_PATH parent or ./logs
        try:
            primary_dir = os.path.dirname(PRIMARY_LOG_PATH)
            if primary_dir:
                os.makedirs(primary_dir, exist_ok=True)
            log_dir = primary_dir
        except Exception:
            fallback_dir = os.path.dirname(os.path.abspath(FALLBACK_LOG_PATH))
            os.makedirs(fallback_dir, exist_ok=True)
            log_dir = fallback_dir
    else:
        os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app_log_path = os.path.join(log_dir, "prism_app.log")
    error_log_path = os.path.join(log_dir, "prism_error.log")

    try:
        app_handler = logging.FileHandler(app_log_path, encoding="utf-8")
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(formatter)
        root_logger.addHandler(app_handler)

        error_handler = logging.FileHandler(error_log_path, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    except Exception as e:
        # Fallback to local ./logs if configured directory fails
        local_logs = os.path.abspath("./logs")
        os.makedirs(local_logs, exist_ok=True)
        app_handler = logging.FileHandler(os.path.join(local_logs, "prism_app.log"), encoding="utf-8")
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(formatter)
        root_logger.addHandler(app_handler)

        error_handler = logging.FileHandler(os.path.join(local_logs, "prism_error.log"), encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)


# Initialize stdlib logging on module import
setup_stdlib_logging()
_sys_logger = logging.getLogger("prism.system")


class QueryLogger:
    """
    Append-only JSONL query and audit logger with log rotation at 50 MB (§11.1).
    Thread-safe implementation for multi-threaded desktop pipeline.
    """

    def __init__(self, log_path: Optional[str] = None, max_bytes: int = MAX_LOG_SIZE_BYTES) -> None:
        self.max_bytes = max_bytes
        self._lock = threading.Lock()

        if log_path:
            self.log_path = log_path
            parent = os.path.dirname(self.log_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        else:
            # Try PRIMARY_LOG_PATH, fall back to FALLBACK_LOG_PATH
            try:
                primary_dir = os.path.dirname(PRIMARY_LOG_PATH)
                if primary_dir:
                    os.makedirs(primary_dir, exist_ok=True)
                # Verify writability
                with open(PRIMARY_LOG_PATH, "a", encoding="utf-8"):
                    pass
                self.log_path = PRIMARY_LOG_PATH
            except Exception:
                fallback_dir = os.path.dirname(os.path.abspath(FALLBACK_LOG_PATH))
                if fallback_dir:
                    os.makedirs(fallback_dir, exist_ok=True)
                self.log_path = os.path.abspath(FALLBACK_LOG_PATH)

    def _check_rotation(self) -> None:
        """
        Rotates current log file if it exceeds max_bytes (default 50 MB).
        Renames current file to query_log_<ISO_DATE>.jsonl and creates an empty log file.
        Archived logs are never deleted.
        """
        if not os.path.exists(self.log_path):
            return

        try:
            if os.path.getsize(self.log_path) >= self.max_bytes:
                # Format ISO timestamp safe for Windows filenames (avoiding ':')
                iso_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                log_dir = os.path.dirname(self.log_path)
                archived_path = os.path.join(log_dir, f"query_log_{iso_date}.jsonl")

                counter = 1
                while os.path.exists(archived_path):
                    archived_path = os.path.join(log_dir, f"query_log_{iso_date}_{counter}.jsonl")
                    counter += 1

                os.rename(self.log_path, archived_path)
                # Initialize new empty file
                with open(self.log_path, "w", encoding="utf-8"):
                    pass
        except Exception as e:
            _sys_logger.error(f"Log rotation error on {self.log_path}: {e}")

    def log_query(self, entry: Dict[str, Any]) -> None:
        """
        Appends one structured JSON object per line. Schema strictly follows SRS §11.1.
        Fills missing fields with standardized schema defaults.
        """
        with self._lock:
            self._check_rotation()

            # Ensure complete schema coverage per §11.1
            payload: Dict[str, Any] = {
                "query_id": entry.get("query_id") or generate_query_id(),
                "timestamp": entry.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                "input_type": entry.get("input_type", "text"),
                "input_text": entry.get("input_text", ""),
                "input_file": entry.get("input_file"),
                "extracted_text": entry.get("extracted_text"),
                "retrieved_products": entry.get("retrieved_products", []),
                "domain_classification": entry.get("domain_classification", ""),
                "generated_text": entry.get("generated_text", ""),
                "fit_score": float(entry.get("fit_score", 0.0)),
                "confidence_level": entry.get("confidence_level", "LOW"),
                "hallucinations_detected": entry.get("hallucinations_detected", []),
                "pricing_mentions_stripped": bool(entry.get("pricing_mentions_stripped", False)),
                "repetition_truncated": bool(entry.get("repetition_truncated", False)),
                "latency": entry.get(
                    "latency",
                    {
                        "embedding_ms": 0,
                        "retrieval_ms": 0,
                        "context_assembly_ms": 0,
                        "ttft_ms": 0,
                        "generation_ms": 0,
                        "validation_ms": 0,
                        "total_ms": 0,
                    },
                ),
                "ram_before_mb": float(entry.get("ram_before_mb", 0.0)),
                "ram_after_mb": float(entry.get("ram_after_mb", 0.0)),
                "user_action": entry.get("user_action"),
                "user_feedback": entry.get("user_feedback"),
                "error": entry.get("error"),
            }

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def log_user_action(self, query_id: str, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Logs user decisions (accept, reject, export_bom, export_boq, re_analyze) per §11.3.
        """
        with self._lock:
            self._check_rotation()

            payload = {
                "type": "USER_ACTION",
                "query_id": query_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_action": action,
                "details": details or {},
            }

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def log_system_event(self, level: str, message: str, **kwargs: Any) -> None:
        """
        Logs system health events, errors, and warnings per §11.4.
        Writes to structured JSONL as well as stdlib loggers.
        """
        upper_level = level.upper()
        # Log to stdlib logger
        log_fn = getattr(_sys_logger, upper_level.lower(), _sys_logger.info)
        log_fn(f"{message} | kwargs={kwargs}")

        with self._lock:
            self._check_rotation()

            payload = {
                "type": "SYSTEM_EVENT",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": upper_level,
                "message": message,
                "details": kwargs,
            }

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

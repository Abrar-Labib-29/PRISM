"""
iValue PRISM — Ollama Service Manager and Streaming Client
SRS References: §9.10, §9.11, §10.4, §2.5
Implementation Plan: TASK-P1.7

This module handles:
  1. OllamaServiceManager: Daemon discovery across standard Windows paths,
     background auto-launch (detached, no console window), model presence verification,
     and model pull tracking.
  2. OllamaStreamingClient: Real-time token streaming via /api/chat with cancellation
     event checking, strict 180s timeout enforcement, and health reporting.
"""

import json
import logging
import os
import shutil
import subprocess
import threading
import time
from typing import Any, Callable, Dict, Generator, List, Optional

import requests

from src.utils.config import (
    ConfigManager,
    NUM_CTX,
    NUM_THREAD,
    OLLAMA_BINARY_PATHS,
    OLLAMA_HOST,
    OLLAMA_MODEL_TAG,
    QUERY_TIMEOUT_SECONDS,
)

_logger = logging.getLogger("prism.ollama")


class OllamaServiceManager:
    """
    Handles Ollama daemon discovery, auto-start, and model presence checks per SRS §9.11.
    """

    def __init__(self, host: str = OLLAMA_HOST) -> None:
        self.host = host.rstrip("/")
        self.config_manager = ConfigManager()

    def is_online(self) -> bool:
        """
        Pings GET /api/tags with a 1.0s timeout (§9.11 step 1).
        Returns True if the daemon responds with HTTP 200, False otherwise.
        """
        try:
            url = f"{self.host}/api/tags"
            response = requests.get(url, timeout=1.0)
            return response.status_code == 200
        except Exception:
            return False

    def discover_binary(self) -> Optional[str]:
        """
        Locates the Ollama executable following the discovery hierarchy (§9.11):
          1. System environment PATH via shutil.which("ollama")
          2. Standard user install: %LOCALAPPDATA%\\Programs\\Ollama\\ollama.exe
          3. Standard machine install: %ProgramFiles%\\Ollama\\ollama.exe
          4. config.json override path ("ollama_binary_path")
        Returns first existing executable path, or None.
        """
        # 1. PATH search
        which_path = shutil.which("ollama")
        if which_path and os.path.isfile(which_path):
            return which_path

        # 2 & 3. Standard paths from config
        for p in OLLAMA_BINARY_PATHS:
            expanded = os.path.expandvars(p)
            if os.path.isfile(expanded):
                return expanded

        # 4. User config override
        cfg_path = self.config_manager.get("ollama_binary_path")
        if cfg_path:
            expanded_cfg = os.path.expandvars(cfg_path)
            if os.path.isfile(expanded_cfg):
                return expanded_cfg

        return None

    def auto_start(self) -> bool:
        """
        Launches 'ollama serve' as a detached background process (no console window).
        Polls /api/tags every 1.5s for up to 15s (§9.11 step 2).
        Returns True if the daemon successfully comes online.
        """
        if self.is_online():
            return True

        binary_path = self.discover_binary()
        if not binary_path:
            _logger.error("Cannot auto-start Ollama: executable not found on system.")
            return False

        _logger.info(f"Auto-starting Ollama daemon from: {binary_path}")

        creationflags = 0
        if os.name == "nt":
            # DETACHED_PROCESS (0x00000008) | CREATE_NO_WINDOW (0x08000000)
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW

        try:
            subprocess.Popen(
                [binary_path, "serve"],
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=(os.name != "nt"),
            )
        except Exception as e:
            _logger.error(f"Failed to spawn Ollama daemon: {e}")
            return False

        # Poll /api/tags every 1.5s up to 30s total to accommodate cold-start & GPU discovery
        start_time = time.time()
        while time.time() - start_time < 30.0:
            time.sleep(1.5)
            if self.is_online():
                _logger.info(f"Ollama daemon came online in {time.time() - start_time:.1f}s.")
                return True

        _logger.warning("Ollama auto-start timed out after 30 seconds.")
        return False

    def check_model_present(self, model_tag: str = OLLAMA_MODEL_TAG) -> bool:
        """
        Queries GET /api/tags to check if model_tag or its common aliases exist (§9.11 step 3).
        Recognizes aliases:
          - phi4-mini
          - phi4-mini:latest
          - phi4-mini:3.8b-instruct-q4_K_M
        """
        if not self.is_online():
            return False

        try:
            url = f"{self.host}/api/tags"
            response = requests.get(url, timeout=3.0)
            if response.status_code != 200:
                return False

            data = response.json()
            models = data.get("models", [])

            tag_lower = model_tag.lower()
            tag_prefix = f"{tag_lower}:"

            # Check aliases
            aliases = {
                tag_lower,
                f"{tag_lower}:latest",
                f"{tag_lower}:3.8b-instruct-q4_k_m",
            }

            for m in models:
                name = (m.get("name") or m.get("model") or "").lower()
                if name in aliases or name.startswith(tag_prefix) or name == tag_lower:
                    return True

            return False
        except Exception as e:
            _logger.warning(f"Error checking model presence: {e}")
            return False

    def pull_model(
        self,
        model_tag: str = OLLAMA_MODEL_TAG,
        progress_callback: Optional[Callable[[float, float, float], None]] = None,
    ) -> bool:
        """
        Pulls a model via POST /api/pull with streaming progress (§9.11 step 3).
        progress_callback receives: (percent: float, downloaded_mb: float, total_mb: float).
        Returns True on successful pull.
        """
        if not self.is_online():
            return False

        url = f"{self.host}/api/pull"
        try:
            with requests.post(url, json={"name": model_tag, "stream": True}, stream=True, timeout=(5.0, 600.0)) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8") if isinstance(line, bytes) else line)
                        status = chunk.get("status", "")
                        completed = chunk.get("completed", 0)
                        total = chunk.get("total", 0)

                        if total > 0 and progress_callback:
                            percent = (completed / total) * 100.0
                            downloaded_mb = completed / (1024.0 * 1024.0)
                            total_mb = total / (1024.0 * 1024.0)
                            progress_callback(percent, downloaded_mb, total_mb)

                        if status == "success":
                            return True

            return self.check_model_present(model_tag)
        except Exception as e:
            _logger.error(f"Failed to pull model {model_tag}: {e}")
            return False


class OllamaStreamingClient:
    """
    Streams tokens from Ollama /api/chat with cancellation and timeout controls (§9.10).
    """

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL_TAG) -> None:
        self.host = host.rstrip("/")
        self.model = model

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        cancel_event: threading.Event,
        timeout: int = QUERY_TIMEOUT_SECONDS,
    ) -> Generator[str, None, None]:
        """
        Streams response tokens from /api/chat.
        - Options enforced: num_ctx=2048, num_thread=4 (§2.6).
        - Yields individual token strings.
        - Checks cancel_event between chunks, exiting cleanly if signalled (§9.8 item 5).
        - Raises TimeoutError if total time exceeds timeout (§10.4).
        """
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_ctx": NUM_CTX,
                "num_thread": NUM_THREAD,
            },
        }

        start_time = time.time()

        try:
            response = requests.post(url, json=payload, stream=True, timeout=(10.0, timeout))
            response.raise_for_status()

            for line in response.iter_lines():
                if cancel_event.is_set():
                    _logger.info("stream_chat aborted: cancellation flag is set.")
                    return

                if time.time() - start_time > timeout:
                    raise TimeoutError(f"LLM generation exceeded timeout of {timeout}s.")

                if line:
                    chunk = json.loads(line.decode("utf-8") if isinstance(line, bytes) else line)
                    if chunk.get("done"):
                        break

                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token

                    if cancel_event.is_set():
                        _logger.info("stream_chat aborted: cancellation flag is set.")
                        return

        except (requests.exceptions.ReadTimeout, requests.exceptions.Timeout):
            if cancel_event.is_set():
                return
            _logger.error(f"Ollama stream_chat timed out after {timeout}s.")
            raise TimeoutError(f"LLM generation exceeded timeout of {timeout}s.")
        except requests.exceptions.RequestException as e:
            if cancel_event.is_set():
                return
            _logger.error(f"HTTP error during Ollama stream_chat: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """
        Returns structured health status and model list for UI diagnostics (§11.4).
        """
        try:
            url = f"{self.host}/api/tags"
            resp = requests.get(url, timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "online",
                    "host": self.host,
                    "models": data.get("models", []),
                    "model_count": len(data.get("models", [])),
                }
            return {
                "status": "offline",
                "host": self.host,
                "error": f"HTTP {resp.status_code}",
                "models": [],
                "model_count": 0,
            }
        except Exception as e:
            return {
                "status": "offline",
                "host": self.host,
                "error": str(e),
                "models": [],
                "model_count": 0,
            }

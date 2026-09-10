"""
iValue PRISM — Configuration and System Constants Module
SRS References: §2.6, §8.1.6, §11.1

This module centralizes all system constants, threshold definitions, token estimation heuristics,
fit score calculations, persistent user configuration management, and the shared SessionSnapshot
data structure.
"""

import os
import sys

# Enforce 100% offline mode for Hugging Face Hub / Transformers (Hard Constraint #2)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional


# ==============================================================================
# System Constants (§2.6)
# ==============================================================================

APP_VERSION: str = "3.4"
OLLAMA_HOST: str = "http://127.0.0.1:11434"
OLLAMA_MODEL_TAG: str = "phi4-mini"
EMBEDDING_MODEL_NAME: str = "bge-small-en-v1.5"

SIMILARITY_FLOOR: float = 0.20
SIMILARITY_WARNING: float = 0.35
SIMILARITY_CEILING: float = 0.80

TOKEN_HEURISTIC_FACTOR: float = 1.3
MAX_SESSION_HISTORY: int = 20
MAX_INPUT_CHARS: int = 10_000
SHORT_INPUT_THRESHOLD: int = 10
MAX_INPUT_TOKENS: int = 1500
QUERY_TIMEOUT_SECONDS: int = 180
QUEUE_POLL_INTERVAL_MS: int = 50
HEALTH_CHECK_INTERVAL_S: int = 30
MAX_TOP_K: int = 5
NUM_CTX: int = 2048
NUM_THREAD: int = 4
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
SUPPORTED_EXTENSIONS: set = {".txt", ".pdf", ".docx"}

OLLAMA_BINARY_PATHS: List[str] = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
    os.path.expandvars(r"%ProgramFiles%\Ollama\ollama.exe"),
]

PRIMARY_LOG_PATH: str = os.path.expandvars(r"%APPDATA%\iValue_PRISM\logs\query_log.jsonl")
FALLBACK_LOG_PATH: str = "./logs/query_log.jsonl"
CONFIG_FILE_PATH: str = os.path.expandvars(r"%APPDATA%\iValue_PRISM\config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "appearance_mode": "dark",
    "window_geometry": [1280, 820, None, None, False],
    "similarity_floor": 0.20,
    "similarity_warning": 0.35,
}


def get_data_path(relative_path: str) -> str:
    """
    Resolves data file path for development mode and PyInstaller frozen bundle (_MEIPASS).
    """
    # Strip redundant leading data/ or data\ if present for uniform searching
    clean_rel = relative_path.replace("\\", "/")
    if clean_rel.startswith("data/"):
        clean_rel = clean_rel[5:]

    # 1. PyInstaller frozen bundle runtime directory
    base_meipass = getattr(sys, "_MEIPASS", None)
    if base_meipass:
        for cand in [
            os.path.join(base_meipass, relative_path),
            os.path.join(base_meipass, "data", clean_rel),
            os.path.join(base_meipass, clean_rel),
        ]:
            if os.path.exists(cand):
                return cand

    # 2. Development mode relative to repository root
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for cand in [
        os.path.join(root_dir, relative_path),
        os.path.join(root_dir, "data", clean_rel),
        os.path.join(root_dir, clean_rel),
    ]:
        if os.path.exists(cand):
            return cand

    # 3. Direct relative or absolute fallback
    return os.path.abspath(os.path.join(root_dir, "data", clean_rel))


# ==============================================================================
# Pure Functions & Calculation Heuristics
# ==============================================================================

def compute_fit_score(cosine_similarity: float) -> float:
    """
    Computes normalized 0-100% Fit Score from raw cosine similarity.
    Formula: max(0.0, min(100.0, (cosine_similarity - SIMILARITY_FLOOR) / (SIMILARITY_CEILING - SIMILARITY_FLOOR) * 100))
    """
    val = max(
        0.0,
        min(
            100.0,
            (cosine_similarity - SIMILARITY_FLOOR) / (SIMILARITY_CEILING - SIMILARITY_FLOOR) * 100.0,
        ),
    )
    return round(val, 2)


def compute_confidence_tier(fit_score: float, all_confirmed: bool) -> str:
    """
    Determines recommendation confidence tier based on fit score and product confirmation status.
    - HIGH: fit_score >= 85.0 and all candidate rows Confirmed
    - MEDIUM: fit_score >= 65.0
    - LOW: fit_score < 65.0 or unconfirmed status
    """
    if fit_score >= 85.0 and all_confirmed:
        return "HIGH"
    elif fit_score >= 65.0:
        return "MEDIUM"
    else:
        return "LOW"


def estimate_tokens(text: str) -> int:
    """
    Estimates token count for UI gauge using whitespace splitting and 1.3x heuristic factor.
    """
    return int(len(text.split()) * TOKEN_HEURISTIC_FACTOR)


# ==============================================================================
# Shared Data Structures (Locked Decision #6)
# ==============================================================================

@dataclass
class SessionSnapshot:
    """
    In-memory record of a single query session. §8.1.5 item 1.
    Volatile — cleared on application exit in Phase 1.
    """
    query_id: str
    timestamp: str                          # ISO 8601
    requirement_text: str                   # Original user input
    recommendations: List[Dict[str, Any]]   # Serialized ProductRecommendation dicts
    user_actions: Dict[str, str] = field(default_factory=dict)  # product_id -> "accept"/"reject"
    export_state: Optional[str] = None      # "bom_exported" / "boq_exported" / None


# ==============================================================================
# Configuration Manager (§8.1.6)
# ==============================================================================

class ConfigManager:
    """
    Manages loading, persisting, and querying user settings in %APPDATA%/iValue_PRISM/config.json.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.config_path = config_path or CONFIG_FILE_PATH
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """
        Loads configuration from JSON file. If file does not exist or is corrupt,
        initializes with default config and saves it to disk.
        """
        if not os.path.exists(self.config_path):
            self.config = dict(DEFAULT_CONFIG)
            self.save()
            return self.config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    # Ensure all default keys exist
                    merged = dict(DEFAULT_CONFIG)
                    merged.update(loaded)
                    self.config = merged
                else:
                    self.config = dict(DEFAULT_CONFIG)
                    self.save()
        except Exception:
            self.config = dict(DEFAULT_CONFIG)
            self.save()

        return self.config

    def save(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Persists configuration dictionary to JSON file.
        Creates parent directories if they do not exist.
        """
        if config is not None:
            self.config.update(config)

        config_dir = os.path.dirname(self.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value by key, returning default if not present.
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Updates a configuration key and persists immediately to disk.
        """
        self.config[key] = value
        self.save()

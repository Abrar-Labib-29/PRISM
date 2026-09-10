# iValue PRISM — Implementation Plan

> **Document version:** 1.1 | **SRS baseline:** v3.4 (locked) | **Planning agent:** Opus | **Last updated:** 2026-09-09
> **All architectural decisions are LOCKED.** See "Locked Architectural Decisions" at the bottom.

---

## Quick Start (Read This First)

1. **Read `AGENTS.md`** in the repo root for hard constraints and model routing policy.
2. **Check the Status Dashboard** below — find the next task with status `Not Started` whose dependencies are all `Done`.
3. **Open that task's full spec** (search by TASK ID in this document) and read its SRS refs.
4. **Execute only that one task.** Do not modify files outside the task's allowed list.
5. **When done:** Update the task's status to `Done` in the dashboard, and append a one-line summary to the **Walkthrough Log** at the bottom.

---

## Status Dashboard

| Task ID | Phase | Title | SRS Refs | Depends On | Status | Files Touched |
|---|---|---|---|---|---|---|
| TASK-P1.1 | 1 — Data & Core | Constants & configuration module | §2.6, §8.1.6 | none | Done | `src/utils/config.py` |
| TASK-P1.2 | 1 — Data & Core | JSONL query logger | §11.1, §11.3, §11.4 | TASK-P1.1 | Done | `src/utils/logger.py` |
| TASK-P1.3 | 1 — Data & Core | System info utilities | §10.7, §11.4 | TASK-P1.1 | Done | `src/utils/system_info.py` |
| TASK-P1.4 | 1 — Data & Core | Document parser (ingestion) | §3 Phase 1 step 3, §10.1, §10.2 | TASK-P1.1 | Done | `src/core/ingestion.py` |
| TASK-P1.5 | 1 — Data & Core | Hybrid retriever | §3 Phase 1 step 4, §7.2, §7.3, §9.1, §9.10 | TASK-P1.1 | Done | `src/core/retrieval.py` |
| TASK-P1.6 | 1 — Data & Core | Context assembler | §3 Phase 1 step 5, §7.4, §7.5, §9.10 | TASK-P1.5 | Done | `src/core/context_builder.py` |
| TASK-P1.7 | 1 — Data & Core | Ollama service manager & streaming client | §9.10, §9.11, §10.4 | TASK-P1.1 | Done | `src/core/ollama_client.py` |
| TASK-P1.8 | 1 — Data & Core | Response validator (pricing, hallucination, repetition) | §3 Phase 1 step 7, §10.4, §10.8, §11.2, §9.10 | TASK-P1.1 | Done | `src/core/validators.py` |
| TASK-P1.9 | 1 — Data & Core | BOM exporter (.xlsx) | §3 Phase 2 step 3, §8.4, §10.5, §9.10 | TASK-P1.1 | Done | `src/core/exporters.py` |
| TASK-P1.10 | 1 — Data & Core | BOQ exporter (.docx) — append to exporters | §3 Phase 2 step 4, §8.4, §10.5 | TASK-P1.9 | Done | `src/core/exporters.py` |
| TASK-P1.11 | 1 — Data & Core | PrismService façade | §8.3 | TASK-P1.4, TASK-P1.5, TASK-P1.6, TASK-P1.7, TASK-P1.8, TASK-P1.9, TASK-P1.10 | Done | `src/core/service.py` |
| TASK-P2.1 | 2 — Threading | Worker thread dispatcher & queue protocol | §9.8, §9.9, §10.7 | TASK-P1.11 | Done | `src/core/worker.py` |
| TASK-P3.1 | 3 — UI Shell | Theme JSON & design tokens | §8.1.2, §8.1.3, §8.1.4, §8.1.11 | none | Done | `themes/ivalue_prism.json` |
| TASK-P3.2 | 3 — UI Shell | Splash preloader (Phase B) | §8.1.7, §8.1.7a | TASK-P3.1, TASK-P1.1 | Done | `src/ui/splash.py` |
| TASK-P3.3 | 3 — UI Shell | Main application window (PRISMApp) | §8.1.1, §8.1.6, §9.8, §9.9 state 0-1 | TASK-P3.1, TASK-P3.2, TASK-P2.1 | Done | `src/ui/app.py`, `main.py` |
| TASK-P3.4 | 3 — UI Shell | Sidebar view | §8.1.5 item 1, §8.1.13 | TASK-P3.1, TASK-P1.1, TASK-P1.3 | Done | `src/ui/components/__init__.py`, `src/ui/components/sidebar.py` |
| TASK-P3.5 | 3 — UI Shell | Requirement input panel | §8.1.5 item 2, §FR-1, §FR-1a, §FR-14 | TASK-P3.1 | Done | `src/ui/components/input_panel.py` |
| TASK-P4.1 | 4 — Results | Token stream terminal | §8.1.5 item 3 | TASK-P3.1 | Done | `src/ui/components/stream_box.py` |
| TASK-P4.2 | 4 — Results | Recommendation result cards | §8.1.5 item 4, §8.1.14, §FR-9 | TASK-P3.1 | Done | `src/ui/components/result_cards.py` |
| TASK-P4.3 | 4 — Results | Document extraction modal | §8.1.12, §FR-13 | TASK-P3.1 | Done | `src/ui/components/extraction_modal.py` |
| TASK-P4.4 | 4 — Results | Toast notification manager | §8.1.9 | TASK-P3.1 | Done | `src/ui/components/toast.py` |
| TASK-P4.5 | 4 — Results | Welcome zero-state guidance | §8.1.8 | TASK-P3.1, TASK-P3.5 | Done | `src/ui/components/welcome.py` |
| TASK-P5.1 | 5 — Export | Export control panel (tksheet BOM grid) | §8.1.5 item 5, §8.4 | TASK-P3.1, TASK-P1.9, TASK-P1.10 | Done | `src/ui/components/export_panel.py` |
| TASK-P6.1 | 6 — Packaging | Boot splash image generation | §8.1.7a, §8.1.11 | none | Done | `assets/branding/boot_splash.png` |
| TASK-P6.2 | 6 — Packaging | PyInstaller build & native splash handoff | §9.7, §8.1.7a, §12.7 STR-10 | All prior tasks | Done | `main.py`, `prism.spec` |
| TASK-P6.3 | 6 — Packaging | Icon & branding assets | §8.1.1, §8.1.11 | none | Done | `assets/branding/ivalue_prism.ico`, `assets/branding/ivalue_prism_logo.png`, `assets/icons/` |

---

## Phase 1 — Data Layer & Core Pipeline

---

### TASK-P1.1 — Create constants and configuration module

**SRS refs:** §2.6, §8.1.6, §11.1

**Depends on:** none

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/utils/config.py`

> **LOCKED DECISION:** This module also defines the `SessionSnapshot` dataclass (used by both UI sidebar and core service). Define it here as a shared data structure.

**Implementation spec:**

Create a module that centralizes all system constants and manages persistent user preferences.

**Constants (verbatim from SRS §2.6):**
```python
APP_VERSION = "3.4"
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL_TAG = "phi4-mini"
EMBEDDING_MODEL_NAME = "bge-small-en-v1.5"
SIMILARITY_FLOOR = 0.20
SIMILARITY_WARNING = 0.35
SIMILARITY_CEILING = 0.80
TOKEN_HEURISTIC_FACTOR = 1.3
MAX_SESSION_HISTORY = 20
MAX_INPUT_CHARS = 10_000
SHORT_INPUT_THRESHOLD = 10
MAX_INPUT_TOKENS = 1500
QUERY_TIMEOUT_SECONDS = 180
QUEUE_POLL_INTERVAL_MS = 50
HEALTH_CHECK_INTERVAL_S = 30
MAX_TOP_K = 5
NUM_CTX = 2048
NUM_THREAD = 4
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}
OLLAMA_BINARY_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
    os.path.expandvars(r"%ProgramFiles%\Ollama\ollama.exe"),
]
```

**Fit score formula (implement as a function):**
```python
def compute_fit_score(cosine_similarity: float) -> float:
    return max(0.0, min(100.0, (cosine_similarity - SIMILARITY_FLOOR) / (SIMILARITY_CEILING - SIMILARITY_FLOOR) * 100))
```

**Confidence tier function:**
```python
def compute_confidence_tier(fit_score: float, all_confirmed: bool) -> str:
    if fit_score >= 85.0 and all_confirmed:
        return "HIGH"
    elif fit_score >= 65.0:
        return "MEDIUM"
    else:
        return "LOW"
```

**Token estimator:**
```python
def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * TOKEN_HEURISTIC_FACTOR)
```

**ConfigManager class:**
- Reads/writes `%APPDATA%\iValue_PRISM\config.json` (create parent dirs with `os.makedirs`).
- Default config on first run (§8.1.6): `{"appearance_mode": "dark", "window_geometry": [1280, 820, null, null, false], "similarity_floor": 0.20, "similarity_warning": 0.35}`.
- Methods: `load() -> dict`, `save(config: dict)`, `get(key, default)`, `set(key, value)`.
- Log file path constants: `PRIMARY_LOG_PATH` resolving `%APPDATA%\iValue_PRISM\logs\query_log.jsonl`, fallback `./logs/query_log.jsonl`.

**SessionSnapshot dataclass (LOCKED DECISION #6 — define here):**
```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class SessionSnapshot:
    """In-memory record of a single query session. §8.1.5 item 1.
    Volatile — cleared on application exit in Phase 1."""
    query_id: str
    timestamp: str                          # ISO 8601
    requirement_text: str                   # Original user input
    recommendations: List[Dict[str, Any]]   # Serialized ProductRecommendation dicts
    user_actions: Dict[str, str] = field(default_factory=dict)  # product_id → "accept"/"reject"
    export_state: Optional[str] = None      # "bom_exported" / "boq_exported" / None
```

**Acceptance criteria / Definition of Done:**
- `compute_fit_score(0.20)` returns `0.0`, `compute_fit_score(0.80)` returns `100.0`, `compute_fit_score(0.50)` returns `50.0`.
- `compute_confidence_tier(90.0, True)` returns `"HIGH"`, `compute_confidence_tier(70.0, True)` returns `"MEDIUM"`, `compute_confidence_tier(50.0, False)` returns `"LOW"`.
- `estimate_tokens("hello world foo")` returns `int(3 * 1.3)` = `3`.
- `ConfigManager` creates `config.json` on first run with defaults, loads it on second run.
- All constants match SRS §2.6 values exactly.

**Do NOT:**
- Add any UI code or CustomTkinter imports.
- Import `sentence_transformers`, `numpy`, or `ollama` (this is a pure-config module).
- Add retry logic or network calls.

---

### TASK-P1.2 — Create JSONL query logger

**SRS refs:** §11.1, §11.3, §11.4

**Depends on:** TASK-P1.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/utils/logger.py`

**Implementation spec:**

Create a `QueryLogger` class implementing the append-only JSONL logging specified in SRS §11.1.

```python
class QueryLogger:
    def __init__(self, log_path: Optional[str] = None):
        """Uses PRIMARY_LOG_PATH from config.py; creates parent dirs."""
        ...
    def log_query(self, entry: dict) -> None:
        """Appends one JSON object per line. Schema per §11.1."""
        ...
    def log_user_action(self, query_id: str, action: str, details: Optional[dict] = None) -> None:
        """Logs Accept/Reject/Export actions per §11.3."""
        ...
    def log_system_event(self, level: str, message: str, **kwargs) -> None:
        """Logs WARN/ERROR/CRITICAL system health events per §11.4."""
        ...
```

- Schema matches §11.1 exactly: `query_id`, `timestamp` (ISO 8601), `input_type`, `input_text`, `input_file`, `extracted_text`, `retrieved_products` (list of `{product_id, similarity_score}`), `domain_classification`, `generated_text`, `fit_score`, `confidence_level`, `hallucinations_detected`, `pricing_mentions_stripped`, `repetition_truncated`, `latency` dict (embedding_ms, retrieval_ms, context_assembly_ms, ttft_ms, generation_ms, validation_ms, total_ms), `ram_before_mb`, `ram_after_mb`, `user_action`, `user_feedback`, `error`.
- Log rotation at 50 MB file size. Rotate by renaming the current file to `query_log_<ISO_DATE>.jsonl` and creating a new empty file. Never delete archived logs.
- Also configure Python stdlib `logging` to write to `logs/prism_app.log` and `logs/prism_error.log` (ERROR+).
- Generate `query_id` using `f"req-{uuid.uuid4().hex[:5]}"` format.

**Acceptance criteria / Definition of Done:**
- `log_query({...})` appends exactly one line of valid JSON to the file.
- `log_user_action("req-abc12", "accept")` appends a correct action entry.
- Log file rotation triggers when file exceeds 50 MB (testable via mock).
- Creates directories and files if they do not exist.

**Do NOT:**
- Import any UI module.
- Delete or overwrite existing log data.
- Add any telemetry or external reporting.

---

### TASK-P1.3 — Create system info utilities

**SRS refs:** §10.7, §11.4

**Depends on:** TASK-P1.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/utils/system_info.py`

**Implementation spec:**

Implement the following functions:

```python
import psutil
import ctypes

def get_ram_usage_mb() -> float:
    """Returns current process RSS in MB via psutil."""
    ...

def get_system_ram_mb() -> float:
    """Returns total system RAM used in MB via psutil.virtual_memory().used."""
    ...

def verify_single_instance(mutex_name: str = "Global\\iValue_PRISM") -> bool:
    """Attempts to create a Windows named mutex via ctypes.windll.kernel32.CreateMutexW.
    Returns True if this is the first instance, False if another instance holds the mutex.
    Per §10.7: single-instance guard."""
    ...

def check_reduced_motion() -> bool:
    """Checks Windows 'SPI_GETCLIENTAREAANIMATION' via ctypes.windll.user32.SystemParametersInfoW.
    Returns True if animations are disabled. Per §8.1.10, §6.9."""
    ...
```

**Acceptance criteria / Definition of Done:**
- `get_ram_usage_mb()` returns a positive float.
- `get_system_ram_mb()` returns a positive float > 1000.
- `verify_single_instance()` returns `True` on first call, `False` if called from a second process with same mutex name.
- `check_reduced_motion()` returns a boolean without crashing.

**Do NOT:**
- Add UI or Tkinter code.
- Add Ollama health checks (those are in `ollama_client.py`).

---

### TASK-P1.4 — Create document parser (ingestion)

**SRS refs:** §3 Phase 1 step 3, §10.1, §10.2

**Depends on:** TASK-P1.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/ingestion.py`

**Implementation spec:**

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExtractionResult:
    text: str
    source_filename: str
    file_size_kb: float
    char_count: int
    estimated_tokens: int
    warning: Optional[str] = None  # e.g., "scanned_pdf", "encoding_fallback"
    error: Optional[str] = None

class DocumentParser:
    """Extracts plain text from .txt, .pdf, .docx files. §3 Phase 1 step 3."""

    def extract(self, file_path: str) -> ExtractionResult:
        """Routes to _extract_txt, _extract_pdf, _extract_docx based on extension.
        Validates:
        - Extension in SUPPORTED_EXTENSIONS (§10.2)
        - File size <= MAX_FILE_SIZE_BYTES (§10.2)
        - Not empty result (§10.2)
        - Scanned PDF detection: extracted text <50 chars AND file >100KB (§10.2)
        """
        ...

    def _extract_txt(self, file_path: str) -> str:
        """UTF-8 with latin-1 fallback per §10.2."""
        ...

    def _extract_pdf(self, file_path: str) -> str:
        """Uses pdfplumber. Catches encryption errors for password-protected PDFs. §10.2."""
        ...

    def _extract_docx(self, file_path: str) -> str:
        """Uses python-docx. Extracts text from paragraphs AND tables. §10.2."""
        ...
```

- All error cases from §10.2 must be handled: unsupported format, corrupted file, empty file, scanned PDF, password-protected, oversized, encoding issues.
- Use `estimate_tokens()` from `config.py`.

**Acceptance criteria / Definition of Done:**
- `.txt` file with UTF-8 content extracts correctly.
- `.txt` file with Windows-1252 encoding falls back to latin-1 without crashing (NEG-14).
- `.pdf` with text extracts correctly.
- `.pdf` that is password-protected returns `error` field set (NEG-11).
- `.docx` extracts paragraph and table text (INT-07 preparatory).
- `.exe` file returns error for unsupported format (NEG-08).
- 0-byte `.txt` returns error for empty file (NEG-09).
- 50 MB PDF returns error for oversized file (NEG-10).
- Scanned PDF (text <50 chars, file >100KB) returns warning `"scanned_pdf"` (NEG-12).

**Do NOT:**
- Add OCR capabilities (out of scope per §1.2).
- Add any UI code or Tkinter imports.
- Handle drag-and-drop (that's UI layer responsibility).

---

### TASK-P1.5 — Create hybrid retriever

**SRS refs:** §3 Phase 1 step 4, §7.2, §7.3, §9.1, §9.1.1, §9.10

**Depends on:** TASK-P1.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/retrieval.py`

**Implementation spec:**

```python
class HybridRetriever:
    def __init__(self, embeddings_path: str = "data/embeddings.npy",
                 metadata_path: str = "data/metadata.pkl",
                 composite_path: str = "data/composite_products.json",
                 taxonomy_path: str = "data/domain_taxonomy.json",
                 model_name: str = "bge-small-en-v1.5"):
        """Loads pre-computed NumPy embeddings matrix (139, 384) and pandas metadata table.
        Loads sentence-transformers model (bge-small-en-v1.5).
        Loads composite_products.json for prompt context.
        Loads domain_taxonomy.json for keyword matching."""
        ...

    def encode_query(self, query_text: str) -> np.ndarray:
        """CRITICAL: Applies bge-small query instruction prefix:
        'Represent this sentence for searching relevant passages: <query>'
        per §7.2. Uses model.encode() with prompt_name='query'."""
        ...

    def _keyword_filter(self, query_text: str) -> Optional[List[int]]:
        """Scans input text for exact matches against known Sub_Domain names,
        OEM names, and Product_Category values from metadata.
        Returns indices of matching products, or None if no keyword matches. §3 Phase 1 step 4a."""
        ...

    def _semantic_search(self, query_vec: np.ndarray, top_k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """NumPy brute-force cosine similarity per §9.1.1:
        scores = np.dot(all_vecs, query_vec) / (np.linalg.norm(all_vecs, axis=1) * np.linalg.norm(query_vec))
        Returns (top_indices, scores). §9.1.1."""
        ...

    def search(self, query_text: str, top_k: int = 5,
               min_similarity: float = 0.20) -> List[Dict[str, Any]]:
        """Executes hybrid search per §3 Phase 1 step 4:
        1. Run _keyword_filter() for deterministic matches.
        2. Run _semantic_search() for meaning-based matches.
        3. Merge results (union + rerank by score). §3 Phase 1 step 4c.
        4. Apply SIMILARITY_FLOOR=0.20 hard cutoff. §3 Phase 1 step 4d.
        5. Flag SIMILARITY_WARNING=0.35 advisory threshold.
        Returns list of dicts with keys: product_id, oem_name, product_name,
        domain_category, sub_domain, similarity_score, fit_score, confidence_tier,
        data_status, composite_text."""
        ...

    def reload_index(self) -> None:
        """Reloads embeddings.npy and metadata.pkl from disk.
        Used after re-embedding. Atomic swap per §4.5."""
        ...

    def check_stale(self, dataset_path: str = "data/raw/iValue_Solution_Recommendation_Dataset.xlsx") -> bool:
        """Compares dataset file mtime against stored last_embed_timestamp. §4.5, §FR-18."""
        ...
```

- Use `compute_fit_score()` and `compute_confidence_tier()` from `config.py`.
- **Do NOT add a non-English input check here.** That check lives solely in `PrismService.analyze()` (TASK-P1.11) as the single gatekeeping point. The retriever must assume it receives valid English text.

**Acceptance criteria / Definition of Done:**
- `encode_query("PAM solution")` returns a 384-dim numpy array (not None, not empty).
- Keyword filter for "SIEM" returns products in that sub-domain.
- Semantic search returns results sorted by descending similarity score.
- Products with similarity < 0.20 are excluded from results.
- Products with top similarity between 0.20 and 0.35 get a LOW confidence tier.
- `reload_index()` swaps the embeddings without crashing during an active query.
- Passes Phase 1 Retrieval Quality Test Set targets: Recall@3 ≥ 80%, Recall@5 ≥ 90% (§12.2).

**Do NOT:**
- Add any UI code or Tkinter imports.
- Use ChromaDB, LanceDB, or any vector database.
- Modify the embeddings.npy or metadata.pkl files (they are pre-computed read-only assets).

---

### TASK-P1.6 — Create context assembler

**SRS refs:** §3 Phase 1 step 5, §7.4, §7.5, §9.10

**Depends on:** TASK-P1.5

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/context_builder.py`

**Implementation spec:**

```python
class ContextAssembler:
    def __init__(self, composite_products_path: str = "data/composite_products.json",
                 metadata_path: str = "data/metadata.pkl"):
        """Loads composite product texts and metadata for context assembly."""
        ...

    def build_messages(self, query_text: str, retrieved_products: List[Dict[str, Any]],
                       max_context_tokens: int = 1200) -> List[Dict[str, str]]:
        """Builds the ChatML message array for Ollama /api/chat.

        System prompt per §7.4 verbatim:
        - Role instructions
        - 6 rules (no pricing, cite sources, etc.)
        - Retrieved product data block

        Returns: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

        Context budget management per §7.5:
        - System prompt instructions: ~250 tokens (fixed)
        - Retrieved product data: ≤ max_context_tokens (variable)
        - User requirement: variable
        - Generation headroom: ~400-600 tokens
        - Total ≤ NUM_CTX (2048)

        Truncation priority per §7.5 (cut lowest priority first):
        1. Domain_Comparables data
        2. Pros/Cons beyond top 2 per product
        3. Features beyond top 3 per product
        4. Reduce from 5 candidates to 3
        5. Trim product descriptions
        """
        ...

    def _format_product_context(self, products: List[Dict[str, Any]], budget: int) -> str:
        """Formats retrieved products as structured text for the LLM prompt.
        Uses estimate_tokens() to enforce budget."""
        ...
```

**Acceptance criteria / Definition of Done:**
- `build_messages()` returns a list of exactly 2 dicts with `role`/`content` keys.
- System message contains the 6 rules from §7.4 verbatim.
- System message contains retrieved product data.
- Total token estimate of system + user messages stays ≤ 1600 tokens (leaving 448 for generation).
- When 5 products with max-length composites are provided, truncation activates and output stays within budget.

**Do NOT:**
- Call Ollama or any LLM.
- Add UI code.
- Change the system prompt rules from §7.4.

---

### TASK-P1.7 — Create Ollama service manager & streaming client

**SRS refs:** §9.10, §9.11, §10.4 (Ollama errors), §2.5

**Depends on:** TASK-P1.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/ollama_client.py`

**Implementation spec:**

```python
import threading
import shutil
import subprocess
from typing import Generator, List, Dict, Optional

class OllamaServiceManager:
    """Handles Ollama daemon discovery, auto-start, and model presence checks. §9.11."""

    def __init__(self, host: str = OLLAMA_HOST):
        ...

    def is_online(self) -> bool:
        """Pings GET /api/tags with 1.0s timeout. §9.11 step 1."""
        ...

    def discover_binary(self) -> Optional[str]:
        """Discovery hierarchy per §9.11:
        1. shutil.which("ollama")
        2. %LOCALAPPDATA%\\Programs\\Ollama\\ollama.exe
        3. %ProgramFiles%\\Ollama\\ollama.exe
        4. config.json override path
        Returns first valid path found, or None."""
        ...

    def auto_start(self) -> bool:
        """Launches 'ollama serve' via subprocess.Popen with CREATE_NO_WINDOW | DETACHED_PROCESS.
        Polls /api/tags every 1.5s for up to 15s. §9.11 step 2.
        Returns True if daemon comes online."""
        ...

    def check_model_present(self, model_tag: str = OLLAMA_MODEL_TAG) -> bool:
        """Queries GET /api/tags, checks if model_tag (or aliases) is in the list. §9.11 step 3.
        Checks: 'phi4-mini', 'phi4-mini:latest', 'phi4-mini:3.8b-instruct-q4_K_M'."""
        ...

    def pull_model(self, model_tag: str = OLLAMA_MODEL_TAG, progress_callback=None) -> bool:
        """POST /api/pull with streaming progress. §9.11 step 3 (download option).
        Calls progress_callback(percent, downloaded_mb, total_mb) during download."""
        ...


class OllamaStreamingClient:
    """Streams token-by-token from Ollama /api/chat. §9.10."""

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL_TAG):
        ...

    def stream_chat(self, messages: List[Dict[str, str]],
                    cancel_event: threading.Event,
                    timeout: int = QUERY_TIMEOUT_SECONDS) -> Generator[str, None, None]:
        """POST /api/chat with stream=true, model=self.model, options={num_ctx: 2048, num_thread: 4}.
        Yields individual token strings.
        Checks cancel_event.is_set() between chunks — aborts cleanly if set. §9.8 item 5.
        Raises TimeoutError if total elapsed time exceeds timeout. §10.4."""
        ...

    def health_check(self) -> dict:
        """Returns parsed /api/tags response for health display. §11.4."""
        ...
```

- Use the `ollama` Python package (`import ollama`) for the streaming client where possible; fall back to raw `requests` if the package doesn't support cancel events cleanly.
- Use `requests` library for raw HTTP calls in OllamaServiceManager.

**Acceptance criteria / Definition of Done:**
- `is_online()` returns `True` when Ollama is running, `False` when not.
- `discover_binary()` finds the Ollama exe on a system where Ollama is installed.
- `auto_start()` successfully starts Ollama if binary found and daemon is offline (INT-01).
- `check_model_present()` returns `True` if phi4-mini is pulled (INT-02).
- `stream_chat()` yields token strings one at a time.
- `stream_chat()` aborts within 2s when `cancel_event.set()` is called (NEG-16).
- `stream_chat()` raises `TimeoutError` after 180s (FR-20).

**Do NOT:**
- Add UI code.
- Modify Ollama configuration files or Modelfile.presales.
- Use any cloud API.

---

### TASK-P1.8 — Create response validator

**SRS refs:** §3 Phase 1 step 7, §10.4, §10.8, §11.2, §9.10

**Depends on:** TASK-P1.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/validators.py`

**Implementation spec:**

```python
class ResponseValidator:
    def __init__(self, catalog_products: List[str], catalog_features: Dict[str, List[str]]):
        """catalog_products: list of all known product names.
        catalog_features: {product_name: [feature_name_1, feature_name_2, ...]}."""
        ...

    def strip_pricing(self, text: str) -> Tuple[str, bool, List[str]]:
        """Regex scan per §10.4 for:
        - Currency symbols: $, €, ₹, £, ¥
        - Keywords: 'price', 'pricing', 'cost', 'costs', 'fee', 'fees', 'discount',
          'per user/month', 'annual fee', 'subscription cost', 'TCO', 'budget', 'investment'
        - Patterns: digits followed by currency words
        Strips entire sentence containing the match. §10.4.
        Replaces with: '[Pricing information removed — contact iValue Sales.]'
        Returns (cleaned_text, was_stripped, list_of_stripped_phrases)."""
        ...

    def check_hallucinations(self, text: str, retrieved_pids: List[str]) -> List[str]:
        """§11.2: Extract product names from generated text.
        Check each against catalog (fuzzy match >90% similarity).
        Extract feature claims ('supports X', 'provides Y', 'includes Z').
        Check each against catalog_features for cited product.
        Returns list of '[Unverified claim]: ...' strings."""
        ...

    def truncate_repetition(self, text: str, n_gram: int = 10, max_repeats: int = 3) -> Tuple[str, bool]:
        """§10.4: Check for same 10+ word n-gram appearing 3+ times.
        If found, truncate at first repetition.
        Append '...[Output truncated due to a generation issue.]'
        Returns (cleaned_text, was_truncated)."""
        ...

    def check_prompt_injection(self, text: str) -> Tuple[bool, List[str]]:
        """§10.8: Pre-generation keyword scan for injection patterns:
        'ignore previous instructions', 'system prompt', 'forget your rules', 'act as', 'you are now'.
        Returns (is_suspicious, matched_keywords). Does NOT block — just flags for logging."""
        ...

    def check_data_exfiltration(self, text: str) -> bool:
        """§10.8: Post-generation check if output contains system prompt fragments
        or schema terms used in a meta/instructional context.
        Returns True if exfiltration attempt detected."""
        ...

    def validate_full(self, generated_text: str, retrieved_pids: List[str]) -> dict:
        """Runs all validators in sequence:
        1. strip_pricing
        2. check_hallucinations
        3. truncate_repetition
        4. check_data_exfiltration
        Returns dict: {cleaned_text, pricing_stripped, hallucinations, repetition_truncated, exfiltration_blocked}."""
        ...
```

**Acceptance criteria / Definition of Done:**
- `strip_pricing("This costs $500 per month.")` strips the sentence and returns `was_stripped=True` (SEC-05).
- `strip_pricing("CyberArk provides session recording.")` returns `was_stripped=False`.
- `check_hallucinations(...)` flags a product name not in the catalog.
- `truncate_repetition(...)` catches 10-word sequences repeated 3+ times.
- `check_prompt_injection("ignore previous instructions")` returns `is_suspicious=True` (SEC-01).
- Passes NEG tests involving pricing (SEC-05, SEC-06), injection (SEC-01, SEC-02), and exfiltration (SEC-03, SEC-04).

**Do NOT:**
- Call any LLM or Ollama.
- Add UI code.
- Remove or modify the pricing regex patterns — they must be strict per §10.4.

---

### TASK-P1.9 — Create BOM exporter (.xlsx)

**SRS refs:** §3 Phase 2 step 3, §8.4, §10.5, §9.10

**Depends on:** TASK-P1.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/exporters.py`

**Implementation spec:**

```python
from dataclasses import dataclass
from typing import List, Optional

# Import the BomItem and BomExportRequest dataclasses from §8.3 verbatim.

class BOMExporter:
    """Generates formatted Excel BOM (.xlsx) with blank pricing columns. §8.4."""

    def export(self, request: BomExportRequest) -> ExportResponse:
        """Creates .xlsx via openpyxl with columns per §8.4 BOM format:
        S.No. | OEM | Product Name | Product Category | Model/Part Reference |
        Quantity | Licensing Model | License Term | Licensing Unit |
        Deployment Model | Support Tier | Unit Price | Total Price | Remarks

        - Unit Price header: 'Unit Price — To be filled by Sales'
        - Total Price header: 'Total Price — To be filled by Sales'
        - Unit Price and Total Price cells: ALWAYS BLANK.
        - Row 1 disclaimer: 'DRAFT — PRICING NOT INCLUDED — FOR INTERNAL USE ONLY'
        - Standard iValue InfoSolutions header row.
        - Missing fields: fill with 'TBD — Consult Sales' per §10.5.
        - Column widths auto-sized for readability.
        """
        ...
```

- Use `openpyxl` for Excel generation.
- Include the dataclass definitions from §8.3: `BomItem`, `BomExportRequest`, `ExportResponse`.
- Handle disk-full errors per §10.5.

**Acceptance criteria / Definition of Done:**
- Generated `.xlsx` opens in Excel with all 14 columns.
- Unit Price and Total Price cells are blank (INT-08, §12.4).
- Disclaimer row is present: `"DRAFT — PRICING NOT INCLUDED — FOR INTERNAL USE ONLY"`.
- Missing licensing fields are filled with `"TBD — Consult Sales"` (§10.5).
- Passes INT-08.

**Do NOT:**
- Add any pricing values, estimates, or formulas to price columns.
- Add UI code.
- Generate BOQ in this task (that's TASK-P1.10).

---

### TASK-P1.10 — Create BOQ exporter (.docx)

**SRS refs:** §3 Phase 2 step 4, §8.4, §10.5

**Depends on:** TASK-P1.9

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/exporters.py` (append to existing file)

**Implementation spec:**

```python
class BOQExporter:
    """Generates formal Word proposal (.docx) with blank pricing columns. §8.4."""

    def export(self, request: BoqExportRequest) -> ExportResponse:
        """Creates .docx via python-docx per §8.4 BOQ format:
        - Header: 'iValue InfoSolutions' (configurable heading)
        - Metadata: Customer Name, Project Reference, Date (auto), Prepared By
        - Line items table mirroring BOM structure with blank price columns
        - Price column headers: 'Unit Price' and 'Total Price' (currency-neutral, optional currency_code)
        - All price cells: BLANK
        - Footer note: 'Pricing to be completed by iValue Sales Team'
        - Watermark text in header: 'DRAFT — PRICING NOT INCLUDED'
        - Document version and generation timestamp in footer
        """
        ...
```

- Import `BoqExportRequest` dataclass from §8.3.
- Use `python-docx` for Word document generation.
- Handle disk-full errors per §10.5 and template rendering failures (CSV fallback per §10.5).

**Acceptance criteria / Definition of Done:**
- Generated `.docx` opens in Word with formatted letterhead.
- Price columns present but all cells blank (INT-09, §12.4).
- Watermark text is present (§12.4).
- Footer says "Pricing to be completed by iValue Sales Team".
- Passes INT-09.

**Do NOT:**
- Add any pricing values.
- Add UI code.
- Modify the BOMExporter class created in TASK-P1.9.

---

### TASK-P1.11 — Create PrismService façade

**SRS refs:** §8.3

**Depends on:** TASK-P1.4, TASK-P1.5, TASK-P1.6, TASK-P1.7, TASK-P1.8, TASK-P1.9, TASK-P1.10

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/service.py`

**Implementation spec:**

Implement the `PrismService` class exactly matching the interface in §8.3:

```python
class PrismService:
    """Core in-process service contract exposed by src/core/ to the GUI. §8.3."""

    def __init__(self):
        """Initializes all core components:
        - DocumentParser
        - HybridRetriever (loads embeddings, metadata, model)
        - ContextAssembler
        - OllamaServiceManager
        - OllamaStreamingClient
        - ResponseValidator
        - BOMExporter
        - BOQExporter
        - QueryLogger
        """
        ...

    def analyze(self, req: AnalyzeRequest, token_stream_callback=None, cancel_event=None) -> AnalyzeResponse:
        """Full pipeline: validate input → extract if file → hybrid retrieval → context assembly →
        streaming LLM → post-validation → return results.
        Calls token_stream_callback(token_str) for each streamed token.
        Respects cancel_event for preemption. §9.9 states 3-8."""
        ...

    def generate_bom(self, req: BomExportRequest) -> ExportResponse:
        ...

    def generate_boq(self, req: BoqExportRequest) -> ExportResponse:
        ...

    def get_product(self, product_id: str) -> Optional[ProductDetails]:
        ...

    def get_domains(self) -> DomainTaxonomyResponse:
        ...

    def get_health(self) -> SystemHealthResponse:
        ...
```

- Import and use all dataclasses from §8.3.
- The `analyze` method orchestrates the complete pipeline with timing for each stage (§11.1 latency dict).
- **LOCKED DECISION — Non-English input check:** The `analyze()` method is the SOLE location for the non-English input check (§10.1). Implement the Unicode script range check here: if >20% of non-whitespace chars have `ord(c) > 0x024F`, return `AnalyzeResponse(status="error", error_message="Only English text is supported.")` immediately. Do NOT duplicate this check in `retrieval.py` or anywhere else.
- Confidence scoring via `compute_fit_score()` and `compute_confidence_tier()`.

**Acceptance criteria / Definition of Done:**
- `PrismService()` initializes without error when all dependencies are available.
- `analyze()` returns an `AnalyzeResponse` with `status="success"` for a valid query.
- `analyze()` returns `status="zero_results"` when similarity < SIMILARITY_FLOOR.
- `generate_bom()` delegates to BOMExporter and returns an ExportResponse.
- `get_health()` returns accurate SystemHealthResponse.
- Passes INT-06 (full pipeline typed text → display).

**Do NOT:**
- Add UI code.
- Add threading logic (that's in `worker.py`).
- Create new dataclasses — use those from §8.3 exactly.

---

## Phase 2 — Threading & Concurrency

---

### TASK-P2.1 — Create worker thread dispatcher and queue protocol

**SRS refs:** §9.8, §9.9, §10.7

**Depends on:** TASK-P1.11

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/core/worker.py`

**Implementation spec:**

```python
import threading
import queue
from typing import Optional

class WorkerThread:
    """Background daemon thread for RAG pipeline execution. §9.8."""

    def __init__(self, service: PrismService, ui_queue: queue.Queue):
        self._service = service
        self._queue = ui_queue
        self._cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def start_analysis(self, request: AnalyzeRequest) -> None:
        """Dispatches a new analysis on a daemon thread. §9.8 item 1-2.
        If a thread is already running, preempts it per §9.8 item 5 (H-6):
        1. Sets cancel_event
        2. Emits STATUS toast 'Cancelling active analysis...'
        3. Joins thread up to 2.0s
        4. Resets state
        5. Starts new thread
        """
        ...

    def cancel(self) -> None:
        """Sets cancel_event and waits up to 2.0s for thread join. §10.7."""
        ...

    @property
    def is_running(self) -> bool:
        ...

    def _run(self, request: AnalyzeRequest) -> None:
        """Worker entry point. Wrapped in global try/except per §10.6.
        Emits queue messages using the exact protocol from §9.10 item 4:
        - {"type": "STATUS_STEP", "step": 1|2|3, "label": "..."}
        - {"type": "STREAM_TOKEN", "token": "..."}
        - {"type": "STREAM_COMPLETE", "full_text": "..."}
        - {"type": "ANALYSIS_SUCCESS", "payload": AnalyzeResponse}
        - {"type": "ANALYSIS_ERROR", "error_type": "TIMEOUT"|"OOM"|"NETWORK", "message": "..."}
        - {"type": "ANALYSIS_CANCELLED"}
        """
        ...
```

- Thread must be `daemon=True` per §9.8.
- Global exception handler wraps `_run()` per §10.6 — catches everything, sends ANALYSIS_ERROR to queue, resets UI state. Never lets an exception silently kill the thread.
- Implements the 3-step stepper: step 1 = Embedding & Catalog Scan, step 2 = Metadata Filtering & Context Assembly, step 3 = Phi-4-mini Grounded Generation.

**Acceptance criteria / Definition of Done:**
- Starting a worker posts `STATUS_STEP` messages to the queue.
- Token streaming posts `STREAM_TOKEN` messages.
- Successful completion posts `ANALYSIS_SUCCESS`.
- Cancelling mid-inference posts `ANALYSIS_CANCELLED` within 2s.
- Exception in worker posts `ANALYSIS_ERROR` and does not crash the process (§10.6).
- Double-dispatch preempts the first thread cleanly (NEG-15 prerequisite).

**Do NOT:**
- Import Tkinter or any UI module.
- Touch UI widgets directly from the worker thread.
- Add retry logic beyond what §10 specifies.

---

## Phase 3 — UI Shell

---

### TASK-P3.1 — Create theme JSON and design tokens module

**SRS refs:** §8.1.2, §8.1.3, §8.1.4, §8.1.11

**Depends on:** none

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `themes/ivalue_prism.json`

**Implementation spec:**

Create the CustomTkinter theme JSON file matching the brand palette in §8.1.2 **exactly**. The file must follow CustomTkinter's theme JSON schema.

Include all color tokens from §8.1.2:
- `bg_canvas`: `("#F1F5F9", "#0B1120")`
- `bg_sidebar`: `("#E2E8F0", "#0F172A")`
- `bg_card_base`: `("#FFFFFF", "#131F37")`
- `bg_card_elevated`: `("#F8FAFC", "#1E293B")`
- `bg_input`: `("#FFFFFF", "#0D1527")`
- `border_subtle`: `("#CBD5E1", "#1E293B")`
- `border_strong`: `("#94A3B8", "#334155")`
- `border_accent`: `("#0284C7", "#38BDF8")`
- `text_primary`: `("#0F172A", "#F8FAFC")`
- `text_secondary`: `("#475569", "#94A3B8")`
- `text_muted`: `("#64748B", "#64748B")`
- `brand_purple`: `("#4C1D95", "#7C3AED")`
- `brand_accent`: `("#0284C7", "#0EA5E9")`
- `accent_hover`: `("#0369A1", "#38BDF8")`

Semantic status tokens from §8.1.2:
- `success`: `("#059669", "#10B981")` — HIGH fit, online
- `warning`: `("#D97706", "#F59E0B")` — MED fit, warning
- `error`: `("#DC2626", "#EF4444")` — LOW fit, offline
- `info`: `("#0284C7", "#38BDF8")` — informational

Spacing tokens from §8.1.4:
- `space_xs: 4`, `space_sm: 8`, `space_md: 12`, `space_lg: 16`, `space_xl: 24`, `space_2xl: 32`, `space_3xl: 48`

Typography from §8.1.3:
- Font family: `"Segoe UI"`, monospace: `"Cascadia Mono"`
- Type scale entries: Display (24pt/700), H1 (18pt/700), H2 (15pt/600), H3 (13pt/600), Body Large (12pt/500), Body Regular (11pt/400), Body Small (10pt/400), Caption (9pt/400), Overline (8.5pt/700)

Layout from §8.1.4:
- `sidebar_width: 280`, `min_width: 1024`, `min_height: 640`, `default_width: 1280`, `default_height: 820`, `max_content_width: 1180`

**Acceptance criteria / Definition of Done:**
- File is valid JSON and loadable with `json.load()`.
- All hex values from §8.1.2 are present and correct.
- All spacing, typography, and layout values from §8.1.3-4 are present.
- File is self-contained — no external imports required.

**Do NOT:**
- Add Python code to this file (it's JSON only).
- Invent colors not specified in §8.1.2.
- Modify the file tree structure in §8.1.11.

---

### TASK-P3.2 — Create splash preloader (Phase B)

**SRS refs:** §8.1.7, §8.1.7a

**Depends on:** TASK-P3.1, TASK-P1.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/splash.py`

**Implementation spec:**

Refer to skill file `.agents/skills/pyinstaller-splash-bootloader/SKILL.md` for the two-phase splash pattern.

```python
class SplashPreloader(customtkinter.CTkToplevel):
    """Phase B in-process splash. §8.1.7."""

    def __init__(self):
        """Creates borderless 480×340px window, centered.
        Background: #0B1120.
        Contains:
        - 96×96px PRISM logo (assets/branding/ivalue_prism_logo.jpg, fallback to text)
        - Title: 'iValue PRISM' (Display 24pt Bold)
        - Subtitle: 'Presales Recommendation & Intelligence System'
        - Indeterminate progress bar (#0EA5E9)
        - 4-line initialization checklist (initially all pending)

        Immediately calls pyi_splash.close() per §8.1.7a to hand off from C-bootloader splash.
        """
        ...

    def update_step(self, step: int, label: str, elapsed: float) -> None:
        """Updates checklist item to green checkmark with timing.
        Steps 1-4 per §8.1.7:
        1. Python desktop runtime initialized
        2. Semantic vector index mounted (139 OEM products)
        3. Sentence-transformers embedding model loaded
        4. Verifying Ollama daemon & warming Phi-4-mini
        """
        ...

    def finish(self, callback: callable) -> None:
        """All 4 checks green → 300ms cross-fade → destroy splash → invoke callback.
        Callback is typically PRISMApp().mainloop(). §8.1.7."""
        ...
```

**Acceptance criteria / Definition of Done:**
- Splash window appears centered at 480×340px.
- Checklist items update in sequence.
- `pyi_splash.close()` called safely with ImportError guard for dev mode (§8.1.7a).
- 300ms cross-fade before main app launch.
- Passes STR-10 (mechanical HDD bootloader latency) when packaged.

**Do NOT:**
- Add the main application logic (that's TASK-P3.3).
- Skip the `pyi_splash.close()` call — it is required for the two-stage handoff.
- Add heavy imports in this module (keep it fast to load).

---

### TASK-P3.3 — Create main application window (PRISMApp) and entry point

**SRS refs:** §8.1.1, §8.1.6, §9.8, §9.9 states 0-1

**Depends on:** TASK-P3.1, TASK-P3.2, TASK-P2.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/app.py`
- `main.py`

**Implementation spec:**

**`main.py`** — Application entry point:
```python
"""iValue PRISM entry point.
1. Show SplashPreloader
2. Initialize PrismService (on splash background)
3. Transition to PRISMApp main window
"""
```
- Acquire single-instance mutex per §10.7 via `verify_single_instance()`.
- Mount SplashPreloader, run initialization steps 1-4 on background thread updating splash.
- On completion, destroy splash and create PRISMApp.
- Set Windows AppUserModelID: `"iValue.PRISM.PresalesDesktop.v3"` per §8.1.1.

**`src/ui/app.py`** — Main window:
```python
class PRISMApp(customtkinter.CTk):
    """Root application window. §8.1.1, §8.1.6."""

    def __init__(self, service: PrismService):
        """
        - Title: 'iValue PRISM — Presales Recommendation & Intelligence System [v3.4]' §8.1.1
        - Icon: assets/branding/ivalue_prism.ico (if exists)
        - Geometry: load from ConfigManager, default 1280×820, centered. §8.1.6
        - Minimum size: 1024×640 via root.minsize(). §8.1.6
        - Layout: sidebar (280px fixed left) + main canvas (flex right, 24px padding)
        - Queue polling: app.after(50, self._process_queue) §9.8 item 4
        - WM_DELETE_WINDOW protocol: graceful shutdown per §9.8 item 6
        """
        ...

    def _process_queue(self) -> None:
        """Polls ui_queue every 50ms. Routes messages to appropriate UI handlers.
        Message types from §9.10 item 4."""
        ...

    def _on_close(self) -> None:
        """Graceful shutdown per §9.8 item 6:
        1. Check if worker running → cancel_event.set()
        2. Join worker thread up to 3.0s
        3. Save window geometry to config
        4. app.destroy()
        """
        ...

    def _validate_window_position(self, x, y, w, h) -> Tuple[int, int, int, int]:
        """Boundary validation for disconnected monitors. §10.6."""
        ...
```

**Acceptance criteria / Definition of Done:**
- Application launches with correct title and icon.
- Window restores geometry from config or defaults to 1280×820 centered.
- Minimum size 1024×640 enforced.
- Queue polling runs every 50ms.
- Graceful shutdown saves geometry and joins worker thread.
- Second instance detection works (INT-14).
- Off-screen window position is corrected (§10.6 display config change).

**Do NOT:**
- Implement sidebar, input panel, or result cards (those are separate tasks).
- Add the full analysis pipeline (the queue handler stubs are sufficient).

---

### TASK-P3.4 — Create sidebar view

**SRS refs:** §8.1.5 item 1, §8.1.13

**Depends on:** TASK-P3.1, TASK-P1.1, TASK-P1.3

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/components/__init__.py` ← **Create this first** (empty file, establishes the package)
- `src/ui/components/sidebar.py`

**Implementation spec:**

```python
class SidebarView(customtkinter.CTkFrame):
    """Left navigation sidebar. §8.1.5 item 1."""

    def __init__(self, parent, service: PrismService, config: ConfigManager, **kwargs):
        """Width: 280px, full height. §8.1.4.
        Contains (top to bottom):
        - Header lockup: 40×40 PRISM logo + 'iValue PRISM' H2 + v3.4 badge pill
        - System status panel: Ollama status indicator, model badge, index count, RAM meter
        - Session history reel: FIFO list of up to 20 SessionSnapshot items
        - Utility actions: New Query, Clear Workspace, Re-index Catalog
        - Theme switcher: CTkSegmentedButton [Dark | Light | System] at bottom
        """
        ...

    def update_health(self, health: SystemHealthResponse) -> None:
        """Updates status indicators from health check. §11.4."""
        ...

    def add_session(self, snapshot: SessionSnapshot) -> None:
        """Adds a query to the session history reel. §8.1.5 item 1."""
        ...

    def set_on_session_restore(self, callback) -> None:
        """Sets callback for when user clicks a session history item. §8.1.5 item 1."""
        ...
```

- Ollama status: 8×8px circle via `CTkCanvas.create_oval()` with `#10B981`/`#EF4444` per §8.1.5.
- RAM meter: live bar showing process usage from `get_ram_usage_mb()`.
- Theme switcher: `customtkinter.set_appearance_mode()` per §8.1.13.
- Reduced-motion check: `check_reduced_motion()` from system_info.

**Acceptance criteria / Definition of Done:**
- Sidebar renders at 280px width.
- Ollama status shows green circle + "Online" when online, red + "OFFLINE" when not.
- Theme switcher toggles dark/light/system modes instantly without restart.
- Session history shows clickable query previews.
- RAM meter updates from psutil data.

**Do NOT:**
- Add analysis logic or pipeline code.
- Change sidebar width from 280px.
- Use bitmap emojis for status indicators.

---

### TASK-P3.5 — Create requirement input panel

**SRS refs:** §8.1.5 item 2, §FR-1, §FR-1a, §FR-14

**Depends on:** TASK-P3.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/components/input_panel.py`

**Implementation spec:**

```python
class RequirementInputPanel(customtkinter.CTkFrame):
    """Customer requirement input area. §8.1.5 item 2."""

    def __init__(self, parent, **kwargs):
        """Contains:
        - Section title: 'Customer Requirement & RFP Input' (H2 Semi-Bold)
        - File loader button: 'Load RFP (.pdf, .docx, .txt)' with folder icon, dashed border
        - CTkTextbox: 140px height, 8px radius, placeholder text per §8.1.5
        - Footer metadata bar: live token/char gauge with color transitions
        - 'Analyze Requirement' button: 42px height, brand_accent, search icon
        - 'Cancel' button (hidden by default, shown during inference)
        """
        ...

    def get_text(self) -> str:
        ...

    def set_text(self, text: str) -> None:
        ...

    def set_analyzing(self, is_analyzing: bool) -> None:
        """Toggles between Analyze/Cancel button states. §10.7."""
        ...

    def set_on_analyze(self, callback) -> None:
        ...

    def set_on_file_load(self, callback) -> None:
        ...

    def _update_gauge(self, *args) -> None:
        """Live character & token gauge per §8.1.5 item 2.
        Green (<8000 chars) → Amber (8000-10000) → Crimson (>10000).
        Uses estimate_tokens() from config.py."""
        ...
```

- Keyboard shortcuts per §6.9: `Ctrl+Enter` to submit, `Ctrl+O` to open file dialog, `Escape` to cancel.
- File dialog uses `tkinter.filedialog.askopenfilename` with filter for `.txt`, `.pdf`, `.docx`.
- Input validation: reject empty (NEG-01, NEG-02), warn on short (NEG-03), truncation warning on long (NEG-05).

**Acceptance criteria / Definition of Done:**
- Textbox accepts text input and shows placeholder.
- Token gauge updates live as user types.
- File loader opens native Windows file picker.
- Analyze button disables during inference.
- Keyboard shortcuts work (Ctrl+Enter, Ctrl+O, Escape).

**Do NOT:**
- Add the document extraction modal (that's TASK-P4.3).
- Add the results display.
- Handle drag-and-drop (stretch goal, not specified in task).

---

## Phase 4 — Result Rendering

---

### TASK-P4.1 — Create token stream terminal

**SRS refs:** §8.1.5 item 3

**Depends on:** TASK-P3.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/components/stream_box.py`

**Implementation spec:**

```python
class TokenStreamTerminal(customtkinter.CTkFrame):
    """Live token streaming display and pipeline stepper. §8.1.5 item 3."""

    def __init__(self, parent, **kwargs):
        """Contains:
        - Progress shimmer bar: CTkProgressBar, 6px height, 3px radius
        - Stage checklist stepper: 3 phases with status icons
        - Token stream terminal: 90px (expandable), background #0A0F1D, Cascadia Mono 11pt
          with blinking caret (#38BDF8, 500ms cycle)
        """
        ...

    def set_step(self, step: int, status: str = "active") -> None:
        """Updates stepper phase. Steps 1-3 per §8.1.5 item 3."""
        ...

    def append_token(self, token: str) -> None:
        """Appends a single token to the stream terminal."""
        ...

    def reset(self) -> None:
        """Clears terminal and resets stepper to initial state."""
        ...

    def show(self) -> None:
        ...

    def hide(self) -> None:
        ...
```

- Blinking caret: 500ms cycle using `after()`.
- Reduced-motion: no shimmer if `check_reduced_motion()` is True (§8.1.10).

**Acceptance criteria / Definition of Done:**
- Progress bar animates during inference.
- Stepper shows 3 phases with real-time status.
- Tokens appear one by one in terminal with blinking caret.
- Terminal auto-scrolls as tokens arrive.

**Do NOT:**
- Handle queue polling (that's in PRISMApp).
- Call Ollama directly.

---

### TASK-P4.2 — Create recommendation result cards

**SRS refs:** §8.1.5 item 4, §8.1.14, §FR-9

**Depends on:** TASK-P3.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/components/result_cards.py`

**Implementation spec:**

```python
class PrimaryRecommendationCard(customtkinter.CTkFrame):
    """Top-pick recommendation card. §8.1.5 item 4."""

    def __init__(self, parent, recommendation: ProductRecommendation, **kwargs):
        """Elevated card with:
        - 1px border_accent, 4px left accent bar, 12px radius, 20px padding
        - OEM & Product title (H1 Bold)
        - Citation pill: '[Catalog: OEM-xxx-Pxx | Confirmed]'
        - Executive rationale (Body Large)
        - Key differentiators as flex-wrap pill chips
        - Pros/Cons 2-column grid
        - Decision toolbar: [Accept] [Modify Rationale] [Exclude/Reject]
        """
        ...

    def set_on_accept(self, callback) -> None: ...
    def set_on_modify(self, callback) -> None: ...
    def set_on_reject(self, callback) -> None: ...


class AlternativeCard(customtkinter.CTkFrame):
    """Collapsed alternative candidate card. §8.1.5 item 4."""

    def __init__(self, parent, recommendation: ProductRecommendation, **kwargs):
        """Muted surface, clickable header to expand/collapse (200ms animation)."""
        ...


class ResultsCanvas(customtkinter.CTkScrollableFrame):
    """Container for verdict header + recommendation cards. §8.1.5 item 4."""

    def __init__(self, parent, **kwargs):
        ...

    def show_results(self, response: AnalyzeResponse) -> None:
        """Renders verdict summary header (domain badge, confidence pill, copy button)
        + primary card + alternative cards."""
        ...

    def clear(self) -> None:
        ...
```

- Confidence pill: color per §8.1.2 semantic status tokens, text per §6.9.
- Copy button: morphs to "✓ Copied to Clipboard!" for 2.0s per §8.1.10.
- Decision toolbar per §8.1.14: Accept (green), Modify Rationale (ghost), Exclude (destructive ghost).
- Modify Rationale: converts rationale to editable CTkTextbox with Save/Revert buttons.
- Reject: inline reason popover with options per §8.1.14.
- Confidence badge pulse: 400ms scale animation per §8.1.10 (skip if reduced-motion).

**Acceptance criteria / Definition of Done:**
- Primary card renders with all specified elements.
- Alternative cards are collapsed by default, expandable.
- Accept button tags product for BOM/BOQ, changes card border to green.
- Copy button copies markdown to clipboard with visual feedback (INT-11).
- Reject button shows reason popover.

**Do NOT:**
- Add the BOM export panel (that's TASK-P5.1).
- Call any backend service directly.

---

### TASK-P4.3 — Create document extraction modal

**SRS refs:** §8.1.12, §FR-13

**Depends on:** TASK-P3.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/components/extraction_modal.py`

**Implementation spec:**

```python
class DocumentPreviewModal(customtkinter.CTkToplevel):
    """Extracted text review & edit modal. §8.1.12."""

    def __init__(self, parent, extraction_result: ExtractionResult, **kwargs):
        """760×540px modal, centered over parent with dimming backdrop.
        Header: 'Extracted Requirement Review' (H2 Semi-Bold)
        Subtitle: 'Extracted from <filename> (Size: <filesize> KB)...'
        Editable CTkTextbox: full width - 32px, 360px height, Segoe UI 11pt
        Footer: extraction metrics + Discard/Confirm buttons per §8.1.12.
        """
        ...

    def set_on_confirm(self, callback) -> None:
        """Callback receives the edited text."""
        ...

    def set_on_discard(self, callback) -> None:
        ...
```

**Acceptance criteria / Definition of Done:**
- Modal appears centered at 760×540.
- Extracted text is shown and editable.
- "Confirm & Analyze" commits text and closes modal.
- "Discard & Re-upload" closes modal without action.
- Extraction metrics (chars, tokens) displayed correctly.

**Do NOT:**
- Add document parsing logic (that's in `ingestion.py`).
- Make the modal non-modal (it must block interaction with the main window).

---

### TASK-P4.4 — Create toast notification manager

**SRS refs:** §8.1.9

**Depends on:** TASK-P3.1

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/components/toast.py`

**Implementation spec:**

```python
class ToastNotificationManager:
    """Sliding toast notification system. §8.1.9."""

    def __init__(self, parent):
        ...

    def show(self, message: str, variant: str = "info", duration_ms: int = 4000,
             action_text: str = None, action_callback: callable = None) -> None:
        """Shows a toast notification.
        Variants: 'success' (green, 4s), 'info' (blue, 4s), 'warning' (amber, 6s), 'error' (red, persistent).
        Position: bottom-right, 16px margin. Width: 340px.
        Stacking: max 3 visible, oldest auto-dismissed.
        Motion: slide in from right (180ms), fade out (120ms). Skip if reduced-motion.
        Optional action button (e.g., 'Open Document', 'Show in Explorer').
        """
        ...

    def dismiss(self, toast_id: str) -> None:
        ...

    def dismiss_all(self) -> None:
        ...
```

**Acceptance criteria / Definition of Done:**
- Success, info, warning, error toasts render with correct colors.
- Auto-dismiss timing matches spec (4s/4s/6s/persistent).
- Max 3 toasts visible, oldest dismissed on overflow.
- Action button triggers callback when clicked.
- Slide-in animation (or instant if reduced-motion).

**Do NOT:**
- Add non-spec toast types.
- Block the main thread with toast operations.

---

### TASK-P4.5 — Create welcome zero-state guidance

**SRS refs:** §8.1.8

**Depends on:** TASK-P3.1, TASK-P3.5

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/components/welcome.py`

**Implementation spec:**

```python
class WelcomeView(customtkinter.CTkFrame):
    """Zero-state guidance shown before first query. §8.1.8."""

    def __init__(self, parent, **kwargs):
        """Centered layout:
        - 64×64 semi-translucent PRISM mark
        - Heading: 'Ready to formulate your next presales recommendation' (H1 Bold)
        - Subheading per §8.1.8
        - 3 interactive quick-start cards with exact text from §8.1.8:
          1. PAM Requirement
          2. NGFW Requirement
          3. SIEM & Log Analytics
        """
        ...

    def set_on_template_select(self, callback) -> None:
        """Callback receives the template text string to populate input panel."""
        ...
```

**Acceptance criteria / Definition of Done:**
- 3 quick-start cards shown with exact requirement text from §8.1.8.
- Clicking a card populates the input panel and highlights Analyze button.
- Welcome view is hidden when results are displayed.

**Do NOT:**
- Trigger analysis automatically on card click.
- Add templates not specified in §8.1.8.

---

## Phase 5 — BOM/BOQ Export

---

### TASK-P5.1 — Create export control panel (tksheet BOM grid)

**SRS refs:** §8.1.5 item 5, §8.4

**Depends on:** TASK-P3.1, TASK-P1.9, TASK-P1.10

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `src/ui/components/export_panel.py`

**Implementation spec:**

Refer to skill file `.agents/skills/bom-grid-tksheet/SKILL.md` for the tksheet implementation pattern.

```python
class ExportControlPanel(customtkinter.CTkFrame):
    """BOM/BOQ interactive export panel with tksheet grid. §8.1.5 item 5."""

    def __init__(self, parent, **kwargs):
        """Hidden by default. Shown when at least one product is Accepted.
        Contains:
        - tksheet grid with columns: Product Name, Category, License Qty, License Term, Support Tier
        - Embedded controls per §8.1.5 item 5:
          - Quantity: numeric spinbox (1-99999)
          - License Term: dropdown (1-Year, 3-Year, 5-Year, Perpetual)
          - Support Tier: dropdown (Standard, 24x7 Enterprise, Mission Critical)
        - Compliance warning banner per §8.1.5 item 5
        - Export buttons: 'Export BOM (.xlsx)' and 'Export BOQ (.docx)'
        - Themed per §8.1.5 item 5: dark headers, alternating rows, accent borders
        """
        ...

    def add_product(self, recommendation: ProductRecommendation) -> None:
        ...

    def remove_product(self, product_id: str) -> None:
        ...

    def get_bom_items(self) -> List[BomItem]:
        """Reads current grid state and returns BomItem list."""
        ...

    def set_on_export_bom(self, callback) -> None:
        ...

    def set_on_export_boq(self, callback) -> None:
        ...
```

- tksheet v7.0.0+ for grid rendering.
- Dark-theme colors from §8.1.5 item 5: header `#0F172A`/`#E2E8F0`, rows `#131F37`+`#0D1527` / `#FFFFFF`+`#F8FAFC`, accent `#0EA5E9`.
- Compliance warning: `"[!] Pricing is intentionally omitted and must be completed by Sales per iValue commercial policy."`.
- Post-export: show toast with "Open Document" and "Show in Explorer" actions per §8.1.15.
- File save dialog pre-populated with naming per §8.1.15.

**Acceptance criteria / Definition of Done:**
- Grid renders with strict column alignment regardless of row count (§12.8 BOM grid regression).
- Quantity spinbox validates integers 1-99999.
- License Term and Support Tier dropdowns work correctly.
- Export BOM generates .xlsx via BOMExporter.
- Export BOQ generates .docx via BOQExporter.
- Dark and light theme rendering works correctly (§12.8).
- Passes INT-08, INT-09.

**Do NOT:**
- Use hand-rolled nested CTkFrame grids (§9.5 explicitly rejected).
- Add pricing columns to the grid display.

---

## Phase 6 — Packaging

---

### TASK-P6.1 — Generate boot splash image

**SRS refs:** §8.1.7a, §8.1.11

**Depends on:** none

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `assets/branding/boot_splash.png`

**Implementation spec:**

Generate a 420×280px branded static card image for the PyInstaller C-bootloader splash:
- Dark background (`#0B1120`)
- Centered iValue PRISM logo artwork (crystalline refractive prism motif)
- Text: "Starting iValue PRISM..." in white Segoe UI
- Subtle brand gradient accent along the bottom
- Clean, professional, matching the iValue brand palette (§8.1.2)

**Use the `generate_image` tool** with prompt: "A 420x280 pixel dark-themed application splash screen for 'iValue PRISM'. Dark navy background (#0B1120). Centered crystalline geometric prism logo reflecting light beams in purple (#7C3AED) to sky blue (#0EA5E9) gradient. Below the logo, white text 'Starting iValue PRISM...' in clean sans-serif font. Subtle gradient accent bar at the bottom edge in sky blue. Professional enterprise software branding. No device frames."

**Acceptance criteria / Definition of Done:**
- Image is exactly 420×280px PNG.
- Visually matches the brand palette from §8.1.2.
- Text "Starting iValue PRISM..." is readable.

**Do NOT:**
- Add device frames around the image.
- Use colors outside the brand palette.

---

### TASK-P6.2 — PyInstaller build configuration & native splash handoff

**SRS refs:** §9.7, §8.1.7a, §12.7 STR-10

**Depends on:** All prior tasks

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `main.py` (add pyi_splash import guard if not present)
- `prism.spec` (or build script)

**Implementation spec:**

Refer to skill file `.agents/skills/pyinstaller-splash-bootloader/SKILL.md`.

Create a PyInstaller spec file or build script matching §9.7 exactly:

```powershell
pyinstaller --noconfirm --onedir --windowed `
  --name "iValue_PRISM" `
  --add-data "data;data" `
  --icon "assets/branding/ivalue_prism.ico" `
  --splash "assets/branding/boot_splash.png" `
  --exclude-module "tkinter.test" `
  --exclude-module "unittest" `
  --exclude-module "pytest" `
  --exclude-module "scipy" `
  main.py
```

Verify `main.py` includes the pyi_splash handoff code from §8.1.7a:
```python
try:
    import pyi_splash
    pyi_splash.update_text("Initializing PRISM Core Engine...")
    pyi_splash.close()
except ImportError:
    pass
```

**Acceptance criteria / Definition of Done:**
- Build completes without errors.
- `dist/iValue_PRISM/iValue_PRISM.exe` launches successfully.
- C-bootloader splash appears within ≤2-3 seconds on HDD (STR-10).
- CTk SplashPreloader takes over after pyi_splash.close().
- Excluded modules are not in the dist folder.

**Do NOT:**
- Use `--onefile` (we use `--onedir` per §9.7).
- Bundle test dependencies.

---

### TASK-P6.3 — Generate icon and branding assets

**SRS refs:** §8.1.1, §8.1.11

**Depends on:** none

**Assigned to:** Fast execution model (Gemini). Escalate to Opus only via Escalation Log if blocked.

**Files you may create/modify (and ONLY these):**
- `assets/branding/ivalue_prism.ico`
- `assets/branding/ivalue_prism_logo.png`
- `assets/icons/` (directory with UI action icons)

**Implementation spec:**

1. **`ivalue_prism_logo.png`**: Convert existing `ivalue_prism_logo.jpg` to 512×512 PNG format.
2. **`ivalue_prism.ico`**: Create multi-resolution Windows ICO from the logo (16, 24, 32, 48, 64, 128, 256px). Use the `Pillow` library.
3. **`assets/icons/`**: Create placeholder 24×24px PNG icons for UI actions. These can be simple monochrome glyphs:
   - `search.png` — magnifying glass
   - `copy.png` — clipboard
   - `folder.png` — folder open
   - `document.png` — document page
   - `edit.png` — pencil
   - `table.png` — grid/table
   - `download.png` — download arrow

**Acceptance criteria / Definition of Done:**
- ICO file contains all required resolutions.
- PNG logo is 512×512.
- Icon files exist in `assets/icons/`.

**Do NOT:**
- Change the brand identity or color scheme.

---

## Escalation Log

| Task ID | Blocked On | Fast Model's Question | Opus Resolution | Status |
|---|---|---|---|---|
| *(empty — to be filled by executing agents)* | | | | |

---

## Walkthrough Log

*(One line per completed task, appended by the executing agent)*
- **TASK-P1.1** (2026-09-09): Implemented system constants, pure calculation functions (compute_fit_score, compute_confidence_tier, estimate_tokens), ConfigManager with disk persistence, and SessionSnapshot dataclass in src/utils/config.py.
- **TASK-P1.2** (2026-09-09): Implemented QueryLogger with append-only JSONL format, complete §11.1 schema validation, 50MB log rotation, user action tracking (§11.3), and stdlib logging to prism_app.log / prism_error.log in src/utils/logger.py.
- **TASK-P1.3** (2026-09-09): Implemented host resource diagnostics (RAM/CPU via psutil), Windows single-instance named mutex verification with subprocess validation, and Win32 reduced motion accessibility detection in src/utils/system_info.py.
- **TASK-P1.4** (2026-09-09): Implemented DocumentParser and ExtractionResult supporting .txt, .pdf, and .docx files with encoding fallbacks, encrypted/password PDF detection, scanned PDF detection, and strict validation in src/core/ingestion.py.
- **TASK-P1.5** (2026-09-09): Implemented HybridRetriever with bge-small-en-v1.5 dense vectors and NumPy brute-force cosine search, deterministic keyword & taxonomy filters, thread-safe index reload, and verified 95.0% Recall@3 and 95.0% Recall@5 in src/core/retrieval.py.
- **TASK-P1.6** (2026-09-09): Implemented ContextAssembler with verbatim §7.4 rules, progressive 5-stage truncation adhering to §7.5 priority order, and strict 1600-token prompt budgeting in src/core/context_builder.py.
- **TASK-P1.7** (2026-09-09): Implemented OllamaServiceManager with Windows binary discovery hierarchy, detached background auto-launch, model presence verification, and OllamaStreamingClient with cancellation events and 180s timeout enforcement in src/core/ollama_client.py.
- **TASK-P1.8** (2026-09-09): Implemented ResponseValidator in src/core/validators.py with zero-tolerance pricing regex filter (§10.4), hallucination detector for catalog products and features (§11.2), repetition loop truncator (§10.4), prompt injection pre-check (§10.8), and post-generation exfiltration blocking (§10.8).
- **TASK-P1.9** (2026-09-09): Implemented BOMExporter and §8.3 export dataclasses (BomItem, BomExportRequest, BoqExportRequest, ExportResponse) in src/core/exporters.py with 14 canonical columns, prominent red watermark disclaimer, blank pricing columns, and §10.5 fallback to CSV on formatting failure.
- **TASK-P1.10** (2026-09-09): Appended BOQExporter to src/core/exporters.py generating formal Word proposals (.docx) in landscape orientation via python-docx with iValue letterhead, "DRAFT — PRICING NOT INCLUDED" header watermark, strictly blank price cells, and sales footer note.
- **TASK-P1.11** (2026-09-09): Implemented PrismService façade in src/core/service.py orchestrating the complete presales pipeline: non-English guard (§10.1), pre-injection scanning (§10.8), hybrid retrieval (§7.2), context assembly (§7.4), streaming inference (§9.9), safety validation (§10.4), export delegation, and §11.1 query logging.
- **TASK-P2.1** (2026-09-09): Implemented WorkerThread in src/core/worker.py providing daemon-threaded asynchronous execution, queue protocol dictionary envelopes (§9.10 item 4: STATUS_STEP 1-3, STREAM_TOKEN, STREAM_COMPLETE, ANALYSIS_SUCCESS, ANALYSIS_ERROR with taxonomy categorization, and ANALYSIS_CANCELLED), double-dispatch preemption (H-6 / NEG-15), sub-50ms thread cancellation (§10.7), and zero Tkinter coupling.
- **TASK-P3.1** (2026-09-09): Configured CustomTkinter theme JSON in themes/ivalue_prism.json matching the iValue brand palette in §8.1.2 exactly (all 14 dual-mode color tokens, semantic status tokens with 10% opacity tint tokens, 4px/8px spacing grid tokens §8.1.4, Segoe UI typography hierarchy §8.1.3, and layout boundaries §8.1.4), fully verified with CustomTkinter widget instantiation.
- **TASK-P3.2** (2026-09-09): Implemented SplashPreloader in src/ui/splash.py supporting Phase A to Phase B C-bootloader splash handoff (pyi_splash.close() with ImportError guard), centered borderless 480×340px presentation with brand logo, neon progress bar, 4-stage sequential checklist update (§8.1.7), and 300ms cross-fade animation with reduced-motion accessibility check.
- **TASK-P3.3** (2026-09-09): Implemented PRISMApp in src/ui/app.py and main.py using a single-root Tkinter architecture to eliminate multi-root deadlocks (root PRISMApp created withdrawn, SplashPreloader parented to root, cross-fade to deiconify), 1280×820 centered geometry with 1024×640 minsize, §10.6 disconnected monitor self-healing, 50ms queue polling with message dispatching, graceful shutdown with worker cancellation and geometry persistence, Windows AppUserModelID registration (§8.1.1), and single-instance named mutex guard (§10.7).
- **TASK-P3.4** (2026-09-09): Implemented SidebarView in src/ui/components/sidebar.py with established src/ui/components/__init__.py package, enforcing fixed 280px width, 40×40 PRISM branding lockup + H2 + v3.4 badge pill (§8.1.5 item 1), live system health status panel (hardware vector dot for Ollama, model badge, catalog count, live RAM bar meter), interactive volatile FIFO session history reel (max 20 SessionSnapshot items with clickable previews and restoration callback), utility action toolbar (New Query, Clear Workspace, Re-index), and dynamic theme switcher ([Dark | Light | System] CTkSegmentedButton with live persistence §8.1.13).
- **TASK-P3.5** (2026-09-09): Implemented RequirementInputPanel in src/ui/components/input_panel.py featuring section header with native Windows document picker button (filtering .pdf, .docx, .txt), 140px CTkTextbox with placeholder support and 2px brand-accent focus glow (§8.1.5 item 2), live token/char gauge with 3-tier color transitions (Green <8k, Amber 8-10k, Crimson >10k), 42px primary Analyze and secondary Cancel buttons with state toggling (§10.7), keyboard accelerators (Ctrl+Enter, Ctrl+O, Escape §6.9), and input validation (empty rejection NEG-01/02, brief input notice NEG-03, max char limit NEG-05).
- **TASK-P4.1** (2026-09-10): Implemented TokenStreamTerminal in src/ui/components/stream_box.py featuring 6px progress shimmer bar with reduced-motion compliance (§8.1.10), 3-phase checklist stepper ([✓], [⟳], [·], [✕]) with auto-completing prior stages (§8.1.5 item 3), dark console terminal container (#0A0F1D) with Cascadia Mono 11pt, 500ms sky blue blinking caret (#38BDF8), and smooth auto-scrolling to the latest tokens.
- **TASK-P4.2** (2026-09-10): Implemented PrimaryRecommendationCard, AlternativeCard, and ResultsCanvas in src/ui/components/result_cards.py featuring 4px left accent bar, OEM & Product title (H1 Bold), catalog citation pill, in-place editable executive rationale with Save/Revert (§8.1.14), key differentiator flex chips, 2-column pros/cons grid, engineer decision toolbar ([✓ Accept] with emerald border shift, [Modify Rationale], [✕ Exclude / Reject] with reason popover), smooth 200ms accordion expansion, 400ms confidence badge pulse (§8.1.10), and one-click clipboard copy CTA with 2.0s checkmark morph.
- **TASK-P4.3** (2026-09-10): Implemented DocumentPreviewModal in src/ui/components/extraction_modal.py featuring 760×540 centered modal geometry over parent with grab_set() modal blocking (§8.1.12), window header with [✕] button and subtitle metrics, optional scanned/warning banner, 360px editable CTkTextbox with Segoe UI 11pt, live character and token gauge updated on typing, and action footer with [✕ Discard & Re-upload] and [✓ Confirm & Analyze Requirement] callbacks.
- **TASK-P4.4** (2026-09-10): Implemented ToastNotificationManager in src/ui/components/toast.py featuring non-blocking sliding toasts anchored to bottom-right (16px margin, 340px width, 8px radius, 1px border), 4 semantic status variants (success 4.0s, info 4.0s, warning 6.0s, error persistent §8.1.9), FIFO max-3 visible toast stacking with vertical repositioning, 180ms slide-in / 120ms slide-out animations with reduced-motion accessibility bypass (§8.1.10), manual [✕] dismissal, and optional interactive action buttons (§8.1.15).
- **TASK-P4.5** (2026-09-10): Implemented WelcomeView in src/ui/components/welcome.py featuring centered 64×64 PRISM refractive emblem (§8.1.8), H1 bold header and body subtitle, 3 interactive quick-start template cards (PAM, NGFW, SIEM) with hover physics and click-to-populate callback without auto-triggering analysis, and clean show()/hide() lifecycle toggling.
- **TASK-P5.1** (2026-09-10): Implemented ExportControlPanel in src/ui/components/export_panel.py featuring tksheet v7.6 DataGrid with locked column alignment across variable row counts (§8.1.5 item 5, §12.8), 5 standard proposal columns (strictly zero pricing), embedded in-cell numeric validation for Quantity (1-99999), embedded native dropdowns for License Term and Support Tier, amber compliance disclaimer banner, dual-theme styling (dark/light), auto-visibility toggle on item selection, pre-populated file save dialogs (§8.1.15), and export dispatch via BOMExporter (.xlsx) and BOQExporter (.docx) with shell-integration toasts.
- **TASK-P6.1** (2026-09-10): Generated 420×280px native PNG boot splash card at assets/branding/boot_splash.png matching the iValue brand palette (§8.1.2, §8.1.7a, §8.1.11), featuring dark navy background (#0B1120), centered crystalline geometric prism emblem, clear white 'Starting iValue PRISM...' text, and sky blue bottom accent bar.
- **TASK-P6.2** (2026-09-10): Configured PyInstaller build specification in prism.spec and main.py native C-bootloader splash handoff (pyi_splash.update_text / pyi_splash.close() inside try/except ImportError). Resolved the endless PyInstaller build freeze by aggressively pruning heavy non-runtime and web/ML test frameworks (streamlit, altair, pydeck, watchdog, uvicorn, starlette, websockets, sympy, pyarrow, torch.distributed, torch.testing, pytest, unittest) and disabling UPX overhead. Verified successful build into dist/iValue_PRISM/ with embedded boot_splash.png C-bootloader splash, bundled data/themes/assets, and clean launch verification of dist/iValue_PRISM/iValue_PRISM.exe (59 MB).
- **TASK-P6.3** (2026-09-10): Generated high-resolution 512×512 PNG brand logo at assets/branding/ivalue_prism_logo.png, multi-resolution Windows ICO at assets/branding/ivalue_prism.ico containing all 7 standard resolutions (16, 24, 32, 48, 64, 128, 256px), and 7 monochrome 24×24px action icons in assets/icons/ (search.png, copy.png, folder.png, document.png, edit.png, table.png, download.png).
- **FULL-AUDIT-RESOLUTION** (2026-09-10): Completed comprehensive point-to-point verification against SRS v3.4 and implementation plan. Resolved all 8 identified defects: (1) Wired PRISMApp (`src/ui/app.py`) integrating SidebarView, RequirementInputPanel, WelcomeView, TokenStreamTerminal, ResultsCanvas, ExportControlPanel, ToastNotificationManager, and DocumentPreviewModal with complete queue routing and bidirectional event dispatching; (2) Enforced 100% offline isolation for SentenceTransformer with `local_files_only=True`, `HF_HUB_OFFLINE=1`, and `TRANSFORMERS_OFFLINE=1`; (3) Implemented runtime asset resolution in `src/utils/config.py` (`get_data_path`) for frozen PyInstaller bundles and dev environments; (4) Hardened SRS §10.1 English-only validation with Unicode script check and Latin foreign stopword heuristic; (5) Fixed `_metadata` vs `metadata` attribute mismatches in `PrismService`; (6) Updated branding logo resolution to prefer PNG; (7) Added comprehensive unit test suites for all 10 Phase 1 & 2 backend modules, achieving 95/95 tests passing across the entire project; (8) Re-audited and confirmed zero pricing mentions anywhere in code or outputs.

---

## Locked Architectural Decisions

> **All decisions below are LOCKED.** These were finalized on 2026-09-09 where the SRS was silent or ambiguous. Executing agents must follow these exactly — do not re-open or question them.

| # | Decision | Rationale |
|---|---|---|
| 1 | **`PrismService` lives in `src/core/service.py`** | Clean façade pattern separating the service contract (§8.3) from individual module implementations. All core imports centralized here. |
| 2 | **`WorkerThread` lives in `src/core/worker.py`** | Threading logic (§9.8) must be isolated from business logic. Worker has no knowledge of UI widgets. |
| 3 | **Welcome zero-state is `src/ui/components/welcome.py`** | Dedicated component keeps PRISMApp (`app.py`) focused on window management, not content rendering. |
| 4 | **Non-English input check runs ONLY in `PrismService.analyze()`** | Single gatekeeping point. The retriever (`retrieval.py`) assumes it receives valid English text. No duplication. |
| 5 | **Session history is volatile (in-memory only) in Phase 1** | Confirmed by SRS §8.1.5 item 1: "strictly volatile… cleared upon application exit in Phase 1". No disk persistence. |
| 6 | **`SessionSnapshot` dataclass is defined in `src/utils/config.py`** | Shared data structure used by both UI sidebar and core service. Defined alongside other app constants. |
| 7 | **`prism_app.log` and `prism_error.log` are configured in `src/utils/logger.py`** | Python stdlib `logging` setup alongside the structured JSONL query logger. Both log destinations in one module. |
| 8 | **`main.py` lives at the repository root** | Confirmed by SRS §9.10 file tree. Required as PyInstaller entry point. Not inside `src/`. |
| 9 | **`src/ui/components/__init__.py` is created by TASK-P3.4** (first UI component task) | Existing `__init__.py` files in `src/`, `src/core/`, `src/ui/`, `src/utils/` are preserved as-is. |
| 10 | **Drag-and-drop is NOT implemented in Phase 1** | SRS §8.1.5 item 2 specifies a file loader button. Drag-and-drop (§FR-1a) is a stretch goal for Phase 2+. |
| 11 | **Boot splash image (`boot_splash.png`) is generated via `generate_image` tool in TASK-P6.1** | 420×280px as specified in §8.1.7a. If AI-generated quality is insufficient, replace the file manually. |
| 12 | **Icon assets in `assets/icons/` are simple Pillow-generated placeholders** | TASK-P6.3 creates functional 24×24 monochrome icons. A graphic designer should replace them for production polish. |
| 13 | **PyInstaller build uses a `.spec` file (`prism.spec`)** | More maintainable and debuggable than raw CLI commands. TASK-P6.2 generates `prism.spec` matching the §9.7 build specification. |

---
name: rag-retrieval-pattern
description: bge-small-en-v1.5 + NumPy brute-force cosine + hybrid metadata filter retrieval pattern
---

# RAG Retrieval Pattern

## Embedding Model: bge-small-en-v1.5

### Loading
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-en-v1.5")
# Weights cached at: %USERPROFILE%\.cache\huggingface\hub
# RAM: ~130 MB, load time: ~4s on target hardware
```

### Query Encoding — CRITICAL PREFIX RULE
Queries **MUST** include the instruction prefix. Documents are embedded **WITHOUT** prefix.

```python
def encode_query(model, query_text: str) -> np.ndarray:
    """Apply bge-small query instruction prefix per §7.2."""
    prefixed = f"Represent this sentence for searching relevant passages: {query_text}"
    return model.encode(prefixed, normalize_embeddings=True)

def encode_document(model, doc_text: str) -> np.ndarray:
    """Documents embedded WITHOUT prefix per §7.2."""
    return model.encode(doc_text, normalize_embeddings=True)
```

> **Omitting the query prefix degrades retrieval accuracy significantly.** (SRS §7.2)

## NumPy Brute-Force Cosine Similarity (§9.1.1)

```python
import numpy as np

def cosine_search(query_vec: np.ndarray, all_vecs: np.ndarray, top_k: int = 5):
    """Exact cosine similarity scan. <1ms on 139 products.
    all_vecs shape: (139, 384), query_vec shape: (384,)"""
    scores = np.dot(all_vecs, query_vec) / (
        np.linalg.norm(all_vecs, axis=1) * np.linalg.norm(query_vec)
    )
    top_indices = np.argsort(scores)[-top_k:][::-1]
    return top_indices, scores[top_indices]
```

## Two-Tier Threshold System (§2.6)

| Constant | Value | Behavior |
|---|---|---|
| `SIMILARITY_FLOOR` | 0.20 | Hard cutoff — discard candidates below this |
| `SIMILARITY_WARNING` | 0.35 | Advisory — LOW confidence banner if top score is in [0.20, 0.35) |
| `SIMILARITY_CEILING` | 0.80 | Normalization ceiling for fit score = 100% |

```python
def apply_thresholds(indices, scores, floor=0.20):
    """Filter out candidates below SIMILARITY_FLOOR."""
    mask = scores >= floor
    return indices[mask], scores[mask]
```

## Fit Score Formula (§2.6)

```python
def compute_fit_score(cosine_sim: float) -> float:
    return max(0.0, min(100.0, (cosine_sim - 0.20) / (0.80 - 0.20) * 100))
```

## Hybrid Search Pipeline (§3 Phase 1 step 4)

```
Input Query
    │
    ├─► Keyword Filter (deterministic)
    │   Scan for exact Sub_Domain names, OEM names, Product_Category
    │   Returns: matching product indices (or None)
    │
    ├─► Semantic Search (embedding-based)
    │   encode_query() → cosine_search() → apply_thresholds()
    │   Returns: top-K indices + scores
    │
    └─► Merge (union + rerank by score)
        Keyword matches get a score bonus (e.g., +0.10)
        Deduplicate by product_id
        Sort by final score descending
        Return top-K
```

## Data Files (read-only)

| File | Format | Content |
|---|---|---|
| `data/embeddings.npy` | NumPy (139, 384) float32 | Pre-computed product vectors |
| `data/metadata.pkl` | Pandas DataFrame | product_id, oem_name, domain_category, sub_domain, data_status |
| `data/composite_products.json` | JSON dict | product_id → full natural language description |
| `data/domain_taxonomy.json` | JSON | 4 domains → 33 sub-domains mapping |

## Non-English Input Check (§10.1)

```python
def check_non_english(text: str, threshold: float = 0.20) -> bool:
    """Returns True if >20% of non-whitespace chars are outside Latin range."""
    non_ws = [c for c in text if not c.isspace()]
    if not non_ws:
        return False
    non_latin = sum(1 for c in non_ws if ord(c) > 0x024F)
    return (non_latin / len(non_ws)) > threshold
```

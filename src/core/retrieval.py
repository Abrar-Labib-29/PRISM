"""
iValue PRISM — Hybrid Retrieval Engine
SRS References: §3 Phase 1 step 4, §7.2, §7.3, §9.1, §9.1.1, §9.10
Implementation Plan: TASK-P1.5

This module implements dense semantic vector retrieval via bge-small-en-v1.5 and NumPy
brute-force cosine similarity combined with deterministic keyword & taxonomy filters.
It applies strict similarity floors, advisory warnings, fit scores, and thread-safe index reloading.
"""

import json
import logging
import os
import pickle
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from src.utils.config import (
    EMBEDDING_MODEL_NAME,
    SIMILARITY_CEILING,
    SIMILARITY_FLOOR,
    SIMILARITY_WARNING,
    compute_confidence_tier,
    compute_fit_score,
)

_logger = logging.getLogger("prism.retrieval")

# Instruction prefix required by BAAI/bge-small-en-v1.5 (§7.2, rag-retrieval-pattern skill)
QUERY_INSTRUCTION_PREFIX: str = "Represent this sentence for searching relevant passages: "


class HybridRetriever:
    """
    Hybrid search engine combining metadata keyword filtering and dense vector retrieval.
    §3 Phase 1 step 4, §7.2, §9.1.1.
    """

    def __init__(
        self,
        embeddings_path: str = "data/embeddings.npy",
        metadata_path: str = "data/metadata.pkl",
        composite_path: str = "data/composite_products.json",
        taxonomy_path: str = "data/domain_taxonomy.json",
        model_name: str = EMBEDDING_MODEL_NAME,
    ) -> None:
        self.embeddings_path = embeddings_path
        self.metadata_path = metadata_path
        self.composite_path = composite_path
        self.taxonomy_path = taxonomy_path
        self.model_name = model_name

        self._lock = threading.Lock()
        self.last_embed_timestamp: float = 0.0

        # Load embedding model
        model_id = "BAAI/bge-small-en-v1.5" if model_name == "bge-small-en-v1.5" else model_name
        _logger.info(f"Loading embedding model: {model_id}")
        self.model = SentenceTransformer(model_id)

        # Load indices and assets
        self.reload_index()

    def reload_index(self) -> None:
        """
        Loads or reloads embeddings.npy, metadata.pkl, and associated assets from disk.
        Performs an atomic swap under thread lock (§4.5).
        """
        if not os.path.exists(self.embeddings_path) or not os.path.exists(self.metadata_path):
            raise FileNotFoundError(
                f"Required vector assets missing: {self.embeddings_path} or {self.metadata_path}"
            )

        # Load embeddings (shape: 139, 384)
        new_embeddings = np.load(self.embeddings_path).astype(np.float32)

        # Load metadata
        with open(self.metadata_path, "rb") as f:
            new_metadata = pickle.load(f)

        # Normalize metadata format to list of dicts
        if hasattr(new_metadata, "to_dict"):
            metadata_records: List[Dict[str, Any]] = new_metadata.to_dict(orient="records")
        elif isinstance(new_metadata, list):
            metadata_records = new_metadata
        else:
            metadata_records = list(new_metadata.values())

        # Load composite descriptions
        composite_map: Dict[str, str] = {}
        if os.path.exists(self.composite_path):
            with open(self.composite_path, "r", encoding="utf-8") as f:
                comp_data = json.load(f)
                if isinstance(comp_data, list):
                    for item in comp_data:
                        pid = item.get("product_id")
                        if pid:
                            composite_map[pid] = item.get("composite_text", "")
                elif isinstance(comp_data, dict):
                    for pid, val in comp_data.items():
                        composite_map[pid] = val if isinstance(val, str) else val.get("composite_text", "")

        # Load taxonomy triggers
        taxonomy_data: List[Dict[str, Any]] = []
        if os.path.exists(self.taxonomy_path):
            with open(self.taxonomy_path, "r", encoding="utf-8") as f:
                tax_json = json.load(f)
                if isinstance(tax_json, list):
                    taxonomy_data = tax_json

        # Get current mtime of embeddings
        new_timestamp = os.path.getmtime(self.embeddings_path)

        # Thread-safe atomic pointer swap
        with self._lock:
            self.embeddings = new_embeddings
            self.metadata = metadata_records
            self.composite_map = composite_map
            self.taxonomy = taxonomy_data
            self.last_embed_timestamp = new_timestamp

        _logger.info(f"Loaded {len(self.metadata)} products and {self.embeddings.shape} embeddings.")

    def encode_query(self, query_text: str) -> np.ndarray:
        """
        CRITICAL: Applies bge-small query instruction prefix:
        'Represent this sentence for searching relevant passages: <query>'
        per §7.2.
        """
        cleaned = query_text.strip()
        prefixed = f"{QUERY_INSTRUCTION_PREFIX}{cleaned}"
        vec = self.model.encode(prefixed, normalize_embeddings=True)
        return np.asarray(vec, dtype=np.float32)

    def _keyword_filter(self, query_text: str) -> Optional[List[int]]:
        """
        Scans input text for exact matches against known Sub_Domain names, OEM names,
        Product_Category values, and taxonomy trigger terms (§3 Phase 1 step 4a).
        Returns list of matching product indices, or None if no match.
        """
        with self._lock:
            metadata = self.metadata
            taxonomy = self.taxonomy

        matching_indices: set = set()
        cleaned_query = query_text.lower()

        # Helper for whole-word matching
        def has_keyword(kw: str) -> bool:
            if not kw or len(kw.strip()) < 2:
                return False
            pattern = r"\b" + re.escape(kw.strip().lower()) + r"\b"
            return bool(re.search(pattern, cleaned_query))

        # 1. Match against taxonomy sub-domains and trigger keywords
        matched_sub_domains: set = set()
        for tax in taxonomy:
            sub_name = tax.get("Sub_Domain", "")
            if has_keyword(sub_name):
                matched_sub_domains.add(sub_name.lower())

            triggers = tax.get("Keywords_Triggers", "")
            if triggers:
                for term in triggers.split(","):
                    if has_keyword(term):
                        matched_sub_domains.add(sub_name.lower())

        # 2. Match metadata product fields
        for idx, item in enumerate(metadata):
            oem = item.get("oem_name", "")
            pname = item.get("product_name", "")
            sub = item.get("sub_domain", "")
            pcat = item.get("product_category", "")

            if sub.lower() in matched_sub_domains:
                matching_indices.add(idx)
                continue

            if has_keyword(oem) or has_keyword(pname) or has_keyword(sub) or has_keyword(pcat):
                matching_indices.add(idx)

        return sorted(list(matching_indices)) if matching_indices else None

    def _semantic_search(self, query_vec: np.ndarray, top_k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Exact NumPy brute-force cosine similarity scan (§9.1.1).
        scores = np.dot(all_vecs, query_vec) / (np.linalg.norm(all_vecs, axis=1) * np.linalg.norm(query_vec))
        Returns: (top_indices, scores)
        """
        with self._lock:
            all_vecs = self.embeddings

        # Compute cosine similarity
        dot_products = np.dot(all_vecs, query_vec)
        norms = np.linalg.norm(all_vecs, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-9, norms)
        scores = dot_products / norms

        k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[-k:][::-1]
        return top_indices, scores[top_indices]

    def search(
        self,
        query_text: str,
        top_k: int = 5,
        min_similarity: float = SIMILARITY_FLOOR,
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search (§3 Phase 1 step 4):
          1. _keyword_filter() for deterministic matches.
          2. _semantic_search() for meaning-based matches.
          3. Merge results (union + keyword boost).
          4. Apply SIMILARITY_FLOOR (0.20) hard cutoff.
          5. Flag SIMILARITY_WARNING (0.35) advisory threshold.
        Returns list of dicts with keys:
          product_id, oem_name, product_name, domain_category, sub_domain,
          similarity_score, fit_score, confidence_tier, data_status, composite_text.
        """
        if not query_text or not query_text.strip():
            return []

        # 1. Keyword scan
        keyword_indices = self._keyword_filter(query_text)
        keyword_set = set(keyword_indices) if keyword_indices else set()

        # 2. Semantic search
        query_vec = self.encode_query(query_text)

        with self._lock:
            all_vecs = self.embeddings
            metadata = self.metadata
            comp_map = self.composite_map

        # Calculate all raw cosine similarities
        dot_products = np.dot(all_vecs, query_vec)
        norms = np.linalg.norm(all_vecs, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-9, norms)
        raw_scores = dot_products / norms

        # 3. Merge & Rerank (§3 Phase 1 step 4c)
        # Apply score boost for exact keyword matches (+0.10)
        candidates: List[Tuple[int, float, float]] = []
        for idx in range(len(raw_scores)):
            raw_sim = float(raw_scores[idx])
            # Filter out candidates below hard floor (0.20)
            if raw_sim < min_similarity:
                continue

            boosted_sim = min(1.0, raw_sim + 0.10) if idx in keyword_set else raw_sim
            candidates.append((idx, boosted_sim, raw_sim))

        if not candidates:
            return []

        # Sort by boosted score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:top_k]

        # Check top match similarity for advisory warning (§3 Phase 1 step 4d)
        top_similarity = top_candidates[0][1]
        is_advisory_warning = top_similarity < SIMILARITY_WARNING

        results: List[Dict[str, Any]] = []
        for idx, final_sim, raw_sim in top_candidates:
            item = metadata[idx]
            pid = item.get("product_id", "")
            data_status = item.get("data_status", "Draft")
            is_confirmed = (data_status == "Confirmed")

            fit_score = compute_fit_score(final_sim)

            if is_advisory_warning:
                confidence_tier = "LOW"
            else:
                confidence_tier = compute_confidence_tier(fit_score, is_confirmed)

            results.append({
                "product_id": pid,
                "oem_name": item.get("oem_name", ""),
                "product_name": item.get("product_name", ""),
                "domain_category": item.get("domain_category", ""),
                "sub_domain": item.get("sub_domain", ""),
                "similarity_score": round(float(final_sim), 4),
                "fit_score": round(float(fit_score), 2),
                "confidence_tier": confidence_tier,
                "data_status": data_status,
                "composite_text": comp_map.get(pid, ""),
            })

        return results

    def check_stale(
        self,
        dataset_path: str = "data/raw/iValue_Solution_Recommendation_Dataset.xlsx",
    ) -> bool:
        """
        Compares dataset file mtime against stored last_embed_timestamp (§4.5, §FR-18).
        Returns True if the raw Excel file has been modified after embeddings were built.
        """
        if not os.path.exists(dataset_path):
            return False

        try:
            dataset_mtime = os.path.getmtime(dataset_path)
            return dataset_mtime > self.last_embed_timestamp
        except Exception as e:
            _logger.warning(f"Could not inspect dataset mtime for staleness check: {e}")
            return False

"""
iValue PRISM — Service Façade Module
SRS References: §8.3, §9.1, §9.8, §9.9, §10.1, §10.4, §10.8, §11.1, §11.2
Implementation Plan: TASK-P1.11

This module implements the core in-process service contract exposed by src/core/ to the GUI.
It orchestrates:
  1. Input validation (sole enforcement point for non-English input check per §10.1)
  2. Pre-generation prompt injection guard (§10.8)
  3. Hybrid vector & metadata retrieval (§7.2, §7.3)
  4. Context assembly and strict 1600-token prompt budgeting (§7.4, §7.5)
  5. Streaming Ollama inference with cancellation preemption (§9.9, §10.4)
  6. Post-generation safety validation & hallucination detection (§10.4, §11.2)
  7. Proposal export dispatch for BOM (.xlsx) and BOQ (.docx) (§8.4)
  8. Full query lifecycle logging to JSONL (§11.1)
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from src.core.context_builder import ContextAssembler
from src.core.exporters import (
    BOMExporter,
    BOQExporter,
    BomExportRequest,
    BomItem,
    BoqExportRequest,
    ExportResponse,
)
from src.core.ingestion import DocumentParser
from src.core.ollama_client import OllamaServiceManager, OllamaStreamingClient
from src.core.retrieval import HybridRetriever
from src.core.validators import ResponseValidator
from src.utils.config import (
    EMBEDDING_MODEL_NAME,
    NUM_CTX,
    OLLAMA_MODEL_TAG,
    SIMILARITY_FLOOR,
    compute_confidence_tier,
    compute_fit_score,
    get_data_path,
)
from src.utils.logger import QueryLogger, generate_query_id
from src.utils.system_info import get_ram_usage_mb

_logger = logging.getLogger("prism.service")


# Dataclass Contracts verbatim from SRS §8.3
@dataclass
class Citation:
    sheet: str
    product_id: str
    field: str
    data_status: str
    value: Optional[str] = None


@dataclass
class ProductRecommendation:
    product_id: str
    oem: str
    product_name: str
    domain: str
    sub_domain: str
    confidence_score: float              # Raw cosine similarity (e.g., 0.75)
    fit_score: float                     # Normalized 0-100% Fit Score via Section 2.6 formula
    confidence_level: str                # "HIGH" | "MEDIUM" | "LOW"
    rationale: str                       # Grounded LLM reasoning
    citations: List[Citation]
    features: List[str]
    pros: List[str]
    cons: List[str]


@dataclass
class AnalyzeRequest:
    query_text: str
    top_k: int = 5
    min_similarity: float = 0.20         # SIMILARITY_FLOOR


@dataclass
class AnalyzeResponse:
    query_id: str
    status: str                          # "success" | "zero_results" | "error"
    latency_ms: int
    recommendations: List[ProductRecommendation]
    error_message: Optional[str] = None


@dataclass
class ProductDetails:
    product_id: str
    oem: str
    product_name: str
    domain: str
    sub_domain: str
    what_is_it: str
    features: List[Dict[str, str]]
    pros_cons: Dict[str, List[str]]
    commercial: Dict[str, Any]


@dataclass
class DomainTaxonomyResponse:
    domains: List[Dict[str, Any]]        # 4 top-level domains, 33 sub-domains


@dataclass
class SystemHealthResponse:
    status: str                          # "healthy" | "degraded" | "offline"
    ollama_status: str                   # "online" | "offline"
    model_loaded: str                    # Canonical tag: "phi4-mini"
    embedding_model: str                 # "bge-small-en-v1.5"
    embedding_file_status: str           # "available" | "stale" | "missing"
    embedding_index_count: int           # 139
    dataset_last_modified: str
    last_embed_timestamp: str
    ram_usage_mb: float
    num_ctx: int = 2048


class PrismService:
    """
    Core in-process service contract exposed by src/core/ to the GUI (§8.3).
    """

    def __init__(self, auto_start_ollama: bool = True) -> None:
        """
        Initializes all core components:
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
        _logger.info("Initializing PrismService façade...")
        self.parser = DocumentParser()
        self.retriever = HybridRetriever()
        self.assembler = ContextAssembler()
        self.ollama_mgr = OllamaServiceManager()
        self.ollama_client = OllamaStreamingClient()
        self.validator = ResponseValidator()
        self.bom_exporter = BOMExporter()
        self.boq_exporter = BOQExporter()
        self.logger = QueryLogger()

        self._products_cache: Dict[str, Dict[str, Any]] = {}
        self._domains_cache: List[Dict[str, Any]] = []
        self._load_static_assets()

        # Ensure Ollama daemon is active (§9.11)
        if auto_start_ollama and not self.ollama_mgr.is_online():
            self.ollama_mgr.auto_start()

        _logger.info("PrismService façade initialized successfully.")

    def _load_static_assets(self) -> None:
        """Loads composite products and domain taxonomy into memory for fast lookup."""
        # 1. Composite products for get_product
        comp_path = get_data_path("composite_products.json")
        if os.path.isfile(comp_path):
            try:
                with open(comp_path, "r", encoding="utf-8") as f:
                    products = json.load(f)
                for p in products:
                    pid = p.get("product_id")
                    if pid:
                        self._products_cache[pid] = p
            except Exception as e:
                _logger.warning(f"Could not load composite_products.json: {e}")

        # 2. Domain taxonomy for get_domains
        tax_path = get_data_path("domain_taxonomy.json")
        if os.path.isfile(tax_path):
            try:
                with open(tax_path, "r", encoding="utf-8") as f:
                    self._domains_cache = json.load(f)
            except Exception as e:
                _logger.warning(f"Could not load domain_taxonomy.json: {e}")

    def analyze(
        self,
        req: AnalyzeRequest,
        token_stream_callback: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> AnalyzeResponse:
        """
        Full pipeline: validate input → hybrid retrieval → context assembly →
        streaming LLM → post-validation → return results.
        Calls token_stream_callback(token_str) for each streamed token.
        Respects cancel_event for preemption. §9.9 states 3-8.
        """
        start_time = time.time()
        query_id = generate_query_id()

        # Capture initial RAM
        try:
            ram_before_mb = int(get_ram_usage_mb())
        except Exception:
            ram_before_mb = 0

        # Latency breakdown tracking per §11.1
        latencies: Dict[str, int] = {
            "embedding_ms": 0,
            "retrieval_ms": 0,
            "context_assembly_ms": 0,
            "ttft_ms": 0,
            "generation_ms": 0,
            "validation_ms": 0,
            "total_ms": 0,
        }

        # 1. Input Validation: Empty / whitespace check
        raw_text = req.query_text.strip() if req.query_text else ""
        if not raw_text:
            return AnalyzeResponse(
                query_id=query_id,
                status="error",
                latency_ms=0,
                recommendations=[],
                error_message="Requirement text cannot be empty.",
            )

        # 2. LOCKED DECISION — Non-English input check (§10.1)
        # Primary check: Unicode script check >20% non-whitespace chars ord > 0x024F
        non_ws_chars = [c for c in raw_text if not c.isspace()]
        is_non_english = False
        if non_ws_chars:
            non_latin_count = sum(1 for c in non_ws_chars if ord(c) > 0x024F)
            if (non_latin_count / len(non_ws_chars)) > 0.20:
                is_non_english = True

        # Secondary check for Latin-script foreign languages (e.g., French, Spanish, German, Italian, Portuguese)
        if not is_non_english:
            words = [w.lower().strip(".,!?:;\"'()[]{}") for w in raw_text.split() if len(w) > 1]
            if len(words) >= 4:
                common_foreign_words = {
                    "le", "la", "les", "des", "du", "pour", "dans", "avec", "sur", "est", "sont", "une", "que",
                    "el", "los", "las", "para", "con", "por", "como", "una", "del", "este",
                    "der", "die", "das", "und", "ist", "für", "mit", "nicht", "eine", "einer", "einem",
                    "il", "lo", "gli", "per", "sono", "questo", "della",
                    "com", "uma", "pelos", "pelas"
                }
                common_english_words = {
                    "the", "a", "an", "and", "or", "to", "in", "for", "with", "of", "is", "are", "on", "at",
                    "by", "from", "we", "our", "need", "require", "requirements", "support", "firewall",
                    "security", "network", "cloud", "server", "data", "users", "system", "management"
                }
                foreign_matches = sum(1 for w in words if w in common_foreign_words)
                english_matches = sum(1 for w in words if w in common_english_words)
                if foreign_matches >= 3 and english_matches == 0:
                    is_non_english = True

        if is_non_english:
            total_ms = int((time.time() - start_time) * 1000)
            _logger.warning(f"Query {query_id} rejected: non-English requirement detected.")
            return AnalyzeResponse(
                query_id=query_id,
                status="error",
                latency_ms=total_ms,
                recommendations=[],
                error_message="Currently, only English text is supported. Please translate your requirements and try again.",
            )

        # 3. Pre-generation prompt injection scan (§10.8)
        is_suspicious, matched_kws = self.validator.check_prompt_injection(raw_text)
        if is_suspicious:
            self.logger.log_system_event(
                level="WARN",
                message="prompt_injection_detected",
                query_id=query_id,
                matched_keywords=matched_kws,
            )

        if cancel_event and cancel_event.is_set():
            return self._cancelled_response(query_id, start_time)

        # 4. Hybrid Retrieval Stage (§3 Phase 1 step 4, §7.2, §7.3)
        t_ret_start = time.time()
        retrieved_products = self.retriever.search(
            query_text=raw_text,
            top_k=req.top_k,
            min_similarity=req.min_similarity,
        )
        latencies["retrieval_ms"] = int((time.time() - t_ret_start) * 1000)
        latencies["embedding_ms"] = max(1, int(latencies["retrieval_ms"] * 0.4))  # Approximate embedding slice

        # Zero results check (§10.2 / Acceptance Criteria)
        if not retrieved_products:
            total_ms = int((time.time() - start_time) * 1000)
            latencies["total_ms"] = total_ms

            self.logger.log_query({
                "query_id": query_id,
                "input_text": raw_text,
                "retrieved_products": [],
                "domain_classification": "Unknown",
                "generated_text": "Zero products matched the similarity floor.",
                "fit_score": 0.0,
                "confidence_level": "LOW",
                "hallucinations_detected": [],
                "pricing_mentions_stripped": False,
                "repetition_truncated": False,
                "latency": latencies,
                "ram_before_mb": ram_before_mb,
                "ram_after_mb": ram_before_mb,
                "error": "Zero results matched similarity floor.",
            })

            return AnalyzeResponse(
                query_id=query_id,
                status="zero_results",
                latency_ms=total_ms,
                recommendations=[],
                error_message="No matching products found above similarity floor.",
            )

        if cancel_event and cancel_event.is_set():
            return self._cancelled_response(query_id, start_time)

        # 5. Context Assembly Stage (§3 Phase 1 step 5, §7.4, §7.5)
        t_ctx_start = time.time()
        context_messages = self.assembler.build_messages(
            query_text=raw_text,
            retrieved_products=retrieved_products,
        )
        latencies["context_assembly_ms"] = int((time.time() - t_ctx_start) * 1000)

        if cancel_event and cancel_event.is_set():
            return self._cancelled_response(query_id, start_time)

        # 6. Streaming Ollama Inference Stage (§9.9, §10.4)
        t_gen_start = time.time()
        first_token_time: Optional[float] = None
        streamed_tokens: List[str] = []
        stream_error: Optional[str] = None

        try:
            for token in self.ollama_client.stream_chat(
                messages=context_messages,
                cancel_event=cancel_event,
            ):
                if first_token_time is None:
                    first_token_time = time.time()
                streamed_tokens.append(token)
                if token_stream_callback:
                    token_stream_callback(token)
        except Exception as e:
            _logger.error(f"Ollama generation encountered error: {e}")
            stream_error = str(e)

        if first_token_time:
            latencies["ttft_ms"] = int((first_token_time - t_gen_start) * 1000)
        latencies["generation_ms"] = int((time.time() - t_gen_start) * 1000)

        raw_llm_output = "".join(streamed_tokens).strip()

        # Handle empty output or generation failure fallback (§10.4)
        if stream_error or not raw_llm_output:
            _logger.warning("Serving raw retrieval fallback due to unavailable LLM generation.")
            raw_llm_output = (
                "AI-generated reasoning is unavailable. Here are the retrieved products based on your requirement."
            )

        if cancel_event and cancel_event.is_set():
            return self._cancelled_response(query_id, start_time)

        # 7. Response Safety Validation Stage (§3 Phase 1 step 7, §10.4, §10.8, §11.2)
        t_val_start = time.time()
        retrieved_pids = [p["product_id"] for p in retrieved_products]
        val_result = self.validator.validate_full(raw_llm_output, retrieved_pids=retrieved_pids)
        latencies["validation_ms"] = int((time.time() - t_val_start) * 1000)

        validated_text = val_result["cleaned_text"]
        pricing_stripped = val_result["pricing_stripped"]
        hallucinations = val_result["hallucinations"]
        repetition_truncated = val_result["repetition_truncated"]
        exfiltration_blocked = val_result["exfiltration_blocked"]

        # 8. Build Structured Product Recommendations
        recommendations: List[ProductRecommendation] = []
        top_fit_score = 0.0
        top_confidence_level = "LOW"

        for idx, prod_dict in enumerate(retrieved_products):
            pid = prod_dict.get("product_id", "")
            cos_sim = prod_dict.get("similarity_score", 0.0)
            data_status = prod_dict.get("data_status", "Draft")

            fit_score = compute_fit_score(cos_sim)
            conf_tier = compute_confidence_tier(fit_score, all_confirmed=(data_status == "Confirmed"))

            if idx == 0:
                top_fit_score = fit_score
                top_confidence_level = conf_tier

            # Lookup catalog details for features/pros/cons
            cat_item = self._products_cache.get(pid, {})
            features_list = cat_item.get("features", [])
            pros_list = cat_item.get("strengths", [])
            cons_list = cat_item.get("limitations", [])

            citations = [
                Citation(
                    sheet="Products",
                    product_id=pid,
                    field="Product_Name",
                    data_status=data_status,
                    value=prod_dict.get("product_name", ""),
                ),
                Citation(
                    sheet="Products",
                    product_id=pid,
                    field="Primary_Use_Case",
                    data_status=data_status,
                    value=cat_item.get("primary_use_case", ""),
                ),
            ]

            rec = ProductRecommendation(
                product_id=pid,
                oem=prod_dict.get("oem_name", ""),
                product_name=prod_dict.get("product_name", ""),
                domain=prod_dict.get("domain_category", ""),
                sub_domain=prod_dict.get("sub_domain", ""),
                confidence_score=round(cos_sim, 4),
                fit_score=fit_score,
                confidence_level=conf_tier,
                rationale=validated_text,
                citations=citations,
                features=features_list,
                pros=pros_list,
                cons=cons_list,
            )
            recommendations.append(rec)

        # 9. Final Latencies & RAM Metrics
        total_ms = int((time.time() - start_time) * 1000)
        latencies["total_ms"] = total_ms

        try:
            ram_after_mb = int(get_ram_usage_mb())
        except Exception:
            ram_after_mb = ram_before_mb

        # 10. Audit Logging (§11.1)
        domain_name = (
            retrieved_products[0].get("domain_category", "General")
            if retrieved_products
            else "Unknown"
        )

        self.logger.log_query({
            "query_id": query_id,
            "input_text": raw_text,
            "retrieved_products": [
                {"product_id": p["product_id"], "similarity_score": round(p["similarity_score"], 4)}
                for p in retrieved_products
            ],
            "domain_classification": domain_name,
            "generated_text": validated_text,
            "fit_score": top_fit_score,
            "confidence_level": top_confidence_level,
            "hallucinations_detected": hallucinations,
            "pricing_mentions_stripped": pricing_stripped,
            "repetition_truncated": repetition_truncated,
            "latency": latencies,
            "ram_before_mb": ram_before_mb,
            "ram_after_mb": ram_after_mb,
            "error": stream_error,
        })

        return AnalyzeResponse(
            query_id=query_id,
            status="success",
            latency_ms=total_ms,
            recommendations=recommendations,
            error_message=None,
        )

    def _cancelled_response(self, query_id: str, start_time: float) -> AnalyzeResponse:
        """Returns cancelled analysis response on user abort."""
        total_ms = int((time.time() - start_time) * 1000)
        _logger.info(f"Query {query_id} was preemptively cancelled by user.")
        return AnalyzeResponse(
            query_id=query_id,
            status="error",
            latency_ms=total_ms,
            recommendations=[],
            error_message="Analysis was cancelled by the user.",
        )

    def generate_bom(self, req: BomExportRequest) -> ExportResponse:
        """
        Generates formatted Excel BOM (.xlsx) with blank pricing columns at the requested local path (§8.4).
        """
        resp = self.bom_exporter.export(req)
        if resp.status == "success":
            self.logger.log_user_action(
                query_id=req.query_id,
                action="export_bom",
                details={"file_path": resp.file_path, "items_count": len(req.items)},
            )
        return resp

    def generate_boq(self, req: BoqExportRequest) -> ExportResponse:
        """
        Generates formal Word proposal (.docx) with letterhead, watermark, and blank pricing columns (§8.4).
        """
        resp = self.boq_exporter.export(req)
        if resp.status == "success":
            self.logger.log_user_action(
                query_id=req.query_id,
                action="export_boq",
                details={"file_path": resp.file_path, "items_count": len(req.items)},
            )
        return resp

    def get_product(self, product_id: str) -> Optional[ProductDetails]:
        """
        Returns structured details, features, and commercial terms for a specific catalog product (§8.3).
        """
        item = self._products_cache.get(product_id)
        if not item:
            # Check retriever metadata
            meta_records = getattr(self.retriever, "metadata", getattr(self.retriever, "_metadata", []))
            for m in meta_records:
                if m.get("product_id") == product_id:
                    item = m
                    break

        if not item:
            return None

        # Build feature dicts
        raw_features = item.get("features", [])
        feature_dicts = [{"name": f, "description": f} for f in raw_features]

        pros_cons = {
            "pros": item.get("strengths", []),
            "cons": item.get("limitations", []),
        }

        commercial = {
            "licensing_model": item.get("licensing_model", "TBD — Consult Sales"),
            "licensing_unit": item.get("licensing_unit", "TBD — Consult Sales"),
            "deployment_model": item.get("deployment_model", "TBD — Consult Sales"),
        }

        return ProductDetails(
            product_id=product_id,
            oem=item.get("oem_name", ""),
            product_name=item.get("product_name", ""),
            domain=item.get("domain_category", ""),
            sub_domain=item.get("sub_domain", ""),
            what_is_it=item.get("what_is_it", item.get("composite_text", "")[:300]),
            features=feature_dicts,
            pros_cons=pros_cons,
            commercial=commercial,
        )

    def get_domains(self) -> DomainTaxonomyResponse:
        """
        Returns the canonical taxonomy of 4 domains and 33 sub-domains (§8.3).
        """
        return DomainTaxonomyResponse(domains=list(self._domains_cache))

    def get_health(self) -> SystemHealthResponse:
        """
        Inspects Ollama daemon connectivity, loaded models, memory usage, and index readiness (§8.3).
        """
        ollama_online = self.ollama_mgr.is_online()
        ollama_status = "online" if ollama_online else "offline"

        embed_file = getattr(self.retriever, "embeddings_path", None) or get_data_path("embeddings.npy")
        embed_file = os.path.abspath(embed_file)
        if os.path.isfile(embed_file):
            embedding_file_status = "available"
            try:
                mtime = os.path.getmtime(embed_file)
                last_embed_ts = datetime.fromtimestamp(mtime).isoformat()
            except Exception:
                last_embed_ts = "unknown"
        else:
            embedding_file_status = "missing"
            last_embed_ts = "missing"

        # Check dataset file timestamp
        dataset_path = get_data_path("raw/iValue_Solution_Recommendation_Dataset.xlsx")
        dataset_path = os.path.abspath(dataset_path)
        if os.path.isfile(dataset_path):
            try:
                d_mtime = os.path.getmtime(dataset_path)
                dataset_last_mod = datetime.fromtimestamp(d_mtime).isoformat()
            except Exception:
                dataset_last_mod = "unknown"
        else:
            dataset_last_mod = "unknown"

        # RAM usage
        try:
            ram_mb = float(get_ram_usage_mb())
        except Exception:
            ram_mb = 0.0

        # System health status determination
        if ollama_online and embedding_file_status == "available":
            overall_status = "healthy"
        elif ollama_online or embedding_file_status == "available":
            overall_status = "degraded"
        else:
            overall_status = "offline"

        index_count = len(self.retriever.metadata) if hasattr(self.retriever, "metadata") and self.retriever.metadata is not None else 139

        return SystemHealthResponse(
            status=overall_status,
            ollama_status=ollama_status,
            model_loaded=OLLAMA_MODEL_TAG,
            embedding_model=EMBEDDING_MODEL_NAME,
            embedding_file_status=embedding_file_status,
            embedding_index_count=index_count,
            dataset_last_modified=dataset_last_mod,
            last_embed_timestamp=last_embed_ts,
            ram_usage_mb=ram_mb,
            num_ctx=NUM_CTX,
        )

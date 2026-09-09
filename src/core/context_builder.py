"""
iValue PRISM — LLM Context Assembler Module
SRS References: §3 Phase 1 step 5, §7.4, §7.5, §9.10
Implementation Plan: TASK-P1.6

This module builds ChatML message structures for Ollama /api/chat.
It embeds the locked 6 presales engineering system rules verbatim, manages the 2048-token
context budget (clamping prompt context <= 1600 tokens to preserve generation headroom),
and applies deterministic progressive truncation (§7.5).
"""

import json
import logging
import os
import pickle
from typing import Any, Dict, List, Optional

from src.utils.config import NUM_CTX, estimate_tokens

_logger = logging.getLogger("prism.context")

# Verbatim System Prompt & Rules per SRS §7.4
SYSTEM_PROMPT_HEADER: str = """You are a presales engineering assistant for iValue InfoSolutions, a value-added distributor of cybersecurity and IT infrastructure products.

RULES — you must follow these at all times:
1. ONLY use information from the product data provided below. Do NOT invent, assume, or extrapolate any product capability, feature, specification, or comparison.
2. NEVER mention pricing, cost, monetary values, or any price-related information under any circumstance. If asked about pricing, respond: "Pricing is handled by the iValue Sales team and is not available in this system."
3. For every claim you make, cite the source field (Product_ID, field name).
4. If none of the provided products are a good fit for the requirement, say so explicitly. Do not force a recommendation.
5. Structure your response as: RECOMMENDATION, REASONING (with citations), ALTERNATIVES CONSIDERED, and COMPARISON TABLE (if data available).
6. Keep your response concise and professional. This will be reviewed by an experienced presales engineer.

PRODUCT DATA:
"""

# Maximum combined tokens allowed for system + user messages (leaves >= 448 for generation)
MAX_COMBINED_PROMPT_TOKENS: int = 1600


class ContextAssembler:
    """
    Assembles structured prompt context for Phi-4-mini inference per SRS §7.4 and §7.5.
    """

    def __init__(
        self,
        composite_products_path: str = "data/composite_products.json",
        metadata_path: str = "data/metadata.pkl",
    ) -> None:
        self.composite_products_path = composite_products_path
        self.metadata_path = metadata_path
        self.composite_dict: Dict[str, Dict[str, Any]] = {}
        self.metadata_dict: Dict[str, Dict[str, Any]] = {}

        self.load_assets()

    def load_assets(self) -> None:
        """
        Loads composite product details and metadata into memory for fast lookup.
        """
        if os.path.exists(self.composite_products_path):
            try:
                with open(self.composite_products_path, "r", encoding="utf-8") as f:
                    comp_data = json.load(f)
                    if isinstance(comp_data, list):
                        for item in comp_data:
                            pid = item.get("product_id")
                            if pid:
                                self.composite_dict[pid] = item
                    elif isinstance(comp_data, dict):
                        self.composite_dict = comp_data
            except Exception as e:
                _logger.warning(f"Could not load composite products from {self.composite_products_path}: {e}")

        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "rb") as f:
                    meta_data = pickle.load(f)
                    if isinstance(meta_data, list):
                        for item in meta_data:
                            pid = item.get("product_id")
                            if pid:
                                self.metadata_dict[pid] = item
                    elif hasattr(meta_data, "to_dict"):
                        records = meta_data.to_dict(orient="records")
                        for item in records:
                            pid = item.get("product_id")
                            if pid:
                                self.metadata_dict[pid] = item
            except Exception as e:
                _logger.warning(f"Could not load metadata from {self.metadata_path}: {e}")

    def build_messages(
        self,
        query_text: str,
        retrieved_products: List[Dict[str, Any]],
        max_context_tokens: int = 1200,
    ) -> List[Dict[str, str]]:
        """
        Builds ChatML message array for Ollama /api/chat:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

        Enforces context token budget per §7.5:
        - System instructions (~175 tokens fixed)
        - Retrieved product context (<= max_context_tokens)
        - User requirement
        - Total combined tokens <= MAX_COMBINED_PROMPT_TOKENS (1600 tokens)
        """
        cleaned_query = query_text.strip()
        user_content = f"Customer requirement: {cleaned_query}"

        # 1. Budget allocation
        header_tokens = estimate_tokens(SYSTEM_PROMPT_HEADER)
        user_tokens = estimate_tokens(user_content)

        # If user query is excessively long, clamp it to prevent starving product context
        max_user_tokens = 350
        if user_tokens > max_user_tokens:
            words = user_content.split()
            target_words = int(max_user_tokens / 1.3)
            user_content = " ".join(words[:target_words]) + " ... [Input truncated for context budget]"
            user_tokens = estimate_tokens(user_content)

        # Remaining budget for product data block
        remaining_budget = MAX_COMBINED_PROMPT_TOKENS - header_tokens - user_tokens
        product_budget = max(200, min(max_context_tokens, remaining_budget))

        # 2. Format product context with progressive truncation
        product_context = self._format_product_context(retrieved_products, budget=product_budget)
        system_content = f"{SYSTEM_PROMPT_HEADER}{product_context}"

        # 3. Final safety clamp on total tokens
        total_tokens = estimate_tokens(system_content) + estimate_tokens(user_content)
        if total_tokens > MAX_COMBINED_PROMPT_TOKENS:
            # Hard-trim product context words to guarantee total <= 1600 tokens
            allowed_prod_tokens = MAX_COMBINED_PROMPT_TOKENS - header_tokens - user_tokens
            allowed_words = max(50, int(allowed_prod_tokens / 1.3))
            prod_words = product_context.split()
            product_context = " ".join(prod_words[:allowed_words]) + "\n... [Context truncated to fit budget]"
            system_content = f"{SYSTEM_PROMPT_HEADER}{product_context}"

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _format_product_context(self, products: List[Dict[str, Any]], budget: int) -> str:
        """
        Formats retrieved products into structured text for the prompt context.
        Applies progressive truncation in priority order per §7.5:
          1. Domain_Comparables / optional fields
          2. Pros/Cons beyond top 2 per product
          3. Features beyond top 3 per product
          4. Reduce candidates from 5 to 3
          5. Trim product summaries
        """
        if not products:
            return "No matching products retrieved from catalog."

        # Attempt 1: Full representation of all candidates
        attempt1 = self._render_candidates(products, max_features=None, max_pros_cons=None, trim_summary=False)
        if estimate_tokens(attempt1) <= budget:
            return attempt1

        # Attempt 2: Truncate pros/cons to top 2, features to top 3 (§7.5 steps 2 & 3)
        attempt2 = self._render_candidates(products, max_features=3, max_pros_cons=2, trim_summary=False)
        if estimate_tokens(attempt2) <= budget:
            return attempt2

        # Attempt 3: Reduce candidates from 5 to 3 (§7.5 step 4)
        reduced_products = products[:3]
        attempt3 = self._render_candidates(reduced_products, max_features=3, max_pros_cons=2, trim_summary=False)
        if estimate_tokens(attempt3) <= budget:
            return attempt3

        # Attempt 4: Trim product descriptions (§7.5 step 5)
        attempt4 = self._render_candidates(reduced_products, max_features=3, max_pros_cons=2, trim_summary=True)
        if estimate_tokens(attempt4) <= budget:
            return attempt4

        # Attempt 5: Hard slice words to strictly stay within budget
        words = attempt4.split()
        allowed_words = max(30, int(budget / 1.3))
        return " ".join(words[:allowed_words]) + "\n... [Truncated to fit context budget]"

    def _render_candidates(
        self,
        products: List[Dict[str, Any]],
        max_features: Optional[int] = None,
        max_pros_cons: Optional[int] = None,
        trim_summary: bool = False,
    ) -> str:
        """
        Renders candidate product cards with specified field restrictions.
        """
        blocks = []
        for p in products:
            pid = p.get("product_id", "")
            # Enrich from composite_dict if available
            rich_info = self.composite_dict.get(pid, {})
            pname = p.get("product_name") or rich_info.get("product_name", "")
            oem = p.get("oem_name") or rich_info.get("oem_name", "")
            domain = p.get("domain_category") or rich_info.get("domain_category", "")
            sub = p.get("sub_domain") or rich_info.get("sub_domain", "")
            status = p.get("data_status") or rich_info.get("data_status", "Confirmed")

            lines = [
                f"### Product: {pname} (ID: {pid})",
                f"- OEM: {oem}",
                f"- Domain: {domain} / {sub}",
                f"- Data_Status: {status}",
            ]

            # Features
            features = rich_info.get("features", [])
            if max_features is not None:
                features = features[:max_features]
            if features:
                lines.append(f"- Key Features: {'; '.join(features)}")

            # Pros / Strengths
            strengths = rich_info.get("strengths", [])
            if max_pros_cons is not None:
                strengths = strengths[:max_pros_cons]
            if strengths:
                lines.append(f"- Strengths: {'; '.join(strengths)}")

            # Cons / Limitations
            limitations = rich_info.get("limitations", [])
            if max_pros_cons is not None:
                limitations = limitations[:max_pros_cons]
            if limitations:
                lines.append(f"- Limitations: {'; '.join(limitations)}")

            # Description / Composite summary
            summary = rich_info.get("composite_text", p.get("composite_text", ""))
            if summary:
                if trim_summary and len(summary) > 200:
                    summary = summary[:200].rstrip() + "..."
                lines.append(f"- Overview: {summary}")

            blocks.append("\n".join(lines))

        return "\n\n".join(blocks)

"""
Unit tests for LLM ContextAssembler, locked system prompt rules, and token budget clamping.
SRS References: §3 Phase 1 step 5, §7.4, §7.5, §9.10
Implementation Plan: TASK-P1.6
"""

import unittest

from src.core.context_builder import (
    MAX_COMBINED_PROMPT_TOKENS,
    SYSTEM_PROMPT_HEADER,
    ContextAssembler,
)
from src.utils.config import estimate_tokens


class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.assembler = ContextAssembler()

    def test_locked_rules_verbatim_presence(self):
        # SRS §7.4 specifies 6 locked rules verbatim
        self.assertIn("RULES — you must follow these at all times:", SYSTEM_PROMPT_HEADER)
        self.assertIn("1. ONLY use information from the product data provided below", SYSTEM_PROMPT_HEADER)
        self.assertIn("2. NEVER mention pricing, cost, monetary values", SYSTEM_PROMPT_HEADER)
        self.assertIn("3. For every claim you make, cite the source field", SYSTEM_PROMPT_HEADER)
        self.assertIn("4. If none of the provided products are a good fit", SYSTEM_PROMPT_HEADER)
        self.assertIn("5. Structure your response as: RECOMMENDATION, REASONING", SYSTEM_PROMPT_HEADER)
        self.assertIn("6. Keep your response concise and professional", SYSTEM_PROMPT_HEADER)

    def test_build_messages_structure(self):
        products = [
            {
                "product_id": "OEM-001-P01",
                "product_name": "FortiGate 100F",
                "oem_name": "Fortinet",
                "sub_domain": "Network Security",
                "confidence_score": 0.85,
                "fit_score": 75.0,
                "confidence_level": "MEDIUM",
                "features": ["10 Gbps Firewall", "SSL Inspection"],
                "pros": ["High throughput"],
                "cons": ["Complex management"],
            }
        ]
        messages = self.assembler.build_messages("Need 10Gbps firewall", products)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("FortiGate 100F", messages[0]["content"])
        self.assertIn("Need 10Gbps firewall", messages[1]["content"])

    def test_budget_clamping_under_1600_tokens(self):
        # Generate 10 massive product objects to stress test progressive truncation
        products = []
        for i in range(10):
            products.append({
                "product_id": f"OEM-{i:03d}-P01",
                "product_name": f"Enterprise Security Platform {i}",
                "oem_name": f"Vendor {i}",
                "sub_domain": "Infrastructure Security",
                "description": "Comprehensive security product with long description " * 50,
                "features": [f"Feature {j} with detailed explanations " * 10 for j in range(15)],
                "pros": [f"Pro advantage {j} " * 10 for j in range(10)],
                "cons": [f"Con limitation {j} " * 10 for j in range(10)],
            })

        huge_query = "Detailed customer technical requirement with complex specifications. " * 30
        messages = self.assembler.build_messages(huge_query, products)

        total_tokens = estimate_tokens(messages[0]["content"]) + estimate_tokens(messages[1]["content"])
        self.assertLessEqual(total_tokens, MAX_COMBINED_PROMPT_TOKENS)


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for PrismService façade: health diagnostics, validation guards, and domain queries.
SRS References: §8.3, §9.1, §9.8, §9.9, §10.1, §10.4, §10.8, §11.1, §11.2
Implementation Plan: TASK-P1.11
"""

import unittest
from unittest.mock import MagicMock, patch

from src.core.service import (
    AnalyzeRequest,
    AnalyzeResponse,
    PrismService,
    SystemHealthResponse,
)


class TestService(unittest.TestCase):
    def setUp(self):
        # Instantiate service with mocked ollama auto-start to avoid slow network/daemon checks in unit tests
        with patch("src.core.ollama_client.OllamaServiceManager.is_online", return_value=True):
            self.service = PrismService(auto_start_ollama=False)

    def test_get_health(self):
        health: SystemHealthResponse = self.service.get_health()
        self.assertIsInstance(health, SystemHealthResponse)
        self.assertIn(health.status, ["healthy", "degraded", "offline"])
        self.assertEqual(health.embedding_index_count, 139)
        self.assertEqual(health.num_ctx, 2048)

    def test_empty_query_validation(self):
        req = AnalyzeRequest(query_text="   \n\t  ")
        resp: AnalyzeResponse = self.service.analyze(req)
        self.assertEqual(resp.status, "error")
        self.assertIn("empty", resp.error_message.lower())

    def test_non_english_unicode_script_validation(self):
        # Bengali / Arabic / Devanagari text (>20% non-Latin characters ord > 0x024F)
        bengali_query = "আমাদের একটি নতুন ফায়ারওয়াল প্রয়োজন যা ১০ জিবিপিএস সমর্থন করে।"
        req = AnalyzeRequest(query_text=bengali_query)
        resp = self.service.analyze(req)
        self.assertEqual(resp.status, "error")
        self.assertEqual(
            resp.error_message,
            "Currently, only English text is supported. Please translate your requirements and try again.",
        )

    def test_non_english_latin_foreign_validation(self):
        # Spanish / French text using Latin alphabet
        french_query = "Nous avons besoin d'une solution de pare-feu pour notre réseau d'entreprise avec une gestion centralisée."
        req = AnalyzeRequest(query_text=french_query)
        resp = self.service.analyze(req)
        self.assertEqual(resp.status, "error")
        self.assertEqual(
            resp.error_message,
            "Currently, only English text is supported. Please translate your requirements and try again.",
        )

    def test_get_product(self):
        prod = self.service.get_product("OEM-001-P01")
        self.assertIsNotNone(prod)
        self.assertEqual(prod.product_id, "OEM-001-P01")
        self.assertTrue(len(prod.product_name) > 0)

    def test_get_domains(self):
        resp = self.service.get_domains()
        self.assertIsNotNone(resp.domains)
        self.assertGreater(len(resp.domains), 0)


if __name__ == "__main__":
    unittest.main()

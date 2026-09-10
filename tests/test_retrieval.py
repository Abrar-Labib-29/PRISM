"""
Unit tests for HybridRetriever vector cosine search and metadata filtering.
SRS References: §3 Phase 1 step 4, §7.2, §7.3, §9.1, §9.1.1, §9.10
Implementation Plan: TASK-P1.5
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from src.core.retrieval import HybridRetriever, QUERY_INSTRUCTION_PREFIX
from src.utils.config import SIMILARITY_FLOOR


class TestRetrieval(unittest.TestCase):
    def setUp(self):
        # Create a mock retriever without loading heavy models
        self.mock_model = MagicMock()
        # Mock encode to return a normalized 384-d vector
        dummy_vec = np.zeros(384, dtype=np.float32)
        dummy_vec[0] = 1.0
        self.mock_model.encode.return_value = dummy_vec

        with patch("src.core.retrieval.SentenceTransformer", return_value=self.mock_model):
            self.retriever = HybridRetriever.__new__(HybridRetriever)
            import threading
            self.retriever._lock = threading.Lock()
            self.retriever.model = self.mock_model

            # Mock 3 products in metadata
            self.retriever.metadata = [
                {
                    "product_id": "OEM-001-P01",
                    "product_name": "FortiGate 100F",
                    "oem_name": "Fortinet",
                    "sub_domain": "Network Security",
                    "domain": "Enterprise & Cyber Security",
                    "product_category": "Next-Generation Firewall",
                },
                {
                    "product_id": "OEM-002-P01",
                    "product_name": "CyberArk Privilege Cloud",
                    "oem_name": "CyberArk",
                    "sub_domain": "Identity & Access Management",
                    "domain": "Enterprise & Cyber Security",
                    "product_category": "PAM",
                },
                {
                    "product_id": "OEM-003-P01",
                    "product_name": "Splunk Enterprise Security",
                    "oem_name": "Splunk",
                    "sub_domain": "Security Operations",
                    "domain": "Enterprise & Cyber Security",
                    "product_category": "SIEM",
                },
            ]
            self.retriever.composite_data = {
                item["product_id"]: item for item in self.retriever.metadata
            }
            self.retriever.taxonomy = [
                {
                    "Sub_Domain": "Network Security",
                    "Keywords_Triggers": "firewall,ngfw,ssl inspection",
                },
                {
                    "Sub_Domain": "Identity & Access Management",
                    "Keywords_Triggers": "pam,vault,credentials,privileged access",
                },
            ]

            # 3 embeddings: Fortinet matches dummy_vec, CyberArk partial, Splunk orthogonal
            vec1 = np.zeros(384, dtype=np.float32)
            vec1[0] = 0.95
            vec2 = np.zeros(384, dtype=np.float32)
            vec2[0] = 0.50
            vec2[1] = 0.50
            vec3 = np.zeros(384, dtype=np.float32)
            vec3[1] = 1.0  # orthogonal to query (cosine = 0)

            self.retriever.embeddings = np.vstack([vec1, vec2, vec3])

    def test_semantic_search_cosine_computation(self):
        query_vec = np.zeros(384, dtype=np.float32)
        query_vec[0] = 1.0

        top_indices, scores = self.retriever._semantic_search(query_vec, top_k=3)
        self.assertEqual(len(top_indices), 3)
        # First index should be 0 with score ~1.0
        self.assertEqual(top_indices[0], 0)
        self.assertAlmostEqual(scores[0], 1.0, places=2)
        # Second should be 1
        self.assertEqual(top_indices[1], 1)
        self.assertGreater(scores[1], 0.6)
        # Third should be 2 with score 0.0
        self.assertEqual(top_indices[2], 2)
        self.assertAlmostEqual(scores[2], 0.0, places=2)

    def test_keyword_filter(self):
        # Matching "firewall" should match Fortinet
        indices = self.retriever._keyword_filter("Need a new firewall appliance")
        self.assertIsNotNone(indices)
        self.assertIn(0, indices)

        # Matching "CyberArk" should match CyberArk
        indices = self.retriever._keyword_filter("Evaluate CyberArk PAM")
        self.assertIsNotNone(indices)
        self.assertIn(1, indices)

        # No match returns None
        indices = self.retriever._keyword_filter("Completely unrelated query about apples")
        self.assertIsNone(indices)

    def test_similarity_floor_filtering(self):
        results = self.retriever.search("test firewall", top_k=5, min_similarity=SIMILARITY_FLOOR)
        # Results below 0.40 must be excluded (Splunk score is 0.0, so excluded)
        for r in results:
            self.assertGreaterEqual(r["similarity_score"], SIMILARITY_FLOOR)
            self.assertIn(r["confidence_tier"], ["HIGH", "MEDIUM", "LOW"])


if __name__ == "__main__":
    unittest.main()

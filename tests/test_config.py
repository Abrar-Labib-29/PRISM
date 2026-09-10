"""
Unit tests for configuration manager, scoring algorithms, and token estimators.
SRS References: §7.3, §8.1.6, §9.10, §12.3
Implementation Plan: TASK-P1.1
"""

import os
import tempfile
import unittest

from src.utils.config import (
    ConfigManager,
    NUM_CTX,
    SIMILARITY_CEILING,
    SIMILARITY_FLOOR,
    compute_confidence_tier,
    compute_fit_score,
    estimate_tokens,
    get_data_path,
)


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = os.path.join(self.temp_dir.name, "test_config.json")
        self.mgr = ConfigManager(self.config_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_values(self):
        self.assertEqual(self.mgr.get("appearance_mode"), "dark")
        self.assertEqual(self.mgr.get("similarity_floor"), 0.20)
        self.assertEqual(self.mgr.get("similarity_warning"), 0.35)

    def test_set_and_persist(self):
        self.mgr.set("test_key", "test_val")
        self.assertEqual(self.mgr.get("test_key"), "test_val")

        # Reload from disk
        reloaded = ConfigManager(self.config_file)
        self.assertEqual(reloaded.get("test_key"), "test_val")

    def test_compute_fit_score(self):
        # Exact similarity floor test (0.20 -> 0.0%)
        score_floor = compute_fit_score(SIMILARITY_FLOOR)
        self.assertEqual(score_floor, 0.0)

        # Exact ceiling test (0.80 -> 100.0%)
        score_top = compute_fit_score(SIMILARITY_CEILING)
        self.assertEqual(score_top, 100.0)

        # Midpoint test (0.50 is halfway between 0.20 and 0.80 -> 50.0%)
        score_mid = compute_fit_score(0.50)
        self.assertEqual(score_mid, 50.0)

        # Sub-floor similarity clamp test
        score_low = compute_fit_score(0.10)
        self.assertEqual(score_low, 0.0)

        # Floating point rounding test (must be rounded to 2 decimals)
        score_round = compute_fit_score(0.433333333333)
        self.assertIsInstance(score_round, float)
        self.assertEqual(score_round, round(score_round, 2))

    def test_compute_confidence_tier(self):
        self.assertEqual(compute_confidence_tier(90.0, True), "HIGH")
        self.assertEqual(compute_confidence_tier(90.0, False), "MEDIUM")
        self.assertEqual(compute_confidence_tier(70.0, True), "MEDIUM")
        self.assertEqual(compute_confidence_tier(50.0, True), "LOW")

    def test_estimate_tokens(self):
        self.assertEqual(estimate_tokens(""), 0)
        # 1 word * 1.3 = 1
        self.assertEqual(estimate_tokens("enterprise"), 1)
        # 4 words * 1.3 = 5
        self.assertEqual(estimate_tokens("enterprise next gen firewall"), 5)

    def test_get_data_path(self):
        p = get_data_path("composite_products.json")
        self.assertTrue(os.path.isabs(p) or os.path.exists(p))


if __name__ == "__main__":
    unittest.main()

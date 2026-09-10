"""
Unit tests for structured query and audit logging.
SRS References: §11.1, §11.3, §11.4
Implementation Plan: TASK-P1.2
"""

import json
import logging
import os
import tempfile
import unittest

from src.utils.logger import (
    MAX_LOG_SIZE_BYTES,
    QueryLogger,
    generate_query_id,
    setup_stdlib_logging,
)


class TestLogger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_file = os.path.join(self.temp_dir.name, "test_query_log.jsonl")
        self.logger = QueryLogger(log_path=self.log_file, max_bytes=1024 * 1024)

    def tearDown(self):
        root_logger = logging.getLogger("prism")
        for h in list(root_logger.handlers):
            h.close()
            root_logger.removeHandler(h)
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_generate_query_id(self):
        qid = generate_query_id()
        self.assertTrue(qid.startswith("req-"))
        self.assertEqual(len(qid), 9)

    def test_log_query_structure(self):
        entry = {
            "query_id": "req-12345",
            "input_text": "Need PAM with session recording",
            "fit_score": 85.5,
            "confidence_level": "HIGH",
        }
        self.logger.log_query(entry)

        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["query_id"], "req-12345")
        self.assertEqual(record["input_text"], "Need PAM with session recording")
        self.assertEqual(record["fit_score"], 85.5)
        self.assertEqual(record["confidence_level"], "HIGH")
        # Ensure default fields are present per §11.1 schema
        self.assertIn("pricing_mentions_stripped", record)
        self.assertIn("latency", record)
        self.assertIn("timestamp", record)

    def test_log_rotation(self):
        # Create a small max_bytes logger
        small_log = os.path.join(self.temp_dir.name, "small_log.jsonl")
        small_logger = QueryLogger(log_path=small_log, max_bytes=200)

        # Write enough data to trigger rotation
        for i in range(5):
            small_logger.log_query({"query_id": f"req-{i:05d}", "input_text": "A" * 80})

        # Rotated files should exist in directory
        all_files = os.listdir(self.temp_dir.name)
        rotated = [f for f in all_files if f.startswith("query_log_")]
        self.assertGreaterEqual(len(rotated), 1)

    def test_setup_stdlib_logging(self):
        # Configure logging in temp directory
        setup_stdlib_logging(log_dir=self.temp_dir.name, force=True)
        app_log = os.path.join(self.temp_dir.name, "prism_app.log")
        error_log = os.path.join(self.temp_dir.name, "prism_error.log")
        self.assertTrue(os.path.exists(app_log))
        self.assertTrue(os.path.exists(error_log))


if __name__ == "__main__":
    unittest.main()

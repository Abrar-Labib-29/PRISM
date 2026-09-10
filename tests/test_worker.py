"""
Unit tests for WorkerThread background execution, queue messaging, and cancellation preemption.
SRS References: §9.8, §9.9, §10.6, §10.7, §9.10 item 4
Implementation Plan: TASK-P2.1
"""

import queue
import time
import unittest
from unittest.mock import MagicMock

from src.core.service import AnalyzeRequest, AnalyzeResponse, Citation, ProductRecommendation
from src.core.worker import WorkerThread


class TestWorker(unittest.TestCase):
    def setUp(self):
        self.mock_service = MagicMock()
        self.ui_queue = queue.Queue()
        self.worker = WorkerThread(self.mock_service, self.ui_queue)

    def test_worker_lifecycle_and_queue_messages(self):
        # Mock analyze method to stream 2 tokens and return success
        def fake_analyze(req, token_stream_callback=None, cancel_event=None):
            if token_stream_callback:
                token_stream_callback("FortiGate ")
                token_stream_callback("100F")
            return AnalyzeResponse(
                query_id="req-99999",
                status="success",
                latency_ms=1200,
                recommendations=[
                    ProductRecommendation(
                        product_id="OEM-001-P01",
                        oem="Fortinet",
                        product_name="FortiGate 100F",
                        domain="Enterprise & Cyber Security",
                        sub_domain="Network Security",
                        confidence_score=0.90,
                        fit_score=85.0,
                        confidence_level="HIGH",
                        rationale="Recommended firewall.",
                        citations=[Citation(sheet="Product_Commercial", product_id="OEM-001-P01", field="Features", data_status="confirmed")],
                        features=["10 Gbps Firewall", "SSL Inspection"],
                        pros=["High throughput"],
                        cons=["Complex configuration"],
                    )
                ],
            )

        self.mock_service.analyze = fake_analyze

        req = AnalyzeRequest(query_text="Need firewall")
        self.worker.start_analysis(req)

        # Wait briefly for daemon thread to complete
        time.sleep(0.3)

        messages = []
        while not self.ui_queue.empty():
            messages.append(self.ui_queue.get_nowait())

        msg_types = [m.get("type") for m in messages]
        self.assertIn("STATUS_STEP", msg_types)
        self.assertIn("STREAM_TOKEN", msg_types)
        self.assertIn("STREAM_COMPLETE", msg_types)
        self.assertIn("ANALYSIS_SUCCESS", msg_types)

        # Check analysis success payload
        success_msg = next(m for m in messages if m.get("type") == "ANALYSIS_SUCCESS")
        payload: AnalyzeResponse = success_msg.get("payload")
        self.assertEqual(payload.query_id, "req-99999")
        self.assertEqual(len(payload.recommendations), 1)

    def test_worker_cancellation(self):
        # Mock analyze method that blocks until cancelled
        def slow_analyze(req, token_stream_callback=None, cancel_event=None):
            while cancel_event and not cancel_event.is_set():
                time.sleep(0.05)
            return AnalyzeResponse(
                query_id="req-cancelled",
                status="cancelled",
                latency_ms=100,
                recommendations=[],
                error_message="Cancelled by user",
            )

        self.mock_service.analyze = slow_analyze

        req = AnalyzeRequest(query_text="Slow task")
        self.worker.start_analysis(req)
        self.assertTrue(self.worker.is_running)

        # Cancel
        self.worker.cancel()
        self.assertFalse(self.worker.is_running)

        messages = []
        while not self.ui_queue.empty():
            messages.append(self.ui_queue.get_nowait())

        msg_types = [m.get("type") for m in messages]
        self.assertIn("ANALYSIS_CANCELLED", msg_types)


if __name__ == "__main__":
    unittest.main()

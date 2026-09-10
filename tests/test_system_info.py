"""
Unit tests for host system diagnostics, RAM monitoring, single-instance mutex, and accessibility.
SRS References: §10.7, §11.4, §8.1.10, §6.9
Implementation Plan: TASK-P1.3
"""

import os
import unittest

from src.utils.system_info import (
    check_reduced_motion,
    get_available_system_ram_mb,
    get_cpu_percent,
    get_ram_usage_mb,
    get_system_ram_mb,
    get_total_system_ram_mb,
    release_single_instance,
    verify_single_instance,
)


class TestSystemInfo(unittest.TestCase):
    def tearDown(self):
        release_single_instance()

    def test_memory_diagnostics(self):
        rss = get_ram_usage_mb()
        self.assertIsInstance(rss, float)
        self.assertGreater(rss, 0.0)

        sys_ram = get_system_ram_mb()
        self.assertIsInstance(sys_ram, float)
        self.assertGreater(sys_ram, 0.0)

        total_ram = get_total_system_ram_mb()
        self.assertIsInstance(total_ram, float)
        self.assertGreater(total_ram, 0.0)

        avail_ram = get_available_system_ram_mb()
        self.assertIsInstance(avail_ram, float)
        self.assertGreater(avail_ram, 0.0)

    def test_cpu_diagnostics(self):
        cpu = get_cpu_percent(interval=None)
        self.assertIsInstance(cpu, float)
        self.assertGreaterEqual(cpu, 0.0)

    def test_reduced_motion_detection(self):
        # Should return a bool without raising
        res = check_reduced_motion()
        self.assertIsInstance(res, bool)

    def test_single_instance_named_mutex(self):
        release_single_instance()
        test_mutex = "Global\\TestPRISMMutex_ABC123"
        # First verification succeeds
        first = verify_single_instance(test_mutex)
        self.assertTrue(first)

        # Same process holds it
        second = verify_single_instance(test_mutex)
        self.assertTrue(second)

        release_single_instance()


if __name__ == "__main__":
    unittest.main()

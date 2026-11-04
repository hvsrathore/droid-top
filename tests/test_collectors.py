"""
Tests for DroidTop Hardware and System Collectors.
"""

import unittest
from droidtop.collectors.system import SystemCollector
from droidtop.collectors.cpu import CPUCollector
from droidtop.collectors.memory import MemoryCollector
from droidtop.collectors.battery import BatteryCollector
from droidtop.collectors.thermal import ThermalCollector
from droidtop.collectors.storage import StorageCollector
from droidtop.collectors.network import NetworkCollector
from droidtop.collectors.process import ProcessCollector


class TestCollectors(unittest.TestCase):

    def test_system_collector(self):
        col = SystemCollector()
        stats = col.get_live_stats()
        self.assertIn("uptime_sec", stats)
        self.assertIn("loads", stats)
        self.assertIn("android", stats)
        self.assertIn("soc", stats)
        self.assertGreaterEqual(stats["uptime_sec"], 0)

    def test_cpu_collector(self):
        col = CPUCollector()
        data = col.update()
        self.assertIn("overall_pct", data)
        self.assertIn("cores", data)
        self.assertIn("clusters", data)
        self.assertGreaterEqual(len(data["cores"]), 1)

    def test_memory_collector(self):
        col = MemoryCollector()
        data = col.update()
        self.assertIn("ram_total_mb", data)
        self.assertIn("ram_used_mb", data)
        self.assertIn("swap_total_mb", data)
        self.assertGreater(data["ram_total_mb"], 0)

    def test_battery_collector(self):
        col = BatteryCollector()
        data = col.update()
        self.assertIn("level", data)
        self.assertIn("status", data)
        self.assertIn("voltage", data)

    def test_thermal_collector(self):
        col = ThermalCollector()
        data = col.update()
        self.assertIn("categories", data)
        self.assertIn("max_shell", data)
        self.assertIn("max_cpu", data)

    def test_storage_collector(self):
        col = StorageCollector()
        disks = col.update()
        self.assertIsInstance(disks, list)
        if disks:
            self.assertIn("used_pct", disks[0])

    def test_network_collector(self):
        col = NetworkCollector()
        data = col.update()
        self.assertIn("interfaces", data)
        self.assertIn("radio_type", data)

    def test_process_collector(self):
        col = ProcessCollector()
        procs = col.update(total_ram_mb=8000.0)
        self.assertIsInstance(procs, list)
        if procs:
            p0 = procs[0]
            self.assertGreater(p0.pid, 0)
            self.assertTrue(hasattr(p0, "cpu_pct"))
            self.assertTrue(hasattr(p0, "rss_mb"))


if __name__ == "__main__":
    unittest.main()

"""
DroidTop - Memory & Android ZRAM Swap Collector.
Parses /proc/meminfo to track physical RAM, ZRAM swap, caching, and buffers.
"""

from typing import Dict, List


class MemoryCollector:
    """Collects RAM and ZRAM Swap metrics and history."""

    def __init__(self, history_size: int = 120):
        self.history_size = history_size
        self.ram_history: List[float] = [0.0] * 20
        self.swap_history: List[float] = [0.0] * 20

    def update(self) -> Dict:
        """Parse /proc/meminfo and compute usage stats."""
        raw = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val_str = parts[1].strip().split()[0]
                        if val_str.isdigit():
                            raw[key] = int(val_str)  # values in kB
        except Exception:
            pass

        # Extract values in Megabytes
        total_kb = raw.get("MemTotal", 1)
        avail_kb = raw.get("MemAvailable", raw.get("MemFree", 0))
        free_kb = raw.get("MemFree", 0)
        buffers_kb = raw.get("Buffers", 0)
        cached_kb = raw.get("Cached", 0)
        active_kb = raw.get("Active", 0)
        inactive_kb = raw.get("Inactive", 0)
        dirty_kb = raw.get("Dirty", 0)

        used_kb = max(0, total_kb - avail_kb)
        ram_pct = (used_kb / total_kb) * 100.0 if total_kb > 0 else 0.0

        # Android ZRAM / Swap
        swap_total_kb = raw.get("SwapTotal", 0)
        swap_free_kb = raw.get("SwapFree", 0)
        swap_used_kb = max(0, swap_total_kb - swap_free_kb)
        swap_pct = (swap_used_kb / swap_total_kb) * 100.0 if swap_total_kb > 0 else 0.0
        swap_cached_kb = raw.get("SwapCached", 0)

        # Update histories
        self.ram_history.append(ram_pct)
        if len(self.ram_history) > self.history_size:
            self.ram_history.pop(0)

        self.swap_history.append(swap_pct)
        if len(self.swap_history) > self.history_size:
            self.swap_history.pop(0)

        return {
            "ram_total_mb": total_kb / 1024.0,
            "ram_used_mb": used_kb / 1024.0,
            "ram_free_mb": free_kb / 1024.0,
            "ram_avail_mb": avail_kb / 1024.0,
            "ram_cached_mb": cached_kb / 1024.0,
            "ram_buffers_mb": buffers_kb / 1024.0,
            "ram_active_mb": active_kb / 1024.0,
            "ram_inactive_mb": inactive_kb / 1024.0,
            "ram_dirty_mb": dirty_kb / 1024.0,
            "ram_pct": ram_pct,
            "ram_history": list(self.ram_history),
            "swap_total_mb": swap_total_kb / 1024.0,
            "swap_used_mb": swap_used_kb / 1024.0,
            "swap_free_mb": swap_free_kb / 1024.0,
            "swap_cached_mb": swap_cached_kb / 1024.0,
            "swap_pct": swap_pct,
            "swap_history": list(self.swap_history),
        }

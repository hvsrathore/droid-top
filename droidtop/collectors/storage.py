"""
DroidTop - Android Storage & Partition Collector.
Monitors Internal Emulated Storage, Termux Data, and System partitions.
"""

import os
from typing import Dict, List


class StorageCollector:
    """Collects disk filesystem capacities and free space."""

    TARGET_PATHS = [
        ("/storage/emulated/0", "Internal Storage (User)"),
        ("/data/data/com.termux/files", "Termux Environment"),
        ("/", "System Root"),
    ]

    def update(self) -> List[Dict]:
        """Query storage stats for standard Android mount points."""
        partitions = []
        for path, label in self.TARGET_PATHS:
            if not os.path.exists(path):
                continue
            try:
                st = os.statvfs(path)
                block_size = st.f_frsize
                total_bytes = st.f_blocks * block_size
                free_bytes = st.f_bavail * block_size
                used_bytes = max(0, total_bytes - free_bytes)

                total_gb = total_bytes / (1024.0 ** 3)
                free_gb = free_bytes / (1024.0 ** 3)
                used_gb = used_bytes / (1024.0 ** 3)
                used_pct = (used_bytes / total_bytes * 100.0) if total_bytes > 0 else 0.0

                partitions.append({
                    "path": path,
                    "label": label,
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "used_pct": used_pct,
                })
            except Exception:
                pass

        return partitions

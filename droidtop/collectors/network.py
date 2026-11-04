"""
DroidTop - Android Network & Cellular Radio Collector.
Parses network interfaces, IP addresses, cellular radio standards, and carrier info.
"""

import subprocess
import os
from typing import Dict, List


class NetworkCollector:
    """Collects network interfaces, IP configurations, and cellular radio properties."""

    def __init__(self):
        self.cached_carrier = ""
        self.cached_sim = ""

    def update(self) -> Dict:
        """Fetch active network interfaces and radio state."""
        interfaces = []
        try:
            p = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=1)
            cur = None
            for line in p.stdout.splitlines():
                if not line.startswith(" ") and ":" in line:
                    parts = line.split(":")
                    name = parts[0].strip()
                    flags = ""
                    if "flags=" in line:
                        try:
                            flags = line.split("flags=")[1].split("<")[1].split(">")[0]
                        except Exception:
                            pass
                    cur = {"name": name, "ip": "", "flags": flags}
                    interfaces.append(cur)
                elif cur and "inet " in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        cur["ip"] = parts[1]
        except Exception:
            pass

        # Radio & Telephony properties
        radio_type = "Unknown"
        sim_operator = ""
        try:
            p = subprocess.run(["getprop", "gsm.network.type"], capture_output=True, text=True, timeout=1)
            val = p.stdout.strip().strip("[]")
            if val:
                radio_type = val
        except Exception:
            pass

        try:
            p = subprocess.run(["getprop", "gsm.sim.operator.alpha"], capture_output=True, text=True, timeout=1)
            val = p.stdout.strip().strip("[]")
            if val:
                sim_operator = val
        except Exception:
            pass

        return {
            "interfaces": interfaces,
            "radio_type": radio_type,
            "sim_operator": sim_operator,
        }

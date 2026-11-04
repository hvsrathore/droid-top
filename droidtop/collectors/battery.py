"""
DroidTop - Android Battery, Power & Health Collector.
Reads battery level, charging state, voltage, temperature, and cycle count.
"""

import os
import glob
import subprocess
from typing import Dict, List, Optional


class BatteryCollector:
    """Collects battery metrics, health, power status, and maintains history."""

    STATUS_MAP = {
        "1": "Unknown",
        "2": "Charging",
        "3": "Discharging",
        "4": "Not Charging",
        "5": "Full",
    }

    def __init__(self, history_size: int = 60):
        self.history_size = history_size
        self.level_history: List[float] = [75.0] * 10
        self.vbat_zone_path = self._find_thermal_zone("vbat")
        self.battery_temp_zone_path = self._find_thermal_zone("battery")
        self.cycle_count_cached = self._read_cycle_count()

    def _find_thermal_zone(self, target_type: str) -> Optional[str]:
        for p in glob.glob("/sys/class/thermal/thermal_zone*"):
            type_file = os.path.join(p, "type")
            if os.path.exists(type_file):
                try:
                    with open(type_file) as f:
                        if target_type.lower() in f.read().strip().lower():
                            return os.path.join(p, "temp")
                except Exception:
                    pass
        return None

    def _read_cycle_count(self) -> str:
        try:
            p = subprocess.run(
                ["getprop", "persist.sys.BatteryCycleCount"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            val = p.stdout.strip()
            if val:
                return val
        except Exception:
            pass
        return "N/A"

    def update(self) -> Dict:
        """Fetch current battery status, level, voltage, and temperature."""
        level = 0.0
        status_code = ""

        # 1. Level via getprop
        try:
            p = subprocess.run(
                ["getprop", "sys.UiBatteryLevel"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            out = p.stdout.strip()
            if out.isdigit():
                level = float(out)
        except Exception:
            pass

        # Fallback to sysfs capacity
        if level <= 0:
            for cap_path in ["/sys/class/power_supply/battery/capacity", "/sys/class/power_supply/bms/capacity"]:
                if os.path.exists(cap_path):
                    try:
                        with open(cap_path) as f:
                            level = float(f.read().strip())
                            break
                    except Exception:
                        pass

        # 2. Status
        try:
            p = subprocess.run(
                ["getprop", "debug.tracing.battery_status"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            status_code = p.stdout.strip()
        except Exception:
            pass

        status_text = self.STATUS_MAP.get(status_code, "Discharging" if level > 0 else "Unknown")

        # 3. Voltage
        voltage_v = 0.0
        if self.vbat_zone_path and os.path.exists(self.vbat_zone_path):
            try:
                with open(self.vbat_zone_path) as f:
                    v_raw = float(f.read().strip())
                    # vbat is in mV, e.g. 4146 mV -> 4.15 V
                    voltage_v = v_raw / 1000.0 if v_raw > 100 else v_raw
            except Exception:
                pass

        # 4. Temperature
        temp_c = 0.0
        if self.battery_temp_zone_path and os.path.exists(self.battery_temp_zone_path):
            try:
                with open(self.battery_temp_zone_path) as f:
                    t_raw = float(f.read().strip())
                    temp_c = t_raw / 1000.0 if t_raw > 1000 else t_raw
            except Exception:
                pass

        # Update history
        if level > 0:
            self.level_history.append(level)
            if len(self.level_history) > self.history_size:
                self.level_history.pop(0)

        # Health estimation
        health = "Good"
        if temp_c > 45.0:
            health = "Overheat"
        elif temp_c > 40.0:
            health = "Warm"

        return {
            "level": level,
            "status": status_text,
            "is_charging": status_text in ("Charging", "Full"),
            "voltage": voltage_v,
            "temperature": temp_c,
            "cycles": self.cycle_count_cached,
            "health": health,
            "history": list(self.level_history),
        }

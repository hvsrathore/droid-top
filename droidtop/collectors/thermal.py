"""
DroidTop - Hardware Thermal & Temperature Sensors Collector.
Scans Android thermal zones for CPU, GPU, DDR, Battery, and Shell skin sensors.
"""

import os
import glob
from typing import Dict, List, Tuple


class ThermalSensor:
    """Represents a hardware temperature sensor."""

    def __init__(self, zone_id: str, name: str, category: str, temp_path: str):
        self.zone_id = zone_id
        self.name = name
        self.category = category  # "Shell", "CPU", "GPU", "Memory", "Battery", "Other"
        self.temp_path = temp_path
        self.current_temp: float = 0.0
        self.history: List[float] = [0.0] * 12

    def update(self) -> float:
        try:
            with open(self.temp_path, "r") as f:
                val = float(f.read().strip())
                # Kernel thermal values are typically in millidegrees C (e.g. 34800 -> 34.8)
                self.current_temp = val / 1000.0 if val > 1000 else val
        except Exception:
            pass

        self.history.append(self.current_temp)
        if len(self.history) > 20:
            self.history.pop(0)
        return self.current_temp


class ThermalCollector:
    """Discovers, categorizes, and updates all hardware thermal sensors."""

    def __init__(self):
        self.sensors: List[ThermalSensor] = []
        self._discover_sensors()

    def _discover_sensors(self):
        zone_paths = sorted(
            glob.glob("/sys/class/thermal/thermal_zone*"),
            key=lambda x: int(os.path.basename(x).replace("thermal_zone", "") or 0)
        )

        for p in zone_paths:
            zone_id = os.path.basename(p)
            type_path = os.path.join(p, "type")
            temp_path = os.path.join(p, "temp")

            if not (os.path.exists(type_path) and os.path.exists(temp_path)):
                continue

            try:
                with open(type_path, "r") as f:
                    sensor_type = f.read().strip()

                st_lower = sensor_type.lower()
                category = "Other"
                if "shell" in st_lower:
                    category = "Shell"
                elif "cpu" in st_lower or "cpuss" in st_lower:
                    category = "CPU"
                elif "gpu" in st_lower:
                    category = "GPU"
                elif "ddr" in st_lower:
                    category = "Memory"
                elif "bat" in st_lower or "bms" in st_lower:
                    category = "Battery"
                elif "video" in st_lower:
                    category = "Video"

                # Filter out raw BCL voltage level sensors that report 0 or are internal IRQ trip points
                if "bcl-lvl" in st_lower or "ibat-lvl" in st_lower:
                    continue

                sensor = ThermalSensor(zone_id, sensor_type, category, temp_path)
                self.sensors.append(sensor)
            except Exception:
                pass

    def update(self) -> Dict:
        """Read temperatures from all discovered sensors."""
        categories: Dict[str, List[Dict]] = {
            "Shell": [],
            "CPU": [],
            "GPU": [],
            "Memory": [],
            "Battery": [],
            "Other": [],
        }

        max_shell = 0.0
        max_cpu = 0.0
        gpu_temp = 0.0

        for sensor in self.sensors:
            temp = sensor.update()
            if sensor.category == "Shell" and temp > max_shell:
                max_shell = temp
            elif sensor.category == "CPU" and temp > max_cpu:
                max_cpu = temp
            elif sensor.category == "GPU" and temp > gpu_temp:
                gpu_temp = temp

            cat_list = categories.get(sensor.category, categories["Other"])
            cat_list.append({
                "zone": sensor.zone_id,
                "name": sensor.name,
                "category": sensor.category,
                "temp": temp,
                "history": list(sensor.history),
            })

        # Thermal state assessment
        throttling = (max_cpu > 75.0) or (max_shell > 46.0)
        thermal_state = "COOL"
        if throttling:
            thermal_state = "THROTTLING"
        elif max_shell > 41.0 or max_cpu > 65.0:
            thermal_state = "HOT"
        elif max_shell > 37.0 or max_cpu > 55.0:
            thermal_state = "WARM"

        return {
            "categories": categories,
            "max_shell": max_shell,
            "max_cpu": max_cpu,
            "gpu_temp": gpu_temp,
            "thermal_state": thermal_state,
            "is_throttling": throttling,
            "total_sensors": len(self.sensors),
        }

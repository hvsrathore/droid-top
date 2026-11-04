"""
DroidTop - Detailed Hardware Thermal & Sensor Zones View.
"""

from typing import List, Dict
from .base import BaseView
from ..themes.palette import Theme
from ..terminal.box import Box
from ..terminal.canvas import Sparkline


class ThermalView(BaseView):
    """Detailed hardware thermal sensors inspector with skin and component breakdowns."""

    def __init__(self):
        super().__init__("thermal", "[5] Sensors")

    def render(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        therm = data["thermal"]
        lines = []

        # Color badges for header
        shell_col = theme.temp_color(min(1.0, therm["max_shell"] / 50.0))
        cpu_col = theme.temp_color(min(1.0, therm["max_cpu"] / 75.0))
        gpu_col = theme.temp_color(min(1.0, therm["gpu_temp"] / 65.0))

        status_text = f"Skin: {shell_col}{therm['max_shell']:.1f}°C\033[0m │ CPU: {cpu_col}{therm['max_cpu']:.1f}°C\033[0m │ GPU: {gpu_col}{therm['gpu_temp']:.1f}°C\033[0m"

        box = Box(
            0, 0, width, height,
            title="HARDWARE SENSORS & THERMAL ZONES",
            badge_right=status_text,
            border_ansi=theme.border_ansi(True),
            title_ansi=theme.title_ansi(),
        )
        lines.append(box.render_top_border())

        inner_w = box.inner_w
        inner_h = box.inner_h
        content = []

        # 1. Thermal Warning Banner
        if therm["is_throttling"]:
            content.append(f" {theme.danger_ansi()}⚠ THERMAL THROTTLING DETECTED! Cores or chassis exceeding safe thermal limits.\033[0m")
        else:
            state_col = theme.success_ansi() if therm["thermal_state"] == "COOL" else theme.warning_ansi()
            content.append(f" {theme.dim_ansi()}Thermal Status:\033[0m {state_col}{therm['thermal_state']}\033[0m │ {theme.dim_ansi()}Total Active Sensors:\033[0m {therm['total_sensors']}")

        # 2. Priority Categories
        priority_cats = ["Shell", "CPU", "GPU", "Memory", "Battery"]

        for cat in priority_cats:
            sensors = therm["categories"].get(cat, [])
            if not sensors:
                continue
            if len(content) >= inner_h:
                break

            content.append(f"{theme.dim_ansi()} ─── {cat} Sensors ({len(sensors)}) ───\033[0m")

            for s in sensors[:8]:
                if len(content) >= inner_h:
                    break
                t_val = s["temp"]
                t_col = theme.temp_color(min(1.0, t_val / (45.0 if cat == "Shell" else 75.0)))
                spark = Sparkline.render(s["history"], 10, max_val=(45.0 if cat == "Shell" else 80.0), color_func=theme.temp_color)

                badge = "NORMAL"
                if cat == "Shell":
                    if t_val > 44.0: badge = "HOT"
                    elif t_val > 38.0: badge = "WARM"
                else:
                    if t_val > 70.0: badge = "HOT"
                    elif t_val > 55.0: badge = "WARM"

                badge_col = theme.danger_ansi() if badge == "HOT" else (theme.warning_ansi() if badge == "WARM" else theme.dim_ansi())
                s_name = s["name"][:20]

                content.append(
                    f"  {s['zone']:<15} {s_name:<20} {t_col}{t_val:>5.1f} °C\033[0m  "
                    f"[{badge_col}{badge:<6}\033[0m] {spark}"
                )

        for line in content[:inner_h]:
            lines.append(box.wrap_inner_line(line))

        while len(lines) < height - 1:
            lines.append(box.render_empty_line())

        lines.append(box.render_bottom_border())
        return lines[:height]

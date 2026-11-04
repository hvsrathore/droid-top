"""
DroidTop - Detailed Battery, Power & Health Inspector.
"""

from typing import List, Dict
from .base import BaseView
from ..themes.palette import Theme
from ..terminal.box import Box
from ..terminal.canvas import BrailleCanvas, ProgressBar


class PowerView(BaseView):
    """Detailed Android battery, charging status, voltage, temp, and cycle inspector."""

    def __init__(self):
        super().__init__("power", "[4] Battery")
        self.canvas = BrailleCanvas(60, 5)

    def render(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        bat = data["battery"]
        lines = []

        bat_color = theme.battery_color(bat["level"] / 100.0)

        box = Box(
            0, 0, width, height,
            title="BATTERY & POWER MANAGEMENT",
            badge_right=f"{bat_color}{bat['level']:.0f}%\033[0m [{bat['status']}]",
            border_ansi=theme.border_ansi(True),
            title_ansi=theme.title_ansi(),
        )
        lines.append(box.render_top_border())

        inner_w = box.inner_w
        inner_h = box.inner_h
        content = []

        # 1. Large Visual Battery Bar
        bar_w = max(10, inner_w - 4)
        bat_bar = ProgressBar.render(bat["level"], bar_w, color_func=theme.battery_color)
        content.append(f" {bat_bar}")

        status_glyph = "⚡" if bat["is_charging"] else "🔋"
        content.append(
            f" {status_glyph} {theme.dim_ansi()}Level:\033[0m {bat_color}{bat['level']:>3.0f}%\033[0m  "
            f"│ {theme.dim_ansi()}Status:\033[0m {bat['status']}  "
            f"│ {theme.dim_ansi()}Health:\033[0m {bat['health']}  "
            f"│ {theme.dim_ansi()}Cycles:\033[0m {bat['cycles']}"
        )

        # 2. Electrical & Thermal Specs
        content.append(f"{theme.dim_ansi()} ─── Electrical & Thermal Diagnostics ───\033[0m")
        temp_c = theme.temp_color(min(1.0, bat["temperature"] / 45.0))
        content.append(
            f"  {theme.dim_ansi()}Terminal Voltage:\033[0m {bat['voltage']:.3f} V   "
            f"│ {theme.dim_ansi()}Battery Temp:\033[0m {temp_c}{bat['temperature']:.1f} °C\033[0m   "
            f"│ {theme.dim_ansi()}Capacity State:\033[0m {'Optimal' if bat['cycles'] != 'N/A' and int(bat['cycles']) < 500 else 'Degraded'}"
        )

        # 3. Braille Level History
        content.append(f"{theme.dim_ansi()} ─── Battery Level History ───\033[0m")
        graph_h = max(2, min(5, inner_h // 5))
        graph_w = max(10, inner_w - 2)

        self.canvas.resize(graph_w, graph_h)
        self.canvas.draw_curve(bat["history"], fill=True, max_val=100.0)

        for gl in self.canvas.render_rows(color_func=theme.battery_color):
            content.append(f" {gl}")

        # 4. Mobile Power Tips
        content.append(f"{theme.dim_ansi()} ─── Mobile Power Optimization Tips ───\033[0m")
        content.append(f"  • Termux WakeLock: run '{theme.title_ansi()}termux-wake-lock\033[0m' to keep background scripts alive.")
        content.append(f"  • AMOLED Savings: switch to '{theme.title_ansi()}oled\033[0m' theme (press 'm') to turn off black pixels.")
        content.append(f"  • Refresh Rate: press '{theme.title_ansi()}-\033[0m' to lower update rate (save CPU/battery).")

        for line in content[:inner_h]:
            lines.append(box.wrap_inner_line(line))

        while len(lines) < height - 1:
            lines.append(box.render_empty_line())

        lines.append(box.render_bottom_border())
        return lines[:height]

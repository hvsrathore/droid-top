"""
DroidTop - Detailed CPU Architecture & Heterogeneous Cluster Inspector.
"""

from typing import List, Dict
from .base import BaseView
from ..themes.palette import Theme
from ..terminal.box import Box
from ..terminal.canvas import BrailleCanvas, Sparkline, ProgressBar


class CPUView(BaseView):
    """Detailed CPU view showing Braille history graph, clusters, and individual core frequencies."""

    def __init__(self):
        super().__init__("cpu", "[2] CPU Cores")
        self.canvas = BrailleCanvas(60, 6)

    def render(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        cpu = data["cpu"]
        sys_info = data["system"]
        lines = []

        # 1. Main CPU Box
        box = Box(
            0, 0, width, height,
            title=f"CPU: {sys_info['soc']} ({sys_info['soc_code']})",
            badge_right=f"LOAD: {cpu['overall_pct']:>5.1f}%",
            border_ansi=theme.border_ansi(True),
            title_ansi=theme.title_ansi(),
        )
        lines.append(box.render_top_border())

        inner_w = box.inner_w
        inner_h = box.inner_h

        content = []

        # Info line
        loads_str = f"{sys_info['loads'][0]:.2f}, {sys_info['loads'][1]:.2f}, {sys_info['loads'][2]:.2f}"
        content.append(f" {theme.dim_ansi()}SoC:\033[0m {sys_info['soc']} │ {theme.dim_ansi()}Cores:\033[0m {cpu['total_cores']} │ {theme.dim_ansi()}Uptime:\033[0m {sys_info['uptime_str']} │ {theme.dim_ansi()}LoadAvg:\033[0m {loads_str}")

        # Braille Graph
        graph_h = max(3, min(8, inner_h // 3))
        graph_w = max(10, inner_w - 2)

        self.canvas.resize(graph_w, graph_h)
        self.canvas.draw_curve(cpu["history"], fill=True, max_val=100.0)

        for gl in self.canvas.render_rows(color_func=theme.cpu_color):
            content.append(f" {gl}")

        # Separator: Heterogeneous Clusters
        content.append(f"{theme.dim_ansi()} ─── Heterogeneous Core Clusters (EAS / WALT) ───\033[0m")

        for cl in cpu["clusters"]:
            c_color = theme.cpu_color(cl["usage_pct"] / 100.0)
            bar = ProgressBar.render(cl["usage_pct"], max(8, inner_w - 48), color_func=theme.cpu_color)
            cores_txt = ",".join(str(c) for c in cl["cpus"])
            content.append(
                f" {cl['name']:<20} Cores:[{cores_txt:<5}] {cl['min_mhz']:>4}-{cl['max_mhz']:<4}MHz "
                f"[{bar}] {c_color}{cl['usage_pct']:>5.1f}%\033[0m"
            )

        # Separator: Individual Cores Live Frequencies
        content.append(f"{theme.dim_ansi()} ─── Individual Core Frequencies & Activity ───\033[0m")

        for ci in cpu["cores"]:
            if len(content) >= inner_h:
                break
            c_color = theme.cpu_color(ci["pct"] / 100.0)
            bar = ProgressBar.render(ci["pct"], max(8, inner_w - 42), color_func=theme.cpu_color)
            spark = Sparkline.render(ci["history"], 10, max_val=100.0, color_func=theme.cpu_color)
            content.append(
                f" CPU {ci['core']:<2} {ci['mhz']:>5} MHz [{bar}] {c_color}{ci['pct']:>5.1f}%\033[0m {spark}"
            )

        for line in content[:inner_h]:
            lines.append(box.wrap_inner_line(line))

        while len(lines) < height - 1:
            lines.append(box.render_empty_line())

        lines.append(box.render_bottom_border())
        return lines[:height]

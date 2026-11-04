"""
DroidTop - Master Overview Dashboard.
Adapts responsively between multi-column grid (wide screens) and stacked cards (mobile phones).
"""

from typing import List, Dict
from .base import BaseView
from ..themes.palette import Theme
from ..terminal.box import Box
from ..terminal.canvas import BrailleCanvas, Sparkline, ProgressBar
from ..terminal.screen import slice_ansi, visible_len
from ..terminal.input import MouseEvent


class OverviewView(BaseView):
    """Master resource overview dashboard with auto-responsive layout."""

    def __init__(self):
        super().__init__("overview", "[1] Overview")
        self.canvas_cpu = BrailleCanvas(30, 4)
        self.canvas_mem = BrailleCanvas(30, 3)

    def render(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        if width >= 90:
            return self._render_wide(width, height, data, theme)
        else:
            return self._render_narrow(width, height, data, theme)

    def _render_wide(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        """Multi-column layout for tablets, landscape, or desktop SSH."""
        left_w = int(width * 0.48)
        right_w = width - left_w

        top_h = max(8, int(height * 0.45))
        bottom_h = height - top_h

        # 1. Top-Left: CPU Box
        cpu_box = Box(
            0, 0, left_w, top_h,
            title="CPU",
            badge_right=f"{data['cpu']['overall_pct']:>5.1f}%",
            border_ansi=theme.border_ansi(True),
            title_ansi=theme.title_ansi(),
        )
        cpu_lines = self._build_cpu_content(cpu_box.inner_w, cpu_box.inner_h, data, theme)
        cpu_rendered = [cpu_box.render_top_border()] + [cpu_box.wrap_inner_line(l) for l in cpu_lines] + [cpu_box.render_bottom_border()]

        # 2. Bottom-Left: Memory & Storage Box
        mem_box = Box(
            0, 0, left_w, bottom_h,
            title="MEM & DISK",
            badge_right=f"RAM: {data['memory']['ram_pct']:.0f}%  ZRAM: {data['memory']['swap_pct']:.0f}%",
            border_ansi=theme.border_ansi(),
            title_ansi=theme.title_ansi(),
        )
        mem_lines = self._build_mem_disk_content(mem_box.inner_w, mem_box.inner_h, data, theme)
        mem_rendered = [mem_box.render_top_border()] + [mem_box.wrap_inner_line(l) for l in mem_lines] + [mem_box.render_bottom_border()]

        left_rendered = (cpu_rendered + mem_rendered)[:height]

        # 3. Top-Right: Battery & Thermal Box
        bat_box = Box(
            0, 0, right_w, max(7, int(top_h * 0.75)),
            title="BATTERY & SENSORS",
            badge_right=f"{data['battery']['level']:.0f}% [{data['battery']['status']}]",
            border_ansi=theme.border_ansi(),
            title_ansi=theme.title_ansi(),
        )
        bat_lines = self._build_bat_thermal_content(bat_box.inner_w, bat_box.inner_h, data, theme)
        bat_rendered = [bat_box.render_top_border()] + [bat_box.wrap_inner_line(l) for l in bat_lines] + [bat_box.render_bottom_border()]

        # 4. Bottom-Right: Top Processes Box
        proc_h = height - len(bat_rendered)
        proc_box = Box(
            0, 0, right_w, proc_h,
            title="TOP PROCESSES",
            badge_right=f"{len(data['processes'])} procs",
            border_ansi=theme.border_ansi(),
            title_ansi=theme.title_ansi(),
        )
        proc_lines = self._build_proc_content(proc_box.inner_w, proc_box.inner_h, data, theme)
        proc_rendered = [proc_box.render_top_border()] + [proc_box.wrap_inner_line(l) for l in proc_lines] + [proc_box.render_bottom_border()]

        right_rendered = (bat_rendered + proc_rendered)[:height]

        # Combine columns horizontally
        combined = []
        for i in range(height):
            l_line = left_rendered[i] if i < len(left_rendered) else " " * left_w
            r_line = right_rendered[i] if i < len(right_rendered) else " " * right_w
            combined.append(f"{l_line}{r_line}")

        return combined

    def _render_narrow(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        """Stacked card layout optimized for mobile phone screens in portrait mode."""
        lines = []

        # 1. CPU Card
        cpu_h = max(6, min(10, int(height * 0.32)))
        cpu_box = Box(
            0, 0, width, cpu_h,
            title="CPU",
            badge_right=f"{data['cpu']['overall_pct']:>5.1f}%",
            border_ansi=theme.border_ansi(True),
            title_ansi=theme.title_ansi(),
        )
        cpu_content = self._build_cpu_content(cpu_box.inner_w, cpu_box.inner_h, data, theme)
        lines.append(cpu_box.render_top_border())
        for l in cpu_content:
            lines.append(cpu_box.wrap_inner_line(l))
        lines.append(cpu_box.render_bottom_border())

        # 2. Battery & Thermal Status Line
        bat = data["battery"]
        therm = data["thermal"]
        bat_color = theme.battery_color(bat["level"] / 100.0)
        therm_color = theme.temp_color(min(1.0, therm["max_shell"] / 50.0))
        bat_card = Box(
            0, 0, width, 4,
            title="BATTERY & THERMAL",
            badge_right=f"{bat_color}{bat['level']:.0f}%\033[0m {bat['status']}",
            border_ansi=theme.border_ansi(),
            title_ansi=theme.title_ansi(),
        )
        bat_text = (
            f" ⚡ {bat_color}{bat['level']:>3.0f}%\033[0m ({bat['voltage']:.2f}V) "
            f"│ Skin: {therm_color}{therm['max_shell']:.1f}°C\033[0m "
            f"│ CPU: {therm['max_cpu']:.1f}°C "
            f"│ GPU: {therm['gpu_temp']:.1f}°C"
        )
        lines.append(bat_card.render_top_border())
        lines.append(bat_card.wrap_inner_line(bat_text))
        lines.append(bat_card.render_bottom_border())

        # 3. Top Processes Card filling remaining space
        avail_proc_h = max(6, height - len(lines))
        proc_box = Box(
            0, 0, width, avail_proc_h,
            title="PROCESSES",
            badge_right=f"{len(data['processes'])} total",
            border_ansi=theme.border_ansi(),
            title_ansi=theme.title_ansi(),
        )
        proc_content = self._build_proc_content(proc_box.inner_w, proc_box.inner_h, data, theme)
        lines.append(proc_box.render_top_border())
        for l in proc_content:
            lines.append(proc_box.wrap_inner_line(l))
        lines.append(proc_box.render_bottom_border())

        return lines[:height]

    def _build_cpu_content(self, inner_w: int, inner_h: int, data: Dict, theme: Theme) -> List[str]:
        lines = []
        cpu = data["cpu"]

        # Allocate space: top graph, bottom cluster summary
        graph_h = max(2, inner_h - 2)
        graph_w = max(10, inner_w - 2)

        self.canvas_cpu.resize(graph_w, graph_h)
        self.canvas_cpu.draw_curve(cpu["history"], fill=True, max_val=100.0)
        graph_lines = self.canvas_cpu.render_rows(color_func=theme.cpu_color)

        for gl in graph_lines:
            lines.append(f" {gl}")

        # Cluster breakdown row
        cluster_parts = []
        for cl in cpu["clusters"]:
            c_color = theme.cpu_color(cl["usage_pct"] / 100.0)
            c_name = cl["name"].split()[0]  # e.g. "Little", "Big", "Prime"
            cluster_parts.append(f"{theme.dim_ansi()}{c_name}:\033[0m{c_color}{cl['usage_pct']:>3.0f}%\033[0m")
        lines.append(" " + "  ".join(cluster_parts))

        # Overall frequency meter row
        if len(lines) < inner_h and cpu["cores"]:
            avg_mhz = sum(c["mhz"] for c in cpu["cores"]) // len(cpu["cores"])
            bar = ProgressBar.render(cpu["overall_pct"], max(10, inner_w - 24), color_func=theme.cpu_color)
            lines.append(f" Avg: {avg_mhz}MHz [{bar}] {cpu['overall_pct']:>4.1f}%")

        while len(lines) < inner_h:
            lines.append("")
        return lines[:inner_h]

    def _build_mem_disk_content(self, inner_w: int, inner_h: int, data: Dict, theme: Theme) -> List[str]:
        lines = []
        mem = data["memory"]

        # RAM Bar
        ram_bar = ProgressBar.render(mem["ram_pct"], max(8, inner_w - 26), color_func=theme.mem_color)
        lines.append(f" RAM  [{ram_bar}] {mem['ram_used_mb']/1024:.1f}/{mem['ram_total_mb']/1024:.1f}GB {mem['ram_pct']:>3.0f}%")

        # ZRAM Bar
        swap_bar = ProgressBar.render(mem["swap_pct"], max(8, inner_w - 26), color_func=theme.mem_color)
        lines.append(f" ZRAM [{swap_bar}] {mem['swap_used_mb']/1024:.1f}/{mem['swap_total_mb']/1024:.1f}GB {mem['swap_pct']:>3.0f}%")

        # Storage Partitions
        if len(lines) < inner_h:
            lines.append(f"{theme.dim_ansi()} ─── Storage Partitions ───\033[0m")

        for disk in data["storage"]:
            if len(lines) >= inner_h:
                break
            d_bar = ProgressBar.render(disk["used_pct"], max(6, inner_w - 28), color_func=theme.cpu_color)
            label = disk["label"].split()[0]
            lines.append(f" {label:<7} [{d_bar}] {disk['used_gb']:.0f}/{disk['total_gb']:.0f}G {disk['used_pct']:>3.0f}%")

        while len(lines) < inner_h:
            lines.append("")
        return lines[:inner_h]

    def _build_bat_thermal_content(self, inner_w: int, inner_h: int, data: Dict, theme: Theme) -> List[str]:
        lines = []
        bat = data["battery"]
        therm = data["thermal"]

        # Battery Bar
        bat_color = theme.battery_color(bat["level"] / 100.0)
        bat_bar = ProgressBar.render(bat["level"], max(8, inner_w - 22), color_func=theme.battery_color)
        lines.append(f" Bat [{bat_bar}] {bat_color}{bat['level']:>3.0f}%\033[0m {bat['status']}")

        # Battery Details
        lines.append(f" {theme.dim_ansi()}Volt:\033[0m {bat['voltage']:.2f}V  {theme.dim_ansi()}Temp:\033[0m {bat['temperature']:.1f}°C  {theme.dim_ansi()}Cycles:\033[0m {bat['cycles']}")

        # Thermal Highlights
        shell_col = theme.temp_color(min(1.0, therm["max_shell"] / 50.0))
        cpu_col = theme.temp_color(min(1.0, therm["max_cpu"] / 70.0))
        lines.append(f" Skin: {shell_col}{therm['max_shell']:.1f}°C\033[0m  CPU: {cpu_col}{therm['max_cpu']:.1f}°C\033[0m  GPU: {therm['gpu_temp']:.1f}°C")

        while len(lines) < inner_h:
            lines.append("")
        return lines[:inner_h]

    def _build_proc_content(self, inner_w: int, inner_h: int, data: Dict, theme: Theme) -> List[str]:
        lines = []
        procs = data["processes"]

        # Table Header
        hdr = f" {theme.dim_ansi()}{'PID':<6} {'USER':<7} {'CPU%':>6} {'RSS':>7}  {'COMMAND'}\033[0m"
        lines.append(hdr)

        avail_rows = inner_h - 1
        for p in procs[:avail_rows]:
            cmd = p.cmdline if len(p.cmdline) < inner_w - 30 else p.cmdline[:inner_w - 33] + "..."
            cpu_c = theme.cpu_color(min(1.0, p.cpu_pct / 50.0))
            line = f" {p.pid:<6} {p.user[:7]:<7} {cpu_c}{p.cpu_pct:>5.1f}%\033[0m {p.rss_mb:>6.1f}M  {cmd}"
            lines.append(line)

        while len(lines) < inner_h:
            lines.append("")
        return lines[:inner_h]

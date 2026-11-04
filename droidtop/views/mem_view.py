"""
DroidTop - Detailed Memory, Android ZRAM Swap, and Storage Inspector.
"""

from typing import List, Dict
from .base import BaseView
from ..themes.palette import Theme
from ..terminal.box import Box
from ..terminal.canvas import BrailleCanvas, ProgressBar


class MemoryView(BaseView):
    """Detailed RAM, ZRAM compressed swap, and disk storage inspector."""

    def __init__(self):
        super().__init__("memory", "[3] Mem & Disk")
        self.canvas_ram = BrailleCanvas(30, 5)
        self.canvas_swap = BrailleCanvas(30, 5)

    def render(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        mem = data["memory"]
        lines = []

        box = Box(
            0, 0, width, height,
            title="MEMORY & STORAGE",
            badge_right=f"RAM: {mem['ram_pct']:.0f}%  ZRAM: {mem['swap_pct']:.0f}%",
            border_ansi=theme.border_ansi(True),
            title_ansi=theme.title_ansi(),
        )
        lines.append(box.render_top_border())

        inner_w = box.inner_w
        inner_h = box.inner_h
        content = []

        # 1. RAM & ZRAM Gauges
        r_bar = ProgressBar.render(mem["ram_pct"], max(10, inner_w - 32), color_func=theme.mem_color)
        s_bar = ProgressBar.render(mem["swap_pct"], max(10, inner_w - 32), color_func=theme.mem_color)

        content.append(f" RAM  [{r_bar}] {mem['ram_used_mb']/1024:.2f} / {mem['ram_total_mb']/1024:.2f} GB ({mem['ram_pct']:>5.1f}%)")
        content.append(f" ZRAM [{s_bar}] {mem['swap_used_mb']/1024:.2f} / {mem['swap_total_mb']/1024:.2f} GB ({mem['swap_pct']:>5.1f}%)")

        # 2. Braille History Graph
        graph_h = max(3, min(6, inner_h // 4))
        graph_w = max(10, inner_w - 2)

        self.canvas_ram.resize(graph_w, graph_h)
        self.canvas_ram.draw_curve(mem["ram_history"], fill=True, max_val=100.0)

        for gl in self.canvas_ram.render_rows(color_func=theme.mem_color):
            content.append(f" {gl}")

        # 3. Memory Subsystem Breakdown
        content.append(f"{theme.dim_ansi()} ─── Memory Subsystem Breakdown (/proc/meminfo) ───\033[0m")
        col1 = f" Free: {mem['ram_free_mb']:.0f} MB"
        col2 = f" Available: {mem['ram_avail_mb']:.0f} MB"
        col3 = f" Cached: {mem['ram_cached_mb']:.0f} MB"
        content.append(f" {col1:<20} │ {col2:<22} │ {col3}")

        col4 = f" Buffers: {mem['ram_buffers_mb']:.0f} MB"
        col5 = f" Active: {mem['ram_active_mb']:.0f} MB"
        col6 = f" Dirty: {mem['ram_dirty_mb']:.1f} MB"
        content.append(f" {col4:<20} │ {col5:<22} │ {col6}")

        # 4. Storage Partitions
        content.append(f"{theme.dim_ansi()} ─── Storage Partitions & Mountpoints ───\033[0m")
        for disk in data["storage"]:
            if len(content) >= inner_h:
                break
            d_bar = ProgressBar.render(disk["used_pct"], max(8, inner_w - 40), color_func=theme.cpu_color)
            content.append(
                f" {disk['label']:<22} [{d_bar}] {disk['used_gb']:>5.1f} / {disk['total_gb']:<5.1f} GB ({disk['used_pct']:>5.1f}%)"
            )

        for line in content[:inner_h]:
            lines.append(box.wrap_inner_line(line))

        while len(lines) < height - 1:
            lines.append(box.render_empty_line())

        lines.append(box.render_bottom_border())
        return lines[:height]

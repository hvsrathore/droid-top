"""
DroidTop - Interactive Process Manager View.
Supports interactive selection, search filter, column sorting, kill confirmation, and touch scrolling.
"""

from typing import List, Dict, Optional
import signal
from .base import BaseView
from ..themes.palette import Theme
from ..terminal.box import Box
from ..terminal.input import MouseEvent


class ProcessView(BaseView):
    """Interactive Process Manager View."""

    def __init__(self, process_collector):
        super().__init__("process", "[6] Processes")
        self.collector = process_collector
        self.selected_idx = 0
        self.scroll_offset = 0
        self.is_filtering = False
        self.filter_buffer = ""
        self.confirm_kill_pid: Optional[int] = None
        self.status_msg = ""
        self.status_is_error = False

    def handle_key(self, key: str) -> bool:
        """Handle keyboard input for navigation, filtering, and process actions."""
        # 1. Filter input mode
        if self.is_filtering:
            if key == "ENTER":
                self.is_filtering = False
                self.collector.filter_query = self.filter_buffer
                self.selected_idx = 0
                self.scroll_offset = 0
                return True
            elif key == "ESC":
                self.is_filtering = False
                self.filter_buffer = self.collector.filter_query
                return True
            elif key == "BACKSPACE":
                self.filter_buffer = self.filter_buffer[:-1]
                self.collector.filter_query = self.filter_buffer
                self.selected_idx = 0
                return True
            elif len(key) == 1 and key.isprintable():
                self.filter_buffer += key
                self.collector.filter_query = self.filter_buffer
                self.selected_idx = 0
                return True
            return True

        # 2. Confirmation modal mode
        if self.confirm_kill_pid is not None:
            if key in ("y", "Y"):
                ok, msg = self.collector.send_signal(self.confirm_kill_pid, signal.SIGKILL)
                self.status_msg = msg
                self.status_is_error = not ok
                self.confirm_kill_pid = None
                return True
            else:
                self.status_msg = "Kill cancelled"
                self.status_is_error = False
                self.confirm_kill_pid = None
                return True

        # 3. Normal view navigation
        if key in ("UP", "k"):
            if self.selected_idx > 0:
                self.selected_idx -= 1
            return True
        elif key in ("DOWN", "j"):
            self.selected_idx += 1
            return True
        elif key == "PAGE_UP":
            self.selected_idx = max(0, self.selected_idx - 10)
            return True
        elif key == "PAGE_DOWN":
            self.selected_idx += 10
            return True
        elif key == "HOME":
            self.selected_idx = 0
            self.scroll_offset = 0
            return True
        elif key == "END":
            self.selected_idx = 999999
            return True
        elif key == "s":
            self.collector.cycle_sort()
            self.status_msg = f"Sorted by {self.collector.sort_by}"
            self.status_is_error = False
            return True
        elif key == "r":
            self.collector.toggle_sort_direction()
            arrow = "▼" if self.collector.sort_desc else "▲"
            self.status_msg = f"Sort order: {arrow}"
            self.status_is_error = False
            return True
        elif key == "/":
            self.is_filtering = True
            self.filter_buffer = self.collector.filter_query
            return True
        elif key in ("c", "C") and self.collector.filter_query:
            self.collector.filter_query = ""
            self.filter_buffer = ""
            self.status_msg = "Filter cleared"
            self.status_is_error = False
            return True

        # Process signals
        procs = self.collector.update()
        if 0 <= self.selected_idx < len(procs):
            sel_proc = procs[self.selected_idx]
            if key == "k" or key == "DELETE":
                self.confirm_kill_pid = sel_proc.pid
                return True
            elif key == "t":
                ok, msg = self.collector.send_signal(sel_proc.pid, signal.SIGTERM)
                self.status_msg = msg
                self.status_is_error = not ok
                return True
            elif key == "i":
                ok, msg = self.collector.send_signal(sel_proc.pid, signal.SIGINT)
                self.status_msg = msg
                self.status_is_error = not ok
                return True
            elif key == "h":
                ok, msg = self.collector.send_signal(sel_proc.pid, signal.SIGHUP)
                self.status_msg = msg
                self.status_is_error = not ok
                return True

        return False

    def handle_mouse(self, event: MouseEvent, view_top: int) -> bool:
        """Handle tap selection, scroll wheel, and clicks."""
        if event.is_scroll_up:
            self.selected_idx = max(0, self.selected_idx - 3)
            return True
        elif event.is_scroll_down:
            self.selected_idx += 3
            return True
        elif event.is_left_click:
            # Check if row click inside table
            row = event.y - view_top - 3  # subtract header rows
            if row >= 0:
                self.selected_idx = self.scroll_offset + row
                return True
        return False

    def render(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        procs = data["processes"]
        n_procs = len(procs)

        # Clamp selection index
        if n_procs > 0:
            self.selected_idx = max(0, min(self.selected_idx, n_procs - 1))
        else:
            self.selected_idx = 0

        # Sort indicator
        sort_arrow = "▼" if self.collector.sort_desc else "▲"
        sort_badge = f"Sort: {self.collector.sort_by} {sort_arrow}"

        box = Box(
            0, 0, width, height,
            title="PROCESS MANAGER",
            badge_right=sort_badge,
            border_ansi=theme.border_ansi(True),
            title_ansi=theme.title_ansi(),
        )
        lines = []
        lines.append(box.render_top_border())

        inner_w = box.inner_w
        inner_h = box.inner_h
        content = []

        # 1. Filter / Status Bar
        filter_str = f"Filter: '{self.filter_buffer}_'" if self.is_filtering else (f"Filter: '{self.collector.filter_query}' [c:Clear]" if self.collector.filter_query else "[/ to search]")
        mode_badge = f"{theme.danger_ansi()}[ROOT]\033[0m" if self.collector.is_root else f"{theme.dim_ansi()}[USER]\033[0m"
        count_str = f"Selected: {self.selected_idx + 1}/{n_procs}" if n_procs > 0 else "0 procs"

        top_bar = f" {mode_badge}  {theme.highlight_ansi()}{filter_str}\033[0m  │  {count_str}"
        content.append(top_bar)

        # 2. Table Column Header
        hdr = (
            f" {theme.title_ansi()}"
            f"{'PID':<7} {'USER':<8} {'THR':>3} {'S':^3} {'RSS':>8} {'CPU%':>7} {'MEM%':>6}  {'COMMAND'}"
            f"\033[0m"
        )
        content.append(hdr)

        # 3. Process Rows with Viewport Scrolling
        table_rows_avail = max(1, inner_h - 3)  # reserve top bar, hdr, and bottom status

        # Keep selected row visible
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + table_rows_avail:
            self.scroll_offset = self.selected_idx - table_rows_avail + 1

        visible_procs = procs[self.scroll_offset:self.scroll_offset + table_rows_avail]

        for i, p in enumerate(visible_procs):
            actual_idx = self.scroll_offset + i
            is_selected = (actual_idx == self.selected_idx)

            cmd_max = max(10, inner_w - 42)
            cmd_display = p.cmdline if len(p.cmdline) <= cmd_max else p.cmdline[:cmd_max - 3] + "..."

            cpu_c = theme.cpu_color(min(1.0, p.cpu_pct / 50.0))
            mem_c = theme.mem_color(min(1.0, p.mem_pct / 20.0))

            if is_selected:
                # Highlighted row
                bg_col = theme.highlight_ansi()
                row_str = (
                    f" \033[7m{p.pid:<7} {p.user[:8]:<8} {p.threads:>3} {p.state:^3} "
                    f"{p.rss_mb:>7.1f}M {p.cpu_pct:>6.1f}% {p.mem_pct:>5.1f}%  {cmd_display}\033[0m"
                )
            else:
                row_str = (
                    f" {p.pid:<7} {p.user[:8]:<8} {p.threads:>3} {p.state:^3} "
                    f"{p.rss_mb:>7.1f}M {cpu_c}{p.cpu_pct:>6.1f}%\033[0m {mem_c}{p.mem_pct:>5.1f}%\033[0m  {cmd_display}"
                )
            content.append(row_str)

        while len(content) < inner_h - 1:
            content.append("")

        # 4. Bottom Action Bar or Confirmation Prompt
        if self.confirm_kill_pid is not None:
            prompt = f" {theme.danger_ansi()}⚠ KILL PID {self.confirm_kill_pid} with SIGKILL? (y/N)\033[0m"
            content.append(prompt)
        elif self.status_msg:
            s_col = theme.danger_ansi() if self.status_is_error else theme.success_ansi()
            content.append(f" {s_col}{self.status_msg}\033[0m")
        else:
            hint = f" {theme.dim_ansi()}[k] Kill  [t] Term  [s] Sort  [r] Rev  [/] Filter  [j/k] Move\033[0m"
            content.append(hint)

        for line in content[:inner_h]:
            lines.append(box.wrap_inner_line(line))

        while len(lines) < height - 1:
            lines.append(box.render_empty_line())

        lines.append(box.render_bottom_border())
        return lines[:height]

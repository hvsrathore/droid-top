"""
DroidTop - Master Application Controller & Interactive Event Loop.
"""

import sys
import time
import signal
from typing import List, Dict, Optional, Tuple

from .config import Config
from .themes.palette import Theme, THEMES
from .terminal.screen import Screen, visible_len, slice_ansi
from .terminal.input import InputReader, MouseEvent, RawTerminal
from .collectors.system import SystemCollector
from .collectors.cpu import CPUCollector
from .collectors.memory import MemoryCollector
from .collectors.battery import BatteryCollector
from .collectors.thermal import ThermalCollector
from .collectors.storage import StorageCollector
from .collectors.network import NetworkCollector
from .collectors.process import ProcessCollector
from .views.overview import OverviewView
from .views.cpu_view import CPUView
from .views.mem_view import MemoryView
from .views.power_view import PowerView
from .views.thermal_view import ThermalView
from .views.proc_view import ProcessView
from .views.help_modal import HelpModal
from .views.theme_modal import ThemeModal


class DroidTopApp:
    """Master application controller."""

    VERSION = "1.0.0"

    def __init__(self):
        self.config = Config()
        self.screen = Screen()
        self.input_reader = InputReader()

        # Theme
        theme_name = self.config.get("theme", "btop")
        self.theme: Theme = THEMES.get(theme_name, THEMES["btop"])

        # Collectors
        self.sys_collector = SystemCollector()
        self.cpu_collector = CPUCollector()
        self.mem_collector = MemoryCollector()
        self.bat_collector = BatteryCollector()
        self.thermal_collector = ThermalCollector()
        self.storage_collector = StorageCollector()
        self.net_collector = NetworkCollector()
        self.proc_collector = ProcessCollector()

        # Views
        self.proc_view = ProcessView(self.proc_collector)
        self.views = [
            OverviewView(),
            CPUView(),
            MemoryView(),
            PowerView(),
            ThermalView(),
            self.proc_view,
        ]
        self.active_view_idx = 0

        # Modals
        self.show_help = False
        self.show_theme_modal = False
        self.theme_modal = ThemeModal(self.theme.name)

        # State
        self.is_running = True
        self.is_paused = False
        self.refresh_interval = float(self.config.get("refresh_rate", 1.0))
        self.last_update_time = 0.0
        self.cached_data: Optional[Dict] = None

        # Tab hitboxes for mouse click: list of (start_x, end_x, view_idx)
        self.tab_hitboxes: List[Tuple[int, int, int]] = []

        # Resize flag
        self.needs_resize = False

    def setup_signals(self):
        """Set up SIGWINCH terminal resize and exit handlers."""
        def handle_resize(signum, frame):
            self.needs_resize = True

        def handle_exit(signum, frame):
            self.is_running = False

        try:
            signal.signal(signal.SIGWINCH, handle_resize)
            signal.signal(signal.SIGINT, handle_exit)
            signal.signal(signal.SIGTERM, handle_exit)
        except Exception:
            pass

    def collect_data(self) -> Dict:
        """Fetch fresh metrics from all collectors."""
        cpu_data = self.cpu_collector.update()
        mem_data = self.mem_collector.update()
        bat_data = self.bat_collector.update()
        thermal_data = self.thermal_collector.update()
        storage_data = self.storage_collector.update()
        net_data = self.net_collector.update()
        sys_data = self.sys_collector.get_live_stats()
        proc_data = self.proc_collector.update(total_ram_mb=mem_data["ram_total_mb"])

        return {
            "cpu": cpu_data,
            "memory": mem_data,
            "battery": bat_data,
            "thermal": thermal_data,
            "storage": storage_data,
            "network": net_data,
            "system": sys_data,
            "processes": proc_data,
        }

    def render_header(self, width: int, data: Dict) -> str:
        """Render top system header bar."""
        sys_info = data["system"]
        title_part = f" {self.theme.title_ansi()}DROIDTOP v{self.VERSION}\033[0m"
        device_part = f"[{sys_info['brand']} {sys_info['model']} | Android {sys_info['android']} | {sys_info['soc']}]"

        loads = sys_info["loads"]
        stats_part = f"Up: {sys_info['uptime_str']}  Load: {loads[0]:.2f} {loads[1]:.2f} {loads[2]:.2f} "

        avail = width - visible_len(title_part) - visible_len(stats_part) - 2
        mid = f" {self.theme.dim_ansi()}{device_part}\033[0m " if avail >= visible_len(device_part) + 2 else " "

        vlen = visible_len(title_part) + visible_len(mid) + visible_len(stats_part)
        gap = " " * max(0, width - vlen)
        return f"{title_part}{mid}{gap}{stats_part}"

    def render_tabs(self, width: int) -> str:
        """Render interactive navigation tabs with active view highlighted."""
        self.tab_hitboxes.clear()
        parts = [" "]
        cur_x = 1

        for idx, v in enumerate(self.views):
            is_active = (idx == self.active_view_idx)
            raw_title = v.tab_title  # e.g. "[1] Overview"
            t_len = len(raw_title)

            self.tab_hitboxes.append((cur_x, cur_x + t_len, idx))
            cur_x += t_len + 1

            if is_active:
                styled_tab = f"\033[7m{self.theme.highlight_ansi()}{raw_title}\033[0m"
            else:
                styled_tab = f"{self.theme.dim_ansi()}{raw_title}\033[0m"

            parts.append(styled_tab)
            parts.append(" ")

        # Right side indicators
        pause_badge = f"{self.theme.warning_ansi()}[PAUSED]\033[0m " if self.is_paused else ""
        rate_badge = f"{self.theme.dim_ansi()}[{self.refresh_interval:.2f}s]\033[0m "
        theme_badge = f"{self.theme.dim_ansi()}[{self.theme.name}]\033[0m"
        right_str = f"{pause_badge}{rate_badge}{theme_badge} "

        left_str = "".join(parts)
        vleft = visible_len(left_str)
        vright = visible_len(right_str)
        gap = " " * max(0, width - vleft - vright)

        return f"{left_str}{gap}{right_str}"

    def render_footer(self, width: int) -> str:
        """Render bottom quick action bar."""
        actions = [
            ("[1-6]", "Tabs"),
            ("[s]", "Sort"),
            ("[r]", "Rev"),
            ("[/]", "Filter"),
            ("[k]", "Kill"),
            ("[m]", "Theme"),
            ("[?]", "Help"),
            ("[q]", "Quit"),
        ]
        parts = [" "]
        for key, name in actions:
            parts.append(f"{self.theme.title_ansi()}{key}\033[0m {self.theme.dim_ansi()}{name}\033[0m  ")

        left = "".join(parts)
        vleft = visible_len(left)
        gap = " " * max(0, width - vleft)
        return f"{left}{gap}"

    def render_frame(self) -> List[str]:
        """Construct full screen frame."""
        width = self.screen.width
        height = self.screen.height

        if self.cached_data is None:
            self.cached_data = self.collect_data()

        frame = []

        # 1. Header
        frame.append(self.render_header(width, self.cached_data))

        # 2. Tabs
        frame.append(self.render_tabs(width))

        # 3. Active View Content
        view_h = max(4, height - 3)
        active_view = self.views[self.active_view_idx]
        view_lines = active_view.render(width, view_h, self.cached_data, self.theme)

        for line in view_lines[:view_h]:
            frame.append(line)

        while len(frame) < height - 1:
            frame.append(" " * width)

        # 4. Footer
        frame.append(self.render_footer(width))

        # 5. Overlays
        if self.show_help:
            frame = HelpModal.overlay_on_frame(frame, width, height, self.theme)
        elif self.show_theme_modal:
            frame = self.theme_modal.overlay_on_frame(frame, width, height, self.theme)

        return frame

    def run(self):
        """Main event loop."""
        self.setup_signals()

        with RawTerminal(), self.screen:
            # Initial collection and draw
            self.cached_data = self.collect_data()
            self.last_update_time = time.time()
            self.screen.flush(self.render_frame())

            while self.is_running:
                now = time.time()

                # Handle resize
                if self.needs_resize:
                    self.screen.update_size()
                    self.needs_resize = False
                    self.screen.flush(self.render_frame())

                # Non-blocking input read
                event = self.input_reader.read_event(timeout=0.05)

                if event is not None:
                    self._handle_input(event)
                    self.screen.flush(self.render_frame())

                # Check periodic refresh
                if not self.is_paused and (now - self.last_update_time >= self.refresh_interval):
                    self.cached_data = self.collect_data()
                    self.last_update_time = now
                    self.screen.flush(self.render_frame())

    def _handle_input(self, event):
        """Route keyboard and mouse events."""
        # 1. Mouse Event
        if isinstance(event, MouseEvent):
            self._handle_mouse(event)
            return

        # 2. Keyboard Event
        key = event

        # Help modal open
        if self.show_help:
            if key in ("ESC", "?", "F1", "ENTER", "SPACE", "q"):
                self.show_help = False
            return

        # Theme modal open
        if self.show_theme_modal:
            consumed, chosen = self.theme_modal.handle_key(key)
            if chosen == "CANCEL":
                self.show_theme_modal = False
            elif chosen and chosen in THEMES:
                self.theme = THEMES[chosen]
                self.config.set("theme", chosen)
                self.show_theme_modal = False
            return

        # Global Hotkeys
        if key == "CTRL_C" or (key == "q" and not (self.active_view_idx == 5 and self.proc_view.is_filtering)):
            self.is_running = False
            return

        # Tab Switching
        if key in ("1", "2", "3", "4", "5", "6") and not (self.active_view_idx == 5 and self.proc_view.is_filtering):
            idx = int(key) - 1
            if 0 <= idx < len(self.views):
                self.active_view_idx = idx
            return

        if key == "TAB" or key == "RIGHT":
            if not (self.active_view_idx == 5 and self.proc_view.is_filtering):
                self.active_view_idx = (self.active_view_idx + 1) % len(self.views)
                return

        if key == "SHIFT_TAB" or key == "LEFT":
            if not (self.active_view_idx == 5 and self.proc_view.is_filtering):
                self.active_view_idx = (self.active_view_idx - 1) % len(self.views)
                return

        # Modals
        if key in ("?", "F1") and not (self.active_view_idx == 5 and self.proc_view.is_filtering):
            self.show_help = True
            return

        if key in ("m", "F2") and not (self.active_view_idx == 5 and self.proc_view.is_filtering):
            self.show_theme_modal = True
            self.theme_modal.selected_idx = ThemeModal.THEME_KEYS.index(self.theme.name) if self.theme.name in ThemeModal.THEME_KEYS else 0
            return

        # Refresh Speed & Pause
        if key == "+" or key == "=":
            self.refresh_interval = max(0.25, round(self.refresh_interval - 0.25, 2))
            self.config.set("refresh_rate", self.refresh_interval)
            return

        if key == "-":
            self.refresh_interval = min(5.0, round(self.refresh_interval + 0.25, 2))
            self.config.set("refresh_rate", self.refresh_interval)
            return

        if key == "p" and not (self.active_view_idx == 5 and self.proc_view.is_filtering):
            self.is_paused = not self.is_paused
            return

        # Delegate to active view
        self.views[self.active_view_idx].handle_key(key)

    def _handle_mouse(self, event: MouseEvent):
        """Handle mouse taps and scrolls."""
        if self.show_help:
            if event.is_left_click:
                self.show_help = False
            return

        if self.show_theme_modal:
            box_h = len(ThemeModal.THEME_KEYS) + 4
            box_y = (self.screen.height - box_h) // 2
            consumed, chosen = self.theme_modal.handle_mouse(event, box_y)
            if chosen and chosen in THEMES:
                self.theme = THEMES[chosen]
                self.config.set("theme", chosen)
                self.show_theme_modal = False
            return

        # Line 1: Tabs click
        if event.y == 1 and event.is_left_click:
            for start_x, end_x, v_idx in self.tab_hitboxes:
                if start_x <= event.x < end_x:
                    self.active_view_idx = v_idx
                    return

        # Line Height - 1: Footer buttons
        if event.y == self.screen.height - 1 and event.is_left_click:
            # Check help or quit
            if event.x >= self.screen.width - 12:
                self.is_running = False
            elif event.x >= self.screen.width - 24:
                self.show_help = True
            return

        # Delegate to view
        self.views[self.active_view_idx].handle_mouse(event, view_top=2)

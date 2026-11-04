"""
DroidTop - Interactive Theme Switcher Modal Overlay.
"""

from typing import List, Tuple, Optional
from ..themes.palette import Theme, THEMES
from ..terminal.box import Box
from ..terminal.screen import visible_len, slice_visible_range
from ..terminal.input import MouseEvent


class ThemeModal:
    """Centered pop-up overlay to select among TrueColor themes with live swatches."""

    THEME_KEYS = ["btop", "oled", "cyberpunk", "dracula", "nord", "gruvbox", "matrix", "monokai"]

    def __init__(self, current_theme_name: str = "btop"):
        self.selected_idx = 0
        if current_theme_name in self.THEME_KEYS:
            self.selected_idx = self.THEME_KEYS.index(current_theme_name)

    def handle_key(self, key: str) -> Tuple[bool, Optional[str]]:
        """
        Handle key.
        Returns (consumed, selected_theme_name or None if still choosing).
        """
        if key in ("UP", "k"):
            self.selected_idx = (self.selected_idx - 1) % len(self.THEME_KEYS)
            return (True, None)
        elif key in ("DOWN", "j"):
            self.selected_idx = (self.selected_idx + 1) % len(self.THEME_KEYS)
            return (True, None)
        elif key in ("ENTER", "SPACE"):
            return (True, self.THEME_KEYS[self.selected_idx])
        elif key in ("ESC", "q", "m"):
            return (True, "CANCEL")
        return (False, None)

    def handle_mouse(self, event: MouseEvent, box_y: int) -> Tuple[bool, Optional[str]]:
        if event.is_left_click:
            row = event.y - box_y - 2
            if 0 <= row < len(self.THEME_KEYS):
                self.selected_idx = row
                return (True, self.THEME_KEYS[self.selected_idx])
        return (False, None)

    def overlay_on_frame(self, frame: List[str], width: int, height: int, active_theme: Theme) -> List[str]:
        box_w = min(56, max(36, width - 6))
        box_h = len(self.THEME_KEYS) + 4

        box_x = (width - box_w) // 2
        box_y = (height - box_h) // 2

        modal = Box(
            box_x, box_y, box_w, box_h,
            title="THEME SELECTOR",
            badge_right="[Enter: Select]",
            border_ansi=active_theme.highlight_ansi(),
            title_ansi=active_theme.title_ansi(),
        )

        modal_lines = []
        modal_lines.append(modal.render_top_border())
        modal_lines.append(modal.wrap_inner_line(f" {active_theme.dim_ansi()}Use Up/Down or click to choose theme:\033[0m"))

        for i, t_key in enumerate(self.THEME_KEYS):
            thm = THEMES[t_key]
            is_active = (i == self.selected_idx)

            # Build color swatch bar
            c1 = thm.cpu_color(0.0)
            c2 = thm.cpu_color(0.5)
            c3 = thm.cpu_color(1.0)
            c4 = thm.mem_color(0.5)
            swatch = f"{c1}█{c2}█{c3}█{c4}█\033[0m"

            cursor = "▶ " if is_active else "  "
            line_str = f" {cursor}{thm.display_name:<28} {swatch}"
            if is_active:
                line_str = f" \033[7m{cursor}{thm.display_name:<28} {swatch}\033[0m"

            modal_lines.append(modal.wrap_inner_line(line_str))

        modal_lines.append(modal.render_bottom_border(footer_right="[Esc: Cancel]"))

        # Overlay onto frame
        out_frame = list(frame)
        for i, m_line in enumerate(modal_lines):
            target_y = box_y + i
            if 0 <= target_y < len(out_frame):
                orig = out_frame[target_y]
                left_part = slice_visible_range(orig, 0, box_x)
                v_left = visible_len(left_part)
                if v_left < box_x:
                    left_part += " " * (box_x - v_left)

                right_start = box_x + box_w
                right_part = slice_visible_range(orig, right_start, width)

                out_frame[target_y] = f"{left_part}{m_line}{right_part}"

        return out_frame

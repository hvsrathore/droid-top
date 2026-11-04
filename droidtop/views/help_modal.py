"""
DroidTop - Interactive Help & Keyboard Shortcuts Dialog Overlay.
"""

from typing import List
from ..themes.palette import Theme
from ..terminal.box import Box
from ..terminal.screen import visible_len, slice_visible_range


class HelpModal:
    """Centered pop-up overlay detailing all keyboard shortcuts and navigation."""

    HELP_ITEMS = [
        ("Navigation", ""),
        ("1 - 6", "Directly switch tabs (Overview, CPU, Mem, Power, Thermal, Proc)"),
        ("Tab / Shift-Tab", "Cycle through tabs"),
        ("Left / Right", "Cycle through tabs"),
        ("Touch / Click", "Tap any tab or row to switch/select directly"),
        ("", ""),
        ("Process Manager", ""),
        ("j / k or Up / Down", "Move process selection cursor"),
        ("PageUp / PageDn", "Scroll process list by 10 rows"),
        ("s", "Cycle sort column (CPU%, MEM%, PID, NAME, THREADS)"),
        ("r", "Toggle ascending / descending sort order"),
        ("/", "Start real-time process search filter"),
        ("c", "Clear active search filter"),
        ("k / Delete", "Send SIGKILL to selected process (with confirmation)"),
        ("t", "Send SIGTERM (graceful shutdown)"),
        ("i", "Send SIGINT (Ctrl+C interrupt)"),
        ("", ""),
        ("Application Controls", ""),
        ("+ / -", "Increase / decrease refresh rate (0.25s - 5.0s)"),
        ("Space / p", "Pause / resume background updates"),
        ("m / F2", "Open Theme Switcher menu"),
        ("? / F1", "Toggle this Help Dialog"),
        ("q / Ctrl+C", "Quit DroidTop"),
    ]

    @classmethod
    def overlay_on_frame(cls, frame: List[str], width: int, height: int, theme: Theme) -> List[str]:
        """Overlay the modal dialog in the center of the rendered screen frame."""
        box_w = min(74, max(40, width - 6))
        box_h = min(len(cls.HELP_ITEMS) + 4, max(12, height - 4))

        box_x = (width - box_w) // 2
        box_y = (height - box_h) // 2

        modal = Box(
            box_x, box_y, box_w, box_h,
            title="HELP & KEYBOARD SHORTCUTS",
            badge_right="[Press Esc/? to Close]",
            border_ansi=theme.highlight_ansi(),
            title_ansi=theme.title_ansi(),
        )

        modal_lines = []
        modal_lines.append(modal.render_top_border())

        inner_h = modal.inner_h
        for key, desc in cls.HELP_ITEMS[:inner_h]:
            if not desc:
                if key:
                    modal_lines.append(modal.wrap_inner_line(f"{theme.title_ansi()} ─── {key} ───\033[0m"))
                else:
                    modal_lines.append(modal.render_empty_line())
            else:
                line = f"  {theme.highlight_ansi()}{key:<18}\033[0m {desc}"
                modal_lines.append(modal.wrap_inner_line(line))

        while len(modal_lines) < box_h - 1:
            modal_lines.append(modal.render_empty_line())

        modal_lines.append(modal.render_bottom_border(footer_right="DroidTop v1.0"))

        # Stamp modal onto frame
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

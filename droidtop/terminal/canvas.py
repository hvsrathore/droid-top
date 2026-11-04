"""
DroidTop - Braille 2x4 Sub-pixel Canvas, Sparklines, and Progress Bars.
"""

from typing import List, Tuple, Optional, Callable


class BrailleCanvas:
    """
    High-resolution terminal canvas using Unicode Braille Patterns (U+2800..U+28FF).
    Each character cell provides a 2x4 sub-pixel grid.
    """

    DOTS = [
        [0x01, 0x08],  # Row 0 (top)
        [0x02, 0x10],  # Row 1
        [0x04, 0x20],  # Row 2
        [0x40, 0x80],  # Row 3 (bottom)
    ]

    def __init__(self, char_w: int, char_h: int):
        self.cw = max(1, char_w)
        self.ch = max(1, char_h)
        self.pw = self.cw * 2
        self.ph = self.ch * 4
        self.grid = [[0 for _ in range(self.cw)] for _ in range(self.ch)]

    def resize(self, char_w: int, char_h: int):
        """Resize canvas dimensions and re-initialize grid."""
        char_w = max(1, char_w)
        char_h = max(1, char_h)
        self.cw = char_w
        self.ch = char_h
        self.pw = char_w * 2
        self.ph = char_h * 4
        self.grid = [[0 for _ in range(self.cw)] for _ in range(self.ch)]

    def clear(self):
        """Reset all pixels to 0."""
        self.grid = [[0 for _ in range(self.cw)] for _ in range(self.ch)]

    def set_pixel(self, px: int, py: int):
        """
        Turn on pixel at (px, py).
        Origin (0, 0) is at the BOTTOM-LEFT.
        """
        if not (0 <= px < self.pw and 0 <= py < self.ph):
            return
        cx = px // 2
        cy = self.ch - 1 - (py // 4)
        sub_x = px % 2
        sub_y = 3 - (py % 4)
        self.grid[cy][cx] |= self.DOTS[sub_y][sub_x]

    def draw_line(self, x0: int, y0: int, x1: int, y1: int):
        """Bresenham's line algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set_pixel(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def draw_curve(self, values: List[float], fill: bool = True, max_val: float = 100.0):
        """
        Plot series of float values (aligned to right edge).
        values: numbers from 0.0 to max_val.
        fill: whether to fill area below curve.
        """
        if not values:
            return
        # Take at most self.pw points
        data = values[-self.pw:]
        n = len(data)
        if n == 0:
            return

        pts = []
        offset_x = self.pw - n
        max_y = self.ph - 1

        for i, val in enumerate(data):
            x = offset_x + i
            norm = max(0.0, min(1.0, val / max_val if max_val > 0 else 0.0))
            y = int(round(norm * max_y))
            pts.append((x, y))

        if len(pts) == 1:
            self.set_pixel(pts[0][0], pts[0][1])
            if fill:
                for fy in range(pts[0][1]):
                    self.set_pixel(pts[0][0], fy)
            return

        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            self.draw_line(x0, y0, x1, y1)
            if fill:
                # Fill vertical stripe under this segment
                step_x = 1 if x0 < x1 else -1
                cur_x = x0
                while cur_x != x1:
                    t = (cur_x - x0) / (x1 - x0) if x1 != x0 else 0.0
                    curve_y = int(y0 + (y1 - y0) * t)
                    for fy in range(curve_y):
                        self.set_pixel(cur_x, fy)
                    cur_x += step_x
                for fy in range(y1):
                    self.set_pixel(x1, fy)

    def render_rows(self, color_func: Optional[Callable[[float], str]] = None) -> List[str]:
        """
        Render canvas into list of self.ch strings.
        color_func: optional callback receiving normalized height t in [0.0..1.0] (0 = bottom, 1 = top),
                    returning an ANSI color string.
        """
        lines = []
        for r in range(self.ch):
            # t: 1.0 at row 0 (top), 0.0 at bottom row
            t = (self.ch - 1 - r) / (self.ch - 1) if self.ch > 1 else 0.5
            color = color_func(t) if color_func else ""
            reset = "\033[0m" if color else ""
            chars = [chr(0x2800 + self.grid[r][c]) for c in range(self.cw)]
            lines.append(f"{color}{''.join(chars)}{reset}")
        return lines


class Sparkline:
    """Renders compact horizontal sparkline text graphs ( ▂▃▄▅▆▇█)."""

    BARS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    @classmethod
    def render(
        cls,
        values: List[float],
        width: int,
        max_val: float = 100.0,
        color_func: Optional[Callable[[float], str]] = None,
    ) -> str:
        """Render values into a sparkline of exact character width."""
        if width <= 0:
            return ""
        if not values:
            return " " * width

        data = values[-width:]
        if len(data) < width:
            data = [0.0] * (width - len(data)) + data

        out = []
        for val in data:
            norm = max(0.0, min(1.0, val / max_val if max_val > 0 else 0.0))
            idx = int(round(norm * (len(cls.BARS) - 1)))
            char = cls.BARS[idx]
            if color_func:
                color = color_func(norm)
                out.append(f"{color}{char}\033[0m")
            else:
                out.append(char)
        return "".join(out)


class ProgressBar:
    """Renders smooth or segmented progress meters."""

    @classmethod
    def render(
        cls,
        percent: float,
        width: int,
        color_func: Optional[Callable[[float], str]] = None,
        style: str = "smooth",  # "smooth" or "blocks"
    ) -> str:
        """Render a progress bar of total character length width."""
        if width <= 0:
            return ""
        p = max(0.0, min(100.0, percent))
        t = p / 100.0
        color = color_func(t) if color_func else ""
        reset = "\033[0m" if color else ""

        if style == "blocks":
            fill_chars = int(round(t * width))
            bar = "█" * fill_chars + "░" * (width - fill_chars)
            return f"{color}{bar}{reset}"

        # Smooth fractional blocks
        sub_blocks = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉"]
        full_blocks = int(t * width)
        frac = (t * width) - full_blocks
        sub_idx = int(round(frac * (len(sub_blocks) - 1)))
        sub_char = sub_blocks[sub_idx] if sub_idx > 0 and (full_blocks < width) else ""
        empty_len = width - full_blocks - (1 if sub_char else 0)
        empty_bars = " " * max(0, empty_len)

        return f"{color}{'█' * full_blocks}{sub_char}{reset}\033[90m{empty_bars}{reset}"

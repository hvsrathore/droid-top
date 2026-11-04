"""
DroidTop - Box drawing and UI pane container.
Provides rounded borders, embedded titles, right badges, and inner layout.
"""

from typing import List, Optional
from .screen import visible_len, slice_ansi


class Box:
    """Represents a UI bordered pane."""

    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        title: str = "",
        badge_right: str = "",
        border_ansi: str = "",
        title_ansi: str = "",
        rounded: bool = True,
    ):
        self.x = x
        self.y = y
        self.w = max(4, w)
        self.h = max(3, h)
        self.title = title
        self.badge_right = badge_right
        self.border_ansi = border_ansi
        self.title_ansi = title_ansi
        self.rounded = rounded

    @property
    def inner_w(self) -> int:
        return max(0, self.w - 2)

    @property
    def inner_h(self) -> int:
        return max(0, self.h - 2)

    def render_top_border(self) -> str:
        """Render top border line with title and optional right badge."""
        tl = "╭" if self.rounded else "┌"
        tr = "╮" if self.rounded else "┐"
        hl = "─"
        reset = "\033[0m"

        # Calculate space for title and badge
        inner_space = self.w - 2  # space between tl and tr
        if inner_space <= 0:
            return f"{self.border_ansi}{tl}{tr}{reset}"

        title_str = ""
        if self.title:
            title_str = f" {self.title_ansi}{self.title}{reset}{self.border_ansi} "
        title_len = visible_len(title_str)

        badge_str = ""
        if self.badge_right:
            badge_str = f" {self.badge_right}{reset}{self.border_ansi} "
        badge_len = visible_len(badge_str)

        remaining = inner_space - title_len - badge_len
        if remaining < 0:
            # Truncate title to fit
            title_str = ""
            title_len = 0
            badge_str = ""
            badge_len = 0
            remaining = inner_space

        left_hl_len = 1
        right_hl_len = max(0, remaining - left_hl_len)

        line = (
            f"{self.border_ansi}{tl}"
            f"{hl * left_hl_len}"
            f"{title_str}"
            f"{hl * right_hl_len}"
            f"{badge_str}"
            f"{tr}{reset}"
        )
        return line

    def render_bottom_border(self, footer_left: str = "", footer_right: str = "") -> str:
        """Render bottom border line with optional footer labels."""
        bl = "╰" if self.rounded else "└"
        br = "╯" if self.rounded else "┘"
        hl = "─"
        reset = "\033[0m"

        inner_space = self.w - 2
        fleft = f" {footer_left} " if footer_left else ""
        fright = f" {footer_right} " if footer_right else ""

        fl_len = visible_len(fleft)
        fr_len = visible_len(fright)
        remaining = inner_space - fl_len - fr_len

        if remaining < 0:
            fleft = ""
            fright = ""
            remaining = inner_space

        mid_len = max(0, remaining)
        line = (
            f"{self.border_ansi}{bl}"
            f"{fleft}"
            f"{hl * mid_len}"
            f"{fright}"
            f"{br}{reset}"
        )
        return line

    def wrap_inner_line(self, content: str) -> str:
        """Enclose content between left and right borders of the box."""
        vl = "│"
        reset = "\033[0m"
        vlen = visible_len(content)
        pad = " " * max(0, self.inner_w - vlen)
        clipped = slice_ansi(content, self.inner_w) if vlen > self.inner_w else content
        return f"{self.border_ansi}{vl}{reset}{clipped}{pad}{self.border_ansi}{vl}{reset}"

    def render_empty_line(self) -> str:
        """Render an empty line enclosed by borders."""
        return self.wrap_inner_line("")

"""
DroidTop - Screen Buffer and Terminal Rendering Engine.
Handles double-buffering, clipping, cursor management, and ANSI TrueColor.
"""

import sys
import shutil
import re
import atexit
from typing import List, Tuple, Optional


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def visible_len(text: str) -> int:
    """Return the visible length of a string ignoring ANSI escape codes."""
    return len(ANSI_ESCAPE_RE.sub("", text))


def slice_visible_range(line: str, start_col: int, end_col: int) -> str:
    """Extract slice of string between start_col and end_col visible columns, preserving ANSI codes."""
    if end_col <= start_col:
        return ""
    cur_col = 0
    res = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "\x1b":
            m = ANSI_ESCAPE_RE.match(line, i)
            if m:
                if cur_col >= start_col and cur_col < end_col:
                    res.append(m.group(0))
                i = m.end()
                continue
        if cur_col >= start_col and cur_col < end_col:
            res.append(line[i])
        cur_col += 1
        i += 1
        if cur_col >= end_col:
            break
    res.append("\033[0m")
    return "".join(res)


def slice_ansi(text: str, max_visible: int) -> str:
    """Slice string so visible characters do not exceed max_visible, preserving ANSI codes."""
    return slice_visible_range(text, 0, max_visible)


class Screen:
    """Terminal Screen Buffer with boundary clipping and flicker-free rendering."""

    def __init__(self):
        self.width = 80
        self.height = 24
        self._buffer: List[str] = [""] * self.height
        self._is_active = False
        self.update_size()

    def set_size(self, w: int, h: int):
        """Manually override size (useful for testing or fixed viewports)."""
        self.width = max(20, w)
        self.height = max(10, h)
        self._buffer = [""] * self.height

    def update_size(self) -> Tuple[int, int]:
        """Query current terminal dimensions."""
        size = shutil.get_terminal_size((self.width, self.height))
        self.width = max(20, size.columns)
        self.height = max(10, size.lines)
        if len(self._buffer) != self.height:
            self._buffer = [""] * self.height
        return (self.width, self.height)

    def enter(self):
        """Initialize alternate screen buffer, mouse tracking, and hide cursor."""
        if self._is_active:
            return
        # Enter alternate screen buffer, hide cursor, clear screen, enable SGR mouse
        # 1000h = normal mouse, 1002h = button motion, 1006h = SGR extended coordinates
        sys.stdout.write(
            "\033[?1049h"       # Alternate screen buffer
            "\033[?25l"         # Hide cursor
            "\033[?1000h"       # Basic mouse tracking
            "\033[?1002h"       # Button event tracking
            "\033[?1006h"       # SGR 1006 extended coordinate mode
            "\033[2J\033[H"     # Clear screen and move to (1,1)
        )
        sys.stdout.flush()
        self._is_active = True
        atexit.register(self.exit)

    def exit(self):
        """Restore terminal to normal state."""
        if not self._is_active:
            return
        # Disable mouse tracking, show cursor, leave alternate screen
        sys.stdout.write(
            "\033[?1006l"
            "\033[?1002l"
            "\033[?1000l"
            "\033[?25h"
            "\033[?1049l"
            "\033[0m"
        )
        sys.stdout.flush()
        self._is_active = False

    def __enter__(self):
        self.enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()

    def clear(self, bg_ansi: str = ""):
        """Clear buffer lines with background style."""
        fill = f"{bg_ansi}{' ' * self.width}\033[0m" if bg_ansi else " " * self.width
        self._buffer = [fill] * self.height

    def print_at(self, x: int, y: int, text: str, max_w: Optional[int] = None):
        """
        Draw string at 0-indexed column x and row y.
        Clips safely inside screen width and height.
        """
        if y < 0 or y >= self.height or x >= self.width:
            return
        # Clip max width to screen boundary
        avail = self.width - x
        if max_w is not None:
            avail = min(avail, max_w)
        if avail <= 0:
            return

        clipped = slice_ansi(text, avail)
        # We overlay this on the row buffer at position x
        row = self._buffer[y]
        # To overlay cleanly, we build a fresh row or slice
        # Since _buffer lines are constructed in render passes, we format per line
        # For simplicity and speed: if row is blank fill, we can position with ANSI cursor
        # Or store row segments. Let us store list of commands per frame!

    def flush(self, frame_content: List[str]):
        """
        Atomically render the full screen frame to terminal.
        frame_content: list of exactly self.height formatted lines.
        """
        output = ["\033[H"]  # Home cursor
        for y, line in enumerate(frame_content[:self.height]):
            # Ensure line length doesn't overflow terminal width
            vlen = visible_len(line)
            if vlen < self.width:
                line = line + (" " * (self.width - vlen))
            elif vlen > self.width:
                line = slice_ansi(line, self.width)
            output.append(line)
            if y < self.height - 1:
                output.append("\r\n")
        output.append("\033[0m")
        sys.stdout.write("".join(output))
        sys.stdout.flush()

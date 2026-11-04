"""
DroidTop - Raw Terminal Input Parser and SGR Mouse Tracker.
"""

import sys
import os
import select
import termios
import tty
import re
from typing import Optional, Union, Tuple


class MouseEvent:
    """Represents a mouse or touch tap event in the terminal."""

    def __init__(self, button: int, x: int, y: int, is_release: bool = False):
        self.button = button
        self.x = x  # 0-indexed column
        self.y = y  # 0-indexed row
        self.is_release = is_release
        self.is_left_click = (button == 0) and not is_release
        self.is_right_click = (button == 2) and not is_release
        self.is_scroll_up = (button == 64)
        self.is_scroll_down = (button == 65)

    def __repr__(self):
        return f"<MouseEvent btn={self.button} x={self.x} y={self.y} rel={self.is_release}>"


# SGR 1006 mouse sequence regex: \033[<btn;col;row(M|m)
SGR_MOUSE_RE = re.compile(r"^\x1b\[<(\d+);(\d+);(\d+)([Mm])")


class RawTerminal:
    """Context manager to place terminal in non-blocking raw mode and restore it."""

    def __init__(self):
        self.old_settings = None

    def __enter__(self):
        if sys.stdin.isatty():
            try:
                self.old_settings = termios.tcgetattr(sys.stdin.fileno())
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass


class InputReader:
    """Reads non-blocking keyboard and mouse events."""

    def __init__(self):
        self._buffer = ""

    def read_event(self, timeout: float = 0.05) -> Optional[Union[str, MouseEvent]]:
        """
        Polls for input with timeout in seconds.
        Returns a key string (e.g. 'UP', 'q', 'ENTER') or a MouseEvent.
        """
        if not self._buffer:
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                try:
                    chunk = os.read(sys.stdin.fileno(), 1024).decode("utf-8", errors="ignore")
                    self._buffer += chunk
                except Exception:
                    return None
            else:
                return None

        if not self._buffer:
            return None

        # Parse buffer
        # 1. Check for SGR mouse event: \x1b[<btn;x;y(M|m)
        m = SGR_MOUSE_RE.match(self._buffer)
        if m:
            btn = int(m.group(1))
            col = int(m.group(2)) - 1  # 1-based to 0-based
            row = int(m.group(3)) - 1
            action = m.group(4)
            is_rel = (action == "m")
            self._buffer = self._buffer[m.end():]
            return MouseEvent(btn, col, row, is_release=is_rel)

        # 2. Check for Escape sequences
        if self._buffer.startswith("\x1b"):
            # Multi-character escape sequences
            seqs = [
                ("\x1b[A", "UP"),
                ("\x1b[B", "DOWN"),
                ("\x1b[C", "RIGHT"),
                ("\x1b[D", "LEFT"),
                ("\x1b[H", "HOME"),
                ("\x1b[F", "END"),
                ("\x1b[1~", "HOME"),
                ("\x1b[4~", "END"),
                ("\x1b[2~", "INSERT"),
                ("\x1b[3~", "DELETE"),
                ("\x1b[5~", "PAGE_UP"),
                ("\x1b[6~", "PAGE_DOWN"),
                ("\x1b[Z", "SHIFT_TAB"),
                ("\x1bOP", "F1"),
                ("\x1bOQ", "F2"),
                ("\x1bOR", "F3"),
                ("\x1bOS", "F4"),
                ("\x1b[15~", "F5"),
                ("\x1b[21~", "F10"),
            ]
            for prefix, name in seqs:
                if self._buffer.startswith(prefix):
                    self._buffer = self._buffer[len(prefix):]
                    return name

            # If starts with \x1b[ but incomplete, wait for rest
            if self._buffer.startswith("\x1b[") or self._buffer.startswith("\x1bO"):
                if len(self._buffer) < 5:
                    # Give it a fraction of a second to get remaining bytes
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.02)
                    if rlist:
                        try:
                            self._buffer += os.read(sys.stdin.fileno(), 1024).decode("utf-8", errors="ignore")
                        except Exception:
                            pass
                        # Re-try match
                        for prefix, name in seqs:
                            if self._buffer.startswith(prefix):
                                self._buffer = self._buffer[len(prefix):]
                                return name
                # Unknown escape sequence, discard the escape prefix
                self._buffer = self._buffer[1:]
                return "ESC"

            # Bare ESC key
            self._buffer = self._buffer[1:]
            return "ESC"

        # 3. Control keys and normal keys
        char = self._buffer[0]
        self._buffer = self._buffer[1:]

        if char == "\r" or char == "\n":
            return "ENTER"
        elif char == "\t":
            return "TAB"
        elif char == "\x7f" or char == "\x08":
            return "BACKSPACE"
        elif char == "\x03":
            return "CTRL_C"
        elif char == " ":
            return "SPACE"

        return char

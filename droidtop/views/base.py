"""
DroidTop - Base View Interface.
"""

from typing import List, Dict, Optional
from ..themes.palette import Theme
from ..terminal.input import MouseEvent


class BaseView:
    """Base class for all DroidTop view screens."""

    def __init__(self, name: str, tab_title: str):
        self.name = name
        self.tab_title = tab_title

    def render(self, width: int, height: int, data: Dict, theme: Theme) -> List[str]:
        """Render the view into exact list of height formatted lines."""
        raise NotImplementedError

    def handle_key(self, key: str) -> bool:
        """Handle key press. Return True if consumed."""
        return False

    def handle_mouse(self, event: MouseEvent, view_top: int) -> bool:
        """Handle mouse event. Return True if consumed."""
        return False

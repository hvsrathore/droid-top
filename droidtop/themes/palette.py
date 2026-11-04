"""
DroidTop - Color themes and styling.
Pure 24-bit TrueColor palettes with smooth gradient interpolation.
"""

from typing import Tuple, List, Dict


def rgb_to_ansi_fg(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit TrueColor foreground sequence."""
    return f"\033[38;2;{r};{g};{b}m"


def rgb_to_ansi_bg(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit TrueColor background sequence."""
    return f"\033[48;2;{r};{g};{b}m"


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex string (e.g. #7aa2f7 or 7aa2f7) to (R, G, B) tuple."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) != 6:
        return (255, 255, 255)
    return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def lerp_rgb(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Linearly interpolate between two RGB colors (t from 0.0 to 1.0)."""
    t = max(0.0, min(1.0, t))
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return (r, g, b)


def multi_gradient(stops: List[Tuple[float, Tuple[int, int, int]]], t: float) -> Tuple[int, int, int]:
    """Interpolate through a list of (position, (r, g, b)) stops."""
    t = max(0.0, min(1.0, t))
    if t <= stops[0][0]:
        return stops[0][1]
    if t >= stops[-1][0]:
        return stops[-1][1]
    for i in range(len(stops) - 1):
        p1, c1 = stops[i]
        p2, c2 = stops[i + 1]
        if p1 <= t <= p2:
            span = p2 - p1
            sub_t = (t - p1) / span if span > 0 else 0.0
            return lerp_rgb(c1, c2, sub_t)
    return stops[-1][1]


class Theme:
    """Represents a UI color theme."""

    def __init__(
        self,
        name: str,
        display_name: str,
        bg: str,
        fg: str,
        border: str,
        border_active: str,
        title: str,
        highlight: str,
        dim: str,
        cpu_stops: List[Tuple[float, str]],
        mem_stops: List[Tuple[float, str]],
        temp_stops: List[Tuple[float, str]],
        battery_stops: List[Tuple[float, str]],
        success: str = "#50fa7b",
        warning: str = "#ffb86c",
        danger: str = "#ff5555",
        info: str = "#8be9fd",
    ):
        self.name = name
        self.display_name = display_name
        self.bg_rgb = hex_to_rgb(bg)
        self.fg_rgb = hex_to_rgb(fg)
        self.border_rgb = hex_to_rgb(border)
        self.border_active_rgb = hex_to_rgb(border_active)
        self.title_rgb = hex_to_rgb(title)
        self.highlight_rgb = hex_to_rgb(highlight)
        self.dim_rgb = hex_to_rgb(dim)

        self.success_rgb = hex_to_rgb(success)
        self.warning_rgb = hex_to_rgb(warning)
        self.danger_rgb = hex_to_rgb(danger)
        self.info_rgb = hex_to_rgb(info)

        # Precompute gradient RGB stops
        self.cpu_stops = [(pos, hex_to_rgb(color)) for pos, color in cpu_stops]
        self.mem_stops = [(pos, hex_to_rgb(color)) for pos, color in mem_stops]
        self.temp_stops = [(pos, hex_to_rgb(color)) for pos, color in temp_stops]
        self.battery_stops = [(pos, hex_to_rgb(color)) for pos, color in battery_stops]

    # Quick ANSI generators
    def fg_ansi(self) -> str:
        return rgb_to_ansi_fg(*self.fg_rgb)

    def bg_ansi(self) -> str:
        return rgb_to_ansi_bg(*self.bg_rgb)

    def border_ansi(self, active: bool = False) -> str:
        return rgb_to_ansi_fg(*(self.border_active_rgb if active else self.border_rgb))

    def title_ansi(self) -> str:
        return rgb_to_ansi_fg(*self.title_rgb)

    def highlight_ansi(self) -> str:
        return rgb_to_ansi_fg(*self.highlight_rgb)

    def dim_ansi(self) -> str:
        return rgb_to_ansi_fg(*self.dim_rgb)

    def success_ansi(self) -> str:
        return rgb_to_ansi_fg(*self.success_rgb)

    def warning_ansi(self) -> str:
        return rgb_to_ansi_fg(*self.warning_rgb)

    def danger_ansi(self) -> str:
        return rgb_to_ansi_fg(*self.danger_rgb)

    def info_ansi(self) -> str:
        return rgb_to_ansi_fg(*self.info_rgb)

    def cpu_color(self, t: float) -> str:
        return rgb_to_ansi_fg(*multi_gradient(self.cpu_stops, t))

    def mem_color(self, t: float) -> str:
        return rgb_to_ansi_fg(*multi_gradient(self.mem_stops, t))

    def temp_color(self, t: float) -> str:
        return rgb_to_ansi_fg(*multi_gradient(self.temp_stops, t))

    def battery_color(self, t: float) -> str:
        return rgb_to_ansi_fg(*multi_gradient(self.battery_stops, t))


# Built-in Themes
THEMES: Dict[str, Theme] = {
    "btop": Theme(
        name="btop",
        display_name="Btop Default",
        bg="#141721",
        fg="#e0e6ed",
        border="#3e4a68",
        border_active="#7aa2f7",
        title="#7aa2f7",
        highlight="#bb9af7",
        dim="#606d88",
        cpu_stops=[(0.0, "#50fa7b"), (0.5, "#ffb86c"), (1.0, "#ff5555")],
        mem_stops=[(0.0, "#8be9fd"), (0.5, "#bd93f9"), (1.0, "#ff79c6")],
        temp_stops=[(0.0, "#8be9fd"), (0.4, "#50fa7b"), (0.7, "#ffb86c"), (1.0, "#ff5555")],
        battery_stops=[(0.0, "#ff5555"), (0.2, "#ffb86c"), (0.6, "#50fa7b"), (1.0, "#8be9fd")],
    ),
    "oled": Theme(
        name="oled",
        display_name="OLED Black (Battery Saver)",
        bg="#000000",
        fg="#ffffff",
        border="#333333",
        border_active="#00e5ff",
        title="#00e5ff",
        highlight="#ff007f",
        dim="#666666",
        cpu_stops=[(0.0, "#00ff66"), (0.5, "#ffea00"), (1.0, "#ff0033")],
        mem_stops=[(0.0, "#00e5ff"), (0.5, "#b388ff"), (1.0, "#ff007f")],
        temp_stops=[(0.0, "#00e5ff"), (0.4, "#00ff66"), (0.7, "#ffea00"), (1.0, "#ff0033")],
        battery_stops=[(0.0, "#ff0033"), (0.2, "#ffea00"), (0.6, "#00ff66"), (1.0, "#00e5ff")],
    ),
    "cyberpunk": Theme(
        name="cyberpunk",
        display_name="Cyberpunk Neon",
        bg="#0d0221",
        fg="#00f0ff",
        border="#541388",
        border_active="#ff007f",
        title="#ffe600",
        highlight="#ff007f",
        dim="#71226e",
        cpu_stops=[(0.0, "#00f0ff"), (0.5, "#ffe600"), (1.0, "#ff007f")],
        mem_stops=[(0.0, "#71226e"), (0.5, "#ff007f"), (1.0, "#00f0ff")],
        temp_stops=[(0.0, "#00f0ff"), (0.4, "#2de2e6"), (0.7, "#ffe600"), (1.0, "#ff007f")],
        battery_stops=[(0.0, "#ff007f"), (0.3, "#ffe600"), (1.0, "#00f0ff")],
    ),
    "dracula": Theme(
        name="dracula",
        display_name="Dracula",
        bg="#282a36",
        fg="#f8f8f2",
        border="#44475a",
        border_active="#bd93f9",
        title="#bd93f9",
        highlight="#ff79c6",
        dim="#6272a4",
        cpu_stops=[(0.0, "#50fa7b"), (0.5, "#f1fa8c"), (1.0, "#ff5555")],
        mem_stops=[(0.0, "#8be9fd"), (0.5, "#bd93f9"), (1.0, "#ff79c6")],
        temp_stops=[(0.0, "#8be9fd"), (0.4, "#50fa7b"), (0.7, "#ffb86c"), (1.0, "#ff5555")],
        battery_stops=[(0.0, "#ff5555"), (0.25, "#ffb86c"), (0.6, "#50fa7b"), (1.0, "#8be9fd")],
    ),
    "nord": Theme(
        name="nord",
        display_name="Nordic Frost",
        bg="#2e3440",
        fg="#eceff4",
        border="#434c5e",
        border_active="#88c0d0",
        title="#88c0d0",
        highlight="#81a1c1",
        dim="#4c566a",
        cpu_stops=[(0.0, "#a3be8c"), (0.5, "#ebcb8b"), (1.0, "#bf616a")],
        mem_stops=[(0.0, "#88c0d0"), (0.5, "#81a1c1"), (1.0, "#b48ead")],
        temp_stops=[(0.0, "#88c0d0"), (0.4, "#a3be8c"), (0.7, "#ebcb8b"), (1.0, "#bf616a")],
        battery_stops=[(0.0, "#bf616a"), (0.25, "#ebcb8b"), (0.6, "#a3be8c"), (1.0, "#88c0d0")],
    ),
    "gruvbox": Theme(
        name="gruvbox",
        display_name="Gruvbox Dark",
        bg="#282828",
        fg="#ebdbb2",
        border="#504945",
        border_active="#fabd2f",
        title="#fabd2f",
        highlight="#fe8019",
        dim="#928374",
        cpu_stops=[(0.0, "#b8bb26"), (0.5, "#fabd2f"), (1.0, "#fb4934")],
        mem_stops=[(0.0, "#83a598"), (0.5, "#d3869b"), (1.0, "#fabd2f")],
        temp_stops=[(0.0, "#83a598"), (0.4, "#b8bb26"), (0.7, "#fabd2f"), (1.0, "#fb4934")],
        battery_stops=[(0.0, "#fb4934"), (0.3, "#fabd2f"), (0.7, "#b8bb26"), (1.0, "#83a598")],
    ),
    "matrix": Theme(
        name="matrix",
        display_name="Matrix Hacker",
        bg="#031405",
        fg="#55ff55",
        border="#0d4a13",
        border_active="#00ff41",
        title="#00ff41",
        highlight="#aaffaa",
        dim="#1b5e20",
        cpu_stops=[(0.0, "#00bb2d"), (0.5, "#aaff00"), (1.0, "#ff5555")],
        mem_stops=[(0.0, "#008820"), (0.5, "#00ff41"), (1.0, "#ccff00")],
        temp_stops=[(0.0, "#00ff41"), (0.5, "#aaff00"), (1.0, "#ff3333")],
        battery_stops=[(0.0, "#ff3333"), (0.3, "#aaff00"), (1.0, "#00ff41")],
    ),
    "monokai": Theme(
        name="monokai",
        display_name="Monokai Pro",
        bg="#221f22",
        fg="#fcfcfa",
        border="#403e41",
        border_active="#a9dc76",
        title="#ffd866",
        highlight="#ff6188",
        dim="#727072",
        cpu_stops=[(0.0, "#a9dc76"), (0.5, "#ffd866"), (1.0, "#ff6188")],
        mem_stops=[(0.0, "#78dce8"), (0.5, "#ab9df2"), (1.0, "#ff6188")],
        temp_stops=[(0.0, "#78dce8"), (0.4, "#a9dc76"), (0.7, "#ffd866"), (1.0, "#ff6188")],
        battery_stops=[(0.0, "#ff6188"), (0.25, "#ffd866"), (0.6, "#a9dc76"), (1.0, "#78dce8")],
    ),
}

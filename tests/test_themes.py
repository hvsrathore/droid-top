"""
Tests for Themes and Color Gradient Engines.
"""

import unittest
from droidtop.themes.palette import THEMES, hex_to_rgb, lerp_rgb, multi_gradient, rgb_to_ansi_fg


class TestThemes(unittest.TestCase):

    def test_hex_to_rgb(self):
        self.assertEqual(hex_to_rgb("#ffffff"), (255, 255, 255))
        self.assertEqual(hex_to_rgb("#000000"), (0, 0, 0))
        self.assertEqual(hex_to_rgb("#ff0000"), (255, 0, 0))

    def test_lerp_rgb(self):
        c1 = (0, 0, 0)
        c2 = (100, 200, 50)
        mid = lerp_rgb(c1, c2, 0.5)
        self.assertEqual(mid, (50, 100, 25))

    def test_themes_exist(self):
        expected = ["btop", "oled", "cyberpunk", "dracula", "nord", "gruvbox", "matrix", "monokai"]
        for k in expected:
            self.assertIn(k, THEMES)
            thm = THEMES[k]
            self.assertTrue(thm.bg_ansi().startswith("\033[48;2;"))
            self.assertTrue(thm.fg_ansi().startswith("\033[38;2;"))
            self.assertTrue(thm.cpu_color(0.5).startswith("\033[38;2;"))


if __name__ == "__main__":
    unittest.main()

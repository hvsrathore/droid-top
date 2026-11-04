"""
Tests for BrailleCanvas, Sparklines, and ProgressBars.
"""

import unittest
from droidtop.terminal.canvas import BrailleCanvas, Sparkline, ProgressBar


class TestBrailleCanvas(unittest.TestCase):

    def test_canvas_dimensions(self):
        canvas = BrailleCanvas(20, 5)
        self.assertEqual(canvas.cw, 20)
        self.assertEqual(canvas.ch, 5)
        self.assertEqual(canvas.pw, 40)
        self.assertEqual(canvas.ph, 20)

    def test_pixel_and_clear(self):
        canvas = BrailleCanvas(10, 4)
        canvas.set_pixel(0, 0)
        lines = canvas.render_rows()
        self.assertEqual(len(lines), 4)
        # origin (0, 0) is bottom-left, dot 3 (0x40)
        self.assertNotEqual(lines[-1][0], "⠀")

        canvas.clear()
        lines_cleared = canvas.render_rows()
        self.assertEqual(lines_cleared[-1][0], "⠀")

    def test_draw_curve(self):
        canvas = BrailleCanvas(15, 4)
        values = [10.0, 30.0, 75.0, 100.0, 50.0]
        canvas.draw_curve(values, fill=True, max_val=100.0)
        lines = canvas.render_rows()
        self.assertEqual(len(lines), 4)
        non_empty = any(c != "⠀" for line in lines for c in line)
        self.assertTrue(non_empty)

    def test_sparkline(self):
        spark = Sparkline.render([0, 25, 50, 75, 100], 5, max_val=100.0)
        self.assertEqual(len(spark), 5)
        self.assertEqual(spark[0], " ")
        self.assertEqual(spark[-1], "█")

    def test_progress_bar(self):
        bar_50 = ProgressBar.render(50.0, 10, style="blocks")
        self.assertIn("█████░░░░░", bar_50)


if __name__ == "__main__":
    unittest.main()

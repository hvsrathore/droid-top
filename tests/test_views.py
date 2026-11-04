"""
Tests for DroidTop Views and Screen Rendering.
"""

import unittest
from droidtop.app import DroidTopApp


class TestViews(unittest.TestCase):

    def setUp(self):
        self.app = DroidTopApp()
        self.data = self.app.collect_data()

    def test_all_views_render(self):
        resolutions = [(80, 24), (100, 30), (60, 20)]
        for w, h in resolutions:
            self.app.screen.set_size(w, h)
            for idx in range(len(self.app.views)):
                self.app.active_view_idx = idx
                frame = self.app.render_frame()
                self.assertEqual(len(frame), h)

    def test_modals_render(self):
        self.app.screen.set_size(80, 24)
        # Help modal
        self.app.show_help = True
        frame_help = self.app.render_frame()
        self.assertEqual(len(frame_help), 24)
        self.app.show_help = False

        # Theme modal
        self.app.show_theme_modal = True
        frame_theme = self.app.render_frame()
        self.assertEqual(len(frame_theme), 24)
        self.app.show_theme_modal = False


if __name__ == "__main__":
    unittest.main()

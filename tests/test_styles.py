"""Style book tests — deterministic picks, palette variation, canvas presets."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyric_short.config import CANVAS_PRESETS, Palette, apply_canvas  # noqa: E402
from lyric_short.styles import (STYLE_NAMES, auto_style, describe, get_style,  # noqa: E402
                                vary)


class TestStyles(unittest.TestCase):
    def test_every_style_builds(self):
        for name in STYLE_NAMES:
            theme = get_style(name)
            self.assertEqual(theme.name, name)
            self.assertEqual(len(theme.palettes), 2)
            self.assertGreater(theme.card_size()[0], 0)

    def test_unknown_style_fails_loudly(self):
        with self.assertRaises(SystemExit):
            get_style("nope")

    def test_palettes_differ(self):
        # a style may reuse one fill (neon is dark glass on both cards) as long as
        # the text colour changes with it
        for name in STYLE_NAMES:
            a, b = get_style(name).palettes
            self.assertTrue(a.fill != b.fill or a.text != b.text,
                            f"{name} renders both cards identically")

    def test_colors_for_kind(self):
        theme = get_style("botanical")
        fill, text, orn = theme.colors_for("a")
        self.assertEqual(fill, theme.palettes[0].fill)
        self.assertEqual(text, theme.palettes[0].text)
        self.assertEqual(orn, theme.palettes[0].orn)
        self.assertEqual(theme.colors_for("b")[0], theme.palettes[1].fill)


class TestAuto(unittest.TestCase):
    def test_auto_is_stable_for_a_seed(self):
        self.assertEqual(auto_style("song-a.mp3").name, auto_style("song-a.mp3").name)

    def test_auto_covers_more_than_one_style(self):
        names = {auto_style(f"track-{i}.mp3").name for i in range(40)}
        self.assertGreater(len(names), 1)

    def test_auto_returns_a_real_style(self):
        for i in range(20):
            self.assertIn(auto_style(f"x{i}").name, STYLE_NAMES)


class TestVary(unittest.TestCase):
    def test_vary_changes_the_palette(self):
        base = get_style("sunset")
        tweaked = vary(base, seed="abc")
        self.assertNotEqual(base.palettes[0].fill, tweaked.palettes[0].fill)
        self.assertEqual(base.name, tweaked.name)

    def test_vary_is_deterministic(self):
        base = get_style("poster")
        self.assertEqual(vary(base, seed="x").palettes[0].fill,
                         vary(base, seed="x").palettes[0].fill)

    def test_vary_keeps_palette_type(self):
        tweaked = vary(get_style("neon"), seed="y")
        self.assertTrue(all(isinstance(p, Palette) for p in tweaked.palettes))


class TestCanvas(unittest.TestCase):
    def test_canvas_presets(self):
        theme = apply_canvas(get_style("botanical"), "landscape")
        self.assertEqual((theme.width, theme.height), (1920, 1080))
        square = apply_canvas(get_style("neon"), "square")
        self.assertEqual((square.width, square.height), (1080, 1080))

    def test_unknown_canvas_fails(self):
        with self.assertRaises(SystemExit):
            apply_canvas(get_style("paper"), "billboard")

    def test_all_presets_exist(self):
        self.assertEqual(set(CANVAS_PRESETS), {"shorts", "landscape", "square"})


class TestDescribe(unittest.TestCase):
    def test_describe_mentions_the_name(self):
        self.assertIn("neon", describe(get_style("neon")))


if __name__ == "__main__":
    unittest.main()

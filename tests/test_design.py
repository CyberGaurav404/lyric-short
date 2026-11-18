"""Design generator tests: determinism, contrast, round-trips, mood handling."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyric_short import design as D  # noqa: E402


class TestGeneration(unittest.TestCase):
    def test_same_seed_and_mood_is_stable(self):
        a = D.generate(seed="song.mp3", mood="warm")
        b = D.generate(seed="song.mp3", mood="warm")
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_different_seeds_differ(self):
        a = D.generate(seed="one.mp3", mood="calm")
        b = D.generate(seed="two.mp3", mood="calm")
        self.assertNotEqual(a.palettes[0].fill, b.palettes[0].fill)

    def test_every_mood_generates(self):
        for mood in D.MOODS:
            spec = D.generate(seed="x", mood=mood)
            self.assertEqual(spec.mood, mood)
            self.assertEqual(len(spec.palettes), 2)

    def test_unknown_mood_fails(self):
        with self.assertRaises(SystemExit):
            D.generate(seed="x", mood="sad")

    def test_generated_text_is_readable(self):
        for mood in D.MOODS:
            for seed in ("a.mp3", "b.mp3", "c.mp3"):
                spec = D.generate(seed=seed, mood=mood)
                for palette in spec.palettes:
                    self.assertGreaterEqual(
                        D.contrast(palette.fill, palette.text), 4.5,
                        f"{mood}/{seed}: {palette.fill} on {palette.text}")

    def test_cards_differ_within_a_design(self):
        spec = D.generate(seed="x.mp3", mood="calm")
        a, b = spec.palettes
        self.assertTrue(a.fill != b.fill or a.text != b.text)


class TestContrast(unittest.TestCase):
    def test_black_on_white_is_high(self):
        self.assertGreater(D.contrast((0, 0, 0), (255, 255, 255)), 20)

    def test_readable_text_picks_light_on_dark(self):
        self.assertGreater(sum(D.readable_text((20, 20, 30))), sum(D.readable_text((240, 240, 240))))


class TestIo(unittest.TestCase):
    def test_round_trip_dict(self):
        spec = D.generate(seed="rt.mp3", mood="bold")
        again = D.DesignSpec.from_dict(spec.to_dict())
        self.assertEqual(spec.to_dict(), again.to_dict())

    def test_save_and_load(self):
        spec = D.generate(seed="io.mp3", mood="dark")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "d.json")
            D.save(spec, path)
            with open(path) as fh:
                self.assertIn("palettes", json.load(fh))
            loaded = D.load(path)
        self.assertEqual(loaded.name, spec.name)
        self.assertEqual(loaded.palettes[0].fill, spec.palettes[0].fill)

    def test_to_theme_carries_the_choices(self):
        spec = D.generate(seed="th.mp3", mood="playful")
        theme = spec.to_theme("shorts")
        self.assertEqual(theme.width, 1080)
        self.assertEqual(theme.height, 1920)
        self.assertEqual(theme.transition, spec.transition)
        self.assertEqual(theme.text_align, spec.text_align)
        self.assertEqual(theme.palettes[0].fill, spec.palettes[0].fill)

    def test_unknown_fields_are_ignored(self):
        data = D.generate(seed="x", mood="calm").to_dict()
        data["something_old"] = 1
        D.DesignSpec.from_dict(data)


if __name__ == "__main__":
    unittest.main()

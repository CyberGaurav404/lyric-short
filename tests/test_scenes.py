"""Scene planner tests — pure logic, no ffmpeg, no model downloads."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lyric_short.scenes import Scene, build_scenes, describe  # noqa: E402


def seg(start, end, text, words=None):
    return {"start": start, "end": end, "text": text, "words": words or []}


class TestChunking(unittest.TestCase):
    def test_splits_by_word_count(self):
        cards = build_scenes([seg(0, 4, "one two three four five six seven")],
                             max_words=3, max_chars=99, min_scene=0.5)
        self.assertEqual([c.text for c in cards],
                         ["one two three", "four five six", "seven"])

    def test_splits_by_char_count(self):
        cards = build_scenes([seg(0, 4, "aa bb cc dd ee")], max_words=99,
                             max_chars=8, min_scene=0.5)
        self.assertTrue(all(len(c.text) <= 8 for c in cards))
        self.assertEqual(" ".join(c.text for c in cards), "aa bb cc dd ee")

    def test_no_words_lost(self):
        text = " ".join(f"w{i}" for i in range(30))
        cards = build_scenes([seg(0, 20, text)], max_words=4, max_chars=99, min_scene=0.5)
        self.assertEqual(" ".join(c.text for c in cards), text)

    def test_empty_transcript(self):
        self.assertEqual(build_scenes([]), [])


class TestTiming(unittest.TestCase):
    def test_word_timestamps_are_used(self):
        words = [{"start": 1.0, "end": 1.4, "word": "hello"},
                 {"start": 1.4, "end": 1.9, "word": "world"}]
        cards = build_scenes([seg(1.0, 1.9, "hello world", words)], max_words=4,
                             min_scene=0.5)
        self.assertAlmostEqual(cards[0].start, 1.0, places=3)
        self.assertAlmostEqual(cards[0].words[1].start, 1.4, places=3)

    def test_min_scene_is_respected(self):
        cards = build_scenes([seg(0, 0.2, "hi")], min_scene=1.5, max_scene=4)
        self.assertGreaterEqual(cards[0].duration, 1.49)

    def test_max_scene_is_respected(self):
        cards = build_scenes([seg(0, 30, "a b c d e f g h", [
            {"start": i * 3.0, "end": i * 3.0 + 2.9, "word": w}
            for i, w in enumerate("abcdefgh")])],
            max_words=1, min_scene=0.5, max_scene=2.0)
        for card in cards:
            self.assertLessEqual(card.duration, 2.01)

    def test_cards_do_not_overlap(self):
        words = [{"start": i * 0.4, "end": i * 0.4 + 0.35, "word": f"w{i}"} for i in range(20)]
        cards = build_scenes([seg(0, 8, " ".join(w["word"] for w in words), words)],
                             max_words=3, min_scene=1.5, max_scene=3)
        for a, b in zip(cards, cards[1:]):
            self.assertLessEqual(a.end, b.start + 1e-6)

    def test_offset_shifts_every_card(self):
        cards = build_scenes([seg(0, 2, "one two")], offset=1.5, min_scene=0.5)
        self.assertAlmostEqual(cards[0].start, 1.5, places=3)


class TestColours(unittest.TestCase):
    def test_alternates_from_a(self):
        cards = build_scenes([seg(0, 8, "a b c d e f")], max_words=1,
                             min_scene=0.5, start_color="a")
        self.assertEqual([c.kind for c in cards], ["a", "b"] * 3)

    def test_alternates_from_b(self):
        cards = build_scenes([seg(0, 4, "a b")], max_words=1,
                             min_scene=0.5, start_color="b")
        self.assertEqual([c.kind for c in cards], ["b", "a"])

    def test_legacy_colour_names_still_work(self):
        cards = build_scenes([seg(0, 4, "a b")], max_words=1,
                             min_scene=0.5, start_color="cream")
        self.assertEqual([c.kind for c in cards], ["b", "a"])


class TestHelpers(unittest.TestCase):
    def test_describe(self):
        scene = Scene(text="hi", start=0.0, end=1.0, kind="a")
        self.assertIn("hi", describe([scene]))


if __name__ == "__main__":
    unittest.main()

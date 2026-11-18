#!/usr/bin/env python3
"""Render one frame per style into assets/styles/ and a contact sheet.

    python scripts/preview_styles.py [--canvas shorts|landscape|square]

Handy after editing a Theme: you see every look in a few seconds instead of
rendering six videos.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

from lyric_short.config import apply_canvas  # noqa: E402
from lyric_short.render import Renderer  # noqa: E402
from lyric_short.scenes import build_scenes  # noqa: E402
from lyric_short.styles import STYLE_NAMES, get_style  # noqa: E402

LINES = [("hmm...", 0.0, 2.0), ("Kahani meri", 2.2, 4.6)]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "styles")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canvas", default="shorts")
    ap.add_argument("--at", type=float, default=5.6, help="timestamp to sample")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    segments = []
    for text, start, end in LINES:
        words = text.split()
        step = (end - start) / len(words)
        segments.append({"start": start, "end": end, "text": text,
                         "words": [{"start": start + i * step, "end": start + (i + 1) * step,
                                    "word": w} for i, w in enumerate(words)]})

    tiles = []
    for name in STYLE_NAMES:
        theme = apply_canvas(get_style(name), args.canvas)
        cards = build_scenes(segments, offset=theme.intro, total_duration=8)
        renderer = Renderer(cards, theme, duration=8.0)
        frame = renderer.frame_at(args.at)
        path = os.path.join(OUT, f"{name}.jpg")
        frame.save(path, quality=90)
        tiles.append((name, frame.resize((270, 480))))
        print("wrote", path)

    sheet = Image.new("RGB", (270 * len(tiles), 480), (0, 0, 0))
    for i, (_, tile) in enumerate(tiles):
        sheet.paste(tile, (i * 270, 0))
    sheet_path = os.path.join(ROOT, "assets", "styles.jpg")
    sheet.save(sheet_path, quality=90)
    print("wrote", sheet_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

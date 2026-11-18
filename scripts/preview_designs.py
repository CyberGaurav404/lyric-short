#!/usr/bin/env python3
"""Render a contact sheet of designs: one per mood, plus every file in designs/.

    python scripts/preview_designs.py [--canvas shorts]

Use it to see what `--design auto` is producing, or to eyeball a design JSON you
just wrote before committing to a full render.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

from lyric_short import design as design_mod  # noqa: E402
from lyric_short.render import Renderer  # noqa: E402
from lyric_short.scenes import build_scenes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "designs")
SEGMENTS = [
    {"start": 0.0, "end": 2.2, "text": "kahani meri",
     "words": [{"start": 0.0, "end": 1.1, "word": "kahani"}, {"start": 1.1, "end": 2.2, "word": "meri"}]},
    {"start": 2.4, "end": 5.6, "text": "adhoori si reh jaaye",
     "words": [{"start": 2.4, "end": 3.3, "word": "adhoori"}, {"start": 3.3, "end": 4.2, "word": "si"},
               {"start": 4.2, "end": 5.0, "word": "reh"}, {"start": 5.0, "end": 5.6, "word": "jaaye"}]},
]


def frame_for(spec, canvas, at):
    theme = spec.to_theme(canvas)
    theme.handle = "@lyricshort"
    cards = build_scenes(SEGMENTS, offset=theme.intro, total_duration=8)
    return Renderer(cards, theme, duration=8.0).frame_at(at)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canvas", default="shorts")
    ap.add_argument("--at", type=float, default=4.4)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    tiles = []

    for mood in design_mod.MOODS:
        spec = design_mod.generate(seed="kahani.mp3", mood=mood, canvas=args.canvas)
        frame = frame_for(spec, args.canvas, args.at)
        frame.save(os.path.join(OUT, f"mood-{mood}.jpg"), quality=90)
        tiles.append(frame.resize((270, 480)))
        print(f"mood   {mood:<8} {design_mod.describe(spec)}")

    for path in sorted(glob.glob(os.path.join(ROOT, "designs", "*.json"))):
        spec = design_mod.load(path)
        frame = frame_for(spec, args.canvas, args.at)
        name = os.path.splitext(os.path.basename(path))[0]
        frame.save(os.path.join(OUT, f"design-{name}.jpg"), quality=90)
        tiles.append(frame.resize((270, 480)))
        print(f"design {name:<12} {design_mod.describe(spec)}")

    sheet = Image.new("RGB", (270 * len(tiles), 480), (0, 0, 0))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (i * 270, 0))
    sheet_path = os.path.join(ROOT, "assets", "designs.jpg")
    sheet.save(sheet_path, quality=90)
    print("wrote", sheet_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

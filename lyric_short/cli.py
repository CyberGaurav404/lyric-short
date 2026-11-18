"""Command line entry point: audio in, 9:16 lyric short out."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile

from . import art, media, scenes as scenes_mod, transcribe as asr
from .config import PRESETS, get_preset
from .render import Renderer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lyric-short",
        description="Turn an audio file into a 9:16 lyric short (YouTube Shorts / Reels).",
    )
    p.add_argument("--audio", required=True, help="input audio or video file")
    p.add_argument("--out", default="short.mp4", help="output mp4 (default: short.mp4)")
    p.add_argument("--preset", default="shorts", choices=sorted(PRESETS),
                   help="canvas preset (default: shorts = 1080x1920)")
    p.add_argument("--fps", type=int, default=None, help="override frame rate")
    p.add_argument("--font", default=None, help="path to a .ttf/.otf serif font")

    g = p.add_argument_group("transcription")
    g.add_argument("--transcript", default=None,
                   help="skip ASR and read a .json/.srt transcript instead")
    g.add_argument("--save-transcript", default=None,
                   help="write the ASR result to this .json file")
    g.add_argument("--model", default="small",
                   help="whisper model: tiny/base/small/medium/large-v3 (default: small)")
    g.add_argument("--language", default=None, help="ISO code such as hi or en (auto if omitted)")
    g.add_argument("--backend", default="faster-whisper",
                   choices=["faster-whisper", "openai-whisper"])
    g.add_argument("--device", default="auto", help="cpu / cuda / auto")
    g.add_argument("--compute-type", default="int8", help="int8 / int8_float16 / float16 / float32")

    s = p.add_argument_group("scenes")
    s.add_argument("--max-words", type=int, default=4, help="words per card (default: 4)")
    s.add_argument("--max-chars", type=int, default=26, help="characters per card (default: 26)")
    s.add_argument("--min-scene", type=float, default=None, help="seconds a card stays up at least")
    s.add_argument("--max-scene", type=float, default=None, help="seconds a card stays up at most")
    s.add_argument("--start-color", default=None, choices=["green", "cream"],
                   help="colour of the first card")
    s.add_argument("--handle", default=None, help="watermark text, e.g. @yourname")
    s.add_argument("--limit", type=float, default=None,
                   help="only use the first N seconds of the audio")

    o = p.add_argument_group("output")
    o.add_argument("--crf", type=int, default=20, help="x264 quality, lower = better (default: 20)")
    o.add_argument("--x264-preset", default="medium",
                   choices=["ultrafast", "superfast", "veryfast", "faster", "fast",
                            "medium", "slow"],
                   help="encoder speed vs file size (default: medium)")
    o.add_argument("--dry-run", action="store_true", help="print the card plan and stop")
    o.add_argument("--seed", type=int, default=7, help="background noise seed")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if not os.path.exists(args.audio):
        raise SystemExit(f"audio not found: {args.audio}")

    theme = get_preset(args.preset)
    if args.fps:
        theme.fps = args.fps
    if args.min_scene:
        theme.min_scene = args.min_scene
    if args.max_scene:
        theme.max_scene = args.max_scene
    if args.start_color:
        theme.start_color = args.start_color
    if args.handle:
        theme.handle = args.handle

    audio_duration = media.probe_duration(args.audio)
    usable = audio_duration if args.limit is None else min(audio_duration, args.limit)

    if args.transcript:
        print(f"[input] transcript {args.transcript}")
        segments = asr.load_transcript(args.transcript)
    else:
        with tempfile.TemporaryDirectory(prefix="lyricshort-") as tmp:
            wav = media.extract_audio(args.audio, os.path.join(tmp, "audio.wav"))
            segments = asr.transcribe(wav, model=args.model, language=args.language,
                                      backend=args.backend, device=args.device,
                                      compute_type=args.compute_type)

    if args.save_transcript:
        asr.save_transcript(segments, args.save_transcript)
        print(f"[whisper] transcript saved to {args.save_transcript}")

    cards = scenes_mod.build_scenes(
        segments,
        max_words=args.max_words,
        max_chars=args.max_chars,
        min_scene=theme.min_scene,
        max_scene=theme.max_scene,
        start_color=theme.start_color,
        offset=theme.intro,
        total_duration=theme.intro + usable,
    )
    if args.limit is not None:
        cards = [c for c in cards if c.start < theme.intro + usable]
        for c in cards:
            c.end = min(c.end, theme.intro + usable)

    if not cards:
        raise SystemExit("no speech found in the audio — nothing to draw")

    print(f"[scenes] {len(cards)} cards:\n" + scenes_mod.describe(cards))
    if args.dry_run:
        return 0

    duration = theme.intro + usable + theme.outro
    renderer = Renderer(cards, theme, font_path=args.font, duration=duration, seed=args.seed)
    renderer.render(args.out, audio_path=args.audio, crf=args.crf,
                    preset=args.x264_preset)
    print(f"[done] {args.out}  ({os.path.getsize(args.out) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Command line entry point: audio in, lyric short out."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import zlib

from . import art, design as design_mod, media, scenes as scenes_mod, styles, transcribe as asr
from .config import CANVAS_PRESETS, apply_canvas
from .render import Renderer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lyric-short",
        description="Turn an audio file into a lyric short (YouTube Shorts / Reels / TikTok).",
        epilog="Styles: " + ", ".join(styles.STYLE_NAMES) + ", auto",
    )
    p.add_argument("--audio", default=None, help="input audio or video file")
    p.add_argument("--out", default="short.mp4", help="output mp4 (default: short.mp4)")
    p.add_argument("--design", default=None,
                   help="render a design: a JSON file, or 'auto' to invent one")
    p.add_argument("--mood", default=None,
                   help="bias for --design auto: " + " | ".join(design_mod.MOODS))
    p.add_argument("--save-design", default=None,
                   help="write the design used to this JSON file (reuse it later)")
    p.add_argument("--style", default="botanical",
                   help="fallback look when no --design is given: "
                        + " | ".join(styles.STYLE_NAMES) + " | auto")
    p.add_argument("--list-styles", action="store_true", help="print the styles and exit")
    p.add_argument("--preset", default="shorts", choices=sorted(CANVAS_PRESETS),
                   help="canvas: shorts (1080x1920), landscape, square")
    p.add_argument("--fps", type=int, default=None, help="override frame rate")
    p.add_argument("--font", default=None, help="path to a .ttf/.otf serif font")
    p.add_argument("--vary", action="store_true",
                   help="nudge the palette a little so runs do not look identical")
    p.add_argument("--seed", default=None,
                   help="seed for style/grain/variation (default: derived from the file name)")

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
    s.add_argument("--start-color", default=None, choices=["a", "b", "green", "cream"],
                   help="which palette the first card uses")
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
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_styles:
        for name in styles.STYLE_NAMES:
            print(f"{name:<10} {styles.describe(styles.get_style(name))}")
        print(f"{'auto':<10} pick one of the above from the audio name")
        return 0

    if not args.audio:
        raise SystemExit("--audio is required (try --list-styles to see the looks)")
    if not os.path.exists(args.audio):
        raise SystemExit(f"audio not found: {args.audio}")

    seed = args.seed or os.path.basename(args.audio)

    spec = None
    if args.design:
        if args.design in ("auto", "generate"):
            spec = design_mod.generate(seed=seed, mood=args.mood, canvas=args.preset)
        else:
            spec = design_mod.load(args.design)
        theme = spec.to_theme(args.preset)
    else:
        theme = (styles.auto_style(seed) if args.style in ("auto", "random")
                 else styles.get_style(args.style))
        if args.vary:
            theme = styles.vary(theme, seed=seed)
        theme = apply_canvas(theme, args.preset)
    if args.fps:
        theme.fps = args.fps
    if args.min_scene:
        theme.min_scene = args.min_scene
    if args.max_scene:
        theme.max_scene = args.max_scene
    if args.handle:
        theme.handle = args.handle
    if spec is not None and args.save_design:
        design_mod.save(spec, args.save_design)
        print(f"[design] saved to {args.save_design}")

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
        start_color=args.start_color or "a",
        offset=theme.intro,
        total_duration=theme.intro + usable,
    )
    if args.limit is not None:
        cards = [c for c in cards if c.start < theme.intro + usable]
        for c in cards:
            c.end = min(c.end, theme.intro + usable)

    if not cards:
        raise SystemExit("no speech found in the audio — nothing to draw")

    if spec is not None:
        print(f"[design] {design_mod.describe(spec)}")
    else:
        print(f"[style] {theme.name} ({theme.bg_mode} bg, {theme.card_mode} card, "
              f"{theme.ornament} ornament, {theme.transition} transition)")
    print(f"[scenes] {len(cards)} cards:\n" + scenes_mod.describe(cards))
    if args.dry_run:
        return 0

    duration = theme.intro + usable + theme.outro
    renderer = Renderer(cards, theme, font_path=args.font, duration=duration, seed=zlib.crc32(seed.encode()) % 9999)
    renderer.render(args.out, audio_path=args.audio, crf=args.crf, preset=args.x264_preset)
    print(f"[done] {args.out}  ({os.path.getsize(args.out) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

---
name: lyric-short
description: Turn an audio file into a 9:16 lyric video for YouTube Shorts, Reels or TikTok. Use when someone hands over a song, voice note, podcast clip or any audio and wants a lyric video, animated captions, a quote video, or a "short" version of it. Whisper transcribes with word-level timestamps, the planner cuts the transcript into cards, one of six visual styles renders the frames, ffmpeg encodes 1080x1920 with the original audio.
license: MIT
---

# lyric-short — audio to lyric short

A command line tool plus a small Python library. You give it an audio file; it
gives back a vertical video where the words appear one at a time, on the beat,
on styled cards.

## When to use this skill

Use it when the user:

- uploads or points at an **audio file** (mp3, wav, m4a, mp4, voice note, song)
  and wants a video made from it
- asks for a **lyric video**, **animated captions**, **quote video**, **music
  visual**, or a **Shorts / Reels / TikTok** version of something
- wants the words on screen to be **synced to the voice**
- wants a video in one of the ready-made looks (botanical, midnight, sunset,
  paper, poster, neon) or a variation of one

Do **not** use it when the user wants a talking-head edit, a slideshow of their
photos, subtitle burn-in over existing footage, or a video with no audio input.

## What it produces

- 1080×1920 @ 30fps H.264 + AAC (or 1920×1080 / 1080×1080 with `--preset`)
- cards alternating between two palettes, one word revealed at a time
- intro (heart) and outro (fade), soft crossfades, optional grain and glow
- the original audio, delayed to match the intro card

## Setup (once per environment)

```bash
pip install -r requirements.txt      # pillow, numpy, imageio-ffmpeg, faster-whisper
python scripts/fetch_fonts.py        # Playfair Display (SIL OFL)
python -m lyric_short --list-styles  # sanity check, prints the six looks
```

`ffmpeg` comes from `imageio-ffmpeg` if it is not on `PATH`. No GPU needed.

## The pipeline

1. **Probe** the audio (`ffmpeg -i`) for duration — you need it to plan.
2. **Transcribe** with faster-whisper, word timestamps on:
   `tiny` for a 20-second draft, `small` for real work, `medium` for a language
   Whisper struggles with (Hindi/Urdu rap, heavy accent), `large-v3` only if time
   is not a constraint. Pass `--language hi` when the audio is not English: auto
   detect on a sung line is the most common cause of a bad transcript.
3. **Plan cards** — `scenes.py` packs words into cards (`--max-words`,
   `--max-chars`), keeps each card on screen for `--min-scene`..`--max-scene`
   seconds and alternates palettes.
4. **Render** — Pillow draws every frame, ffmpeg encodes and muxes.
5. **Verify** — see the checklist below before you show the file to the user.

## Commands

```bash
# simplest run, 9:16, default look
python -m lyric_short --audio song.mp3 --out short.mp4 --handle "@yourname"

# a look picked for you from the file name, with a small palette variation
python -m lyric_short --audio song.mp3 --out short.mp4 --style auto --vary

# specific look + Hindi lyrics + only the first 45 seconds
python -m lyric_short --audio song.mp3 --out short.mp4 --style sunset --language hi --limit 45

# inspect the plan without rendering (fast, do this first)
python -m lyric_short --audio song.mp3 --transcript t.json --dry-run

# reuse a transcript across restyles (no model reload, no re-ASR)
python -m lyric_short --audio song.mp3 --out v1.mp4 --transcript t.json --style neon
```

Key flags: `--style`, `--vary`, `--preset shorts|landscape|square`, `--model`,
`--language`, `--max-words`, `--max-chars`, `--min-scene`, `--max-scene`,
`--start-color a|b`, `--handle`, `--limit`, `--crf`, `--x264-preset`,
`--transcript`, `--save-transcript`, `--dry-run`, `--seed`, `--font`.

## Choosing a style (creative direction)

| audio is… | style | why |
| --- | --- | --- |
| soft, acoustic, romantic | `botanical` | sage and cream, floral corners, calm |
| late-night, lo-fi, sad | `midnight` | navy, ivory type, brass arcs |
| warm, nostalgic, indie | `sunset` | dusk gradient, plum and peach, cards slide |
| poetry, storytelling, a note to camera | `paper` | daylight, ink on paper, minimal |
| hype, rap, a hook you want shouted | `poster` | full-bleed panels, huge type, pop cuts |
| electronic, pop, night drive | `neon` | dark glass, glowing cyan and magenta |

Rules of thumb:

- **Uncertain or the user said "you decide"** → `--style auto --vary`. It hashes
  the file name, so the same audio keeps its look and a new song gets a new one.
- **Two videos for the same user** → give them different styles, or the same
  style with `--vary`, so the feed does not look like one template.
- **Long words or a Hindi/Urdu line** → lower `--max-words` to 3 and
  `--max-chars` to 22; cards breathe and the type stays big.
- **Fast song** → `--max-scene 2.4 --min-scene 1.1` so cards keep up.
- **A single killer line** → `--max-scene 6 --min-scene 3` to let it sit.
- **Instagram / TikTok crop-safe area** → keep `--handle` short and lower case;
  the card sits at 47% height so it stays clear of the UI.

## Making it new (not the same video twice)

- `--style` across the six looks is the cheapest variety.
- `--vary` shifts the palette per seed; `--seed` makes a variation repeatable.
- `--start-color b` flips which palette opens the video.
- `--preset landscape|square` for the same content on other surfaces.
- For a genuinely new look, add a builder in `lyric_short/styles.py` (a `Theme`
  with palettes, `bg_mode`, `card_mode`, `ornament`, `transition`, `grain`,
  `glow`) and register it in `BUILDERS` — the renderer needs no change.
  Preview every style in seconds with `python scripts/preview_styles.py`.

## Verify before delivering

1. `ffmpeg -i out.mp4` → 1080×1920, 30fps, has an audio stream, duration ≈
   intro + audio + outro.
2. Look at three frames (first card, middle, last) — text must be readable,
   inside the card, and not clipped.
3. The last card should not be cut mid-word: if it is, raise `--min-scene` or
   trim with `--limit`.
4. Audio sync: the first word must land on the first syllable. If the voice
   starts before the card, the intro is too long — lower `theme.intro`.
5. Report the style used and the runtime to the user in one line.

## When something goes wrong

| symptom | cause | fix |
| --- | --- | --- |
| empty transcript / no cards | no speech, or music only | tell the user; the tool needs words |
| transcript is gibberish | wrong language or a sung line | `--language hi`, bigger `--model` |
| cards drift out of sync | VAD dropped a quiet intro | `--min-scene 1.2`, or trim the audio first |
| text clipped at card edges | long words | `--max-words 3 --max-chars 22` |
| encoder dies on a small machine | memory | `--x264-preset veryfast`, or let the built-in PNG fallback run |
| fonts look wrong | Playfair missing | `python scripts/fetch_fonts.py` or `--font path/to/serif.ttf` |

## Copyright and safety

Whisper transcribing a song does not give anyone the right to publish it. If the
user does not own the recording or the lyrics, say so plainly before rendering,
and offer the alternative: their own voice note, a royalty-free track, or
`scripts/make_demo_audio.py` for a generated bed. Do not put words in a real
person's mouth, and do not label a generated video as someone else's work.

---
name: lyric-short
description: Turn an audio file into a 9:16 lyric video for YouTube Shorts, Reels or TikTok, designing the scene for that specific audio. Use when someone hands over a song, voice note, podcast clip or any audio and wants a lyric video, animated captions, a quote video, or a short. Whisper transcribes with word-level timestamps, you compose a design (palette, background, card, type, motion), the renderer draws it, ffmpeg encodes 1080x1920 with the original audio.
license: MIT
---

# lyric-short — audio to lyric short, designed per video

A CLI plus a small library: audio in, vertical lyric video out.

**The important part:** the six styles in `styles.py` are *reference points*, not
the product. A reference clip someone shows you is an example of the *format*
(words on cards, 9:16, synced to the voice) — not a look to copy. Your job on
every job is to design the scene for that audio, so two videos never come out the
same.

## When to use this skill

Use it when the user:

- hands over an **audio file** (mp3, wav, m4a, voice note, song) and wants a video
- asks for a **lyric video**, **animated captions**, **quote video**, **music
  visual**, or a **Shorts / Reels / TikTok** cut
- wants the words on screen **synced to the voice**
- shows a reference video and says "make one like this" — take the format, then
  design something of your own

Do **not** use it for talking-head edits, photo slideshows, or burning subtitles
over existing footage.

## The workflow

1. **Read the material.** Transcribe first (`--save-transcript t.json`), then read
   the lines. What is it — a love note, a hype hook, a poem, a rant? That is the
   mood, and the mood decides the design. Note the tempo too: a fast track needs
   shorter cards.
2. **Design the scene** (see below). Either write a design JSON yourself, or let
   the generator propose one (`--design auto --mood warm`) and then adjust it.
   Save it next to the transcript (`--save-design`) so the look is repeatable.
3. **Dry run** (`--dry-run`) and read the card plan: card count, seconds per card,
   no card holding half a verse.
4. **Render**, then **verify** against the checklist at the bottom.
5. **Report** in one or two lines: the design you chose and why.

```bash
# 1. transcribe once
python -m lyric_short --audio song.mp3 --transcript t.json --save-transcript t.json --dry-run

# 2. invent a design from the mood, keep it
python -m lyric_short --audio song.mp3 --transcript t.json --out short.mp4 \
       --design auto --mood warm --save-design designs/song.json --handle "@you"

# 3. or render a design you wrote by hand
python -m lyric_short --audio song.mp3 --transcript t.json --out short.mp4 \
       --design designs/ink_and_sun.json
```

## Designing the scene

A design is a `DesignSpec` — a JSON file, or generated. Every field below changes
what the video looks like. Change at least three of them between two videos for
the same person.

| field | what it does | good range |
| --- | --- | --- |
| `palettes` | two card looks: `fill`, `text`, `orn` colours | text vs fill contrast ≥ 4.5 |
| `bg_mode` | `bokeh` soft night, `stars` pinpoints, `gradient` wash, `paper` daylight | pick to match the mood's light |
| `bg_color`, `glow_color` | the backdrop and the glow behind the card | keep the card the brightest thing |
| `card_mode` | `frame` bordered card, `rounded` soft panel, `fullbleed` colour panel | one per video |
| `card_ratio`, `card_aspect`, `card_center_y` | card size and where it sits | 0.84–0.94, 1.24–1.42, 0.44–0.52 |
| `corner` | corner radius as a fraction of card height | 0 for print-like, 0.02–0.05 for soft |
| `ornament` | `botanical` leaves, `arcs`, `lines`, `none` | one at most, never with `fullbleed` clutter |
| `text_align` | `center` classic, `left` editorial | `left` pairs with `accent_rule` |
| `accent_rule` | short rule under the lyric block | on for minimal/editorial, off for romantic |
| `font_weight`, `text_size` | weight axis and starting size | 400–500 gentle, 600–700 bold; 0.09–0.13 |
| `transition` | `fade` calm, `slide` warm, `pop` punchy | match tempo |
| `zoom` | slow push inside the card | 0.01–0.04 |
| `grain`, `glow` | film grain, text glow | grain ≤ 0.08; glow only for neon/dark |

Writing one by hand:

```json
{
  "name": "monsoon_note",
  "mood": "calm",
  "palettes": [
    {"fill": [38, 54, 62], "text": [238, 244, 240], "orn": [150, 180, 170]},
    {"fill": [238, 244, 240], "text": [38, 54, 62], "orn": [38, 54, 62]}
  ],
  "bg_mode": "bokeh",
  "bg_color": [6, 12, 14],
  "glow_color": [18, 34, 38],
  "card_mode": "rounded",
  "card_ratio": 0.90,
  "card_aspect": 1.32,
  "card_center_y": 0.46,
  "corner": 0.03,
  "ornament": "none",
  "text_align": "left",
  "accent_rule": true,
  "font_weight": 500,
  "text_size": 0.10,
  "transition": "fade",
  "zoom": 0.02,
  "grain": 0.03,
  "glow": 0.0,
  "handle_color": [170, 196, 188]
}
```

Rules of taste (break them on purpose, not by accident):

- **One idea per video.** A full-bleed poster with a glow and botanical leaves is
  noise. Pick a lane.
- **Contrast first.** If the type does not clear 4.5:1 against the card, change
  the text colour, not the mood.
- **The card is the loudest thing in the frame.** Background glow stays behind it.
- **Text never touches the edge.** Keep lines inside 78% of the card width; the
  renderer shrinks to fit, but a line that shrinks twice is too long — lower
  `--max-words`.
- **Motion matches tempo.** `fade` for slow, `slide` for warm mid-tempo, `pop` for
  hooks. Grain and glow are seasoning, not structure.

Mood → starting point, if you want a shortcut (then vary it):

| the words feel… | `--mood` | usually lands on |
| --- | --- | --- |
| soft, romantic, acoustic | `calm` | muted green/cream, bokeh, fade |
| warm, nostalgic | `warm` | dusk gradient, rounded, slide |
| late-night, lonely | `dark` | navy stars, thin arcs, faint glow |
| a hook you shout | `bold` | full-bleed panels, huge type, pop |
| poetry, a letter | `minimal` | paper, left aligned, one rule |
| playful, pop | `playful` | saturated pairs, arcs, pop |

`python scripts/preview_designs.py` renders every mood plus every file in
`designs/` in a few seconds — use it before committing to a 3-minute render.

## Scene pacing

- `--max-words 4 --max-chars 26` default; drop to 3 / 22 for long words or
  Devanagari-heavy lines.
- `--min-scene 1.5 --max-scene 4` default; fast song → `1.1 / 2.4`, one killer
  line → `3 / 6`.
- `--limit 45` for Shorts, `--limit 60` for Reels.
- `--start-color b` flips which palette opens, for a different opening beat.

## Verify before delivering

1. `ffmpeg -i out.mp4` → 1080×1920, 30fps, audio stream present, duration ≈
   intro + audio + outro.
2. Look at three frames: first card, a middle card, the last card. Text readable,
   inside the card, not clipped.
3. First word lands on the first syllable. If the voice starts before the card,
   the intro is too long.
4. The last card is not cut mid-word; if it is, raise `--min-scene` or trim.
5. Say which design you used and why, in one line.

## When something goes wrong

| symptom | cause | fix |
| --- | --- | --- |
| empty transcript / no cards | no speech, music only | tell the user; the tool needs words |
| gibberish transcript | wrong language, or a sung line | `--language hi`, bigger `--model` |
| cards drift | VAD dropped a quiet intro | `--min-scene 1.2`, or trim the audio |
| text clipped | long words | `--max-words 3 --max-chars 22` |
| unreadable card | low contrast palette | fix `palettes`, check with `contrast()` |
| encoder dies on a small machine | memory | `--x264-preset veryfast`; the PNG fallback also kicks in |
| fonts wrong | Playfair missing | `python scripts/fetch_fonts.py` or `--font path` |

## Copyright and safety

Whisper transcribing a song does not grant the right to publish it. If the user
does not own the recording or the lyrics, say so before rendering, and offer their
own voice note, a royalty-free track, or `scripts/make_demo_audio.py`. Do not put
words in a real person's mouth and do not present a generated video as someone
else's work.

# lyric-short

Audio in → 9:16 lyric video out. Built for YouTube Shorts, Reels and TikTok.

Give it a song, a voice note or any audio file. It transcribes the words with
Whisper, cuts the transcript into short lyric cards, picks a look, and renders a
vertical video in which every word appears in sync with the voice.

It is also a **skill for an AI agent** — see [SKILL.md](SKILL.md) for the
instructions an agent follows to drive it end to end.

```
audio.mp3 ──► ffmpeg ──► Whisper (word timestamps) ──► scene planner ──► renderer ──► short.mp4
```

![preview](assets/preview.jpg)

## Six looks, one command

![styles](assets/styles.jpg)

`botanical` · `midnight` · `sunset` · `paper` · `poster` · `neon` — plus `auto`,
which picks one from a hash of the file name so the same song keeps its look and
the next song gets a different one. `--vary` shifts the palette a little so two
videos in the same style never look identical.

| style | mood | card | motion |
| --- | --- | --- | --- |
| `botanical` | soft, acoustic, romantic | cream & sage frame, floral corners | fade |
| `midnight` | late night, lo-fi | navy card, brass arcs | fade + grain |
| `sunset` | warm, nostalgic | rounded plum & peach | slide |
| `paper` | poetry, storytelling | daylight, ink on paper | fade, tiny zoom |
| `poster` | hype, rap, hooks | full-bleed colour panels, huge type | pop cuts |
| `neon` | electronic, night drive | dark glass, glowing type | pop + glow |

## Install

```bash
git clone https://github.com/CyberGaurav404/lyric-short.git
cd lyric-short

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/fetch_fonts.py          # Playfair Display, SIL OFL
```

`ffmpeg` is required. If you do not have it system-wide, `pip install
imageio-ffmpeg` (already in `requirements.txt`) provides a bundled binary and the
tool finds it automatically.

## Use

```bash
python -m lyric_short --audio song.mp3 --out short.mp4 --handle "@yourname"
```

More:

```bash
# let the tool choose the look, with a palette variation
python -m lyric_short --audio song.mp3 --out short.mp4 --style auto --vary

# a specific look, Hindi lyrics, first 45 seconds only
python -m lyric_short --audio song.mp3 --out short.mp4 --style sunset --language hi --limit 45

# see the card plan without rendering
python -m lyric_short --audio song.mp3 --transcript t.json --dry-run

# restyle the same transcript (no model reload, no second ASR pass)
python -m lyric_short --audio song.mp3 --out v2.mp4 --transcript t.json --style neon
```

| flag | what it does |
| --- | --- |
| `--style botanical\|midnight\|sunset\|paper\|poster\|neon\|auto` | the look |
| `--vary` | nudge the palette so runs differ |
| `--preset shorts\|landscape\|square` | canvas shape (default `shorts` = 1080×1920) |
| `--model tiny\|base\|small\|medium\|large-v3` | Whisper model (default `small`) |
| `--language hi` | force a language instead of auto-detect |
| `--max-words 4 --max-chars 26` | how much text one card may carry |
| `--min-scene 1.5 --max-scene 4` | how long one card stays on screen |
| `--start-color a\|b` | which palette opens the video |
| `--handle "@yourname"` | small watermark near the bottom |
| `--limit 45` | only use the first 45 seconds |
| `--transcript t.json` / `--save-transcript t.json` | reuse / keep the Whisper output |
| `--dry-run` | print the card plan, render nothing |
| `--crf 20` | quality vs size, lower is better |
| `--x264-preset veryfast` | encode faster with a slightly bigger file |
| `--list-styles` | print the six looks and their settings |

Typical run:

```
$ python -m lyric_short --audio song.mp3 --out short.mp4 --language hi --style auto
[whisper] loading faster-whisper model 'small' (auto, int8)
[whisper] language=hi (p=0.98)
[style] sunset (gradient bg, rounded card, none ornament, slide transition)
[scenes] 24 cards:
01    1.50–  3.10  a      kahani meri
02    3.12–  5.40  b      adhoori si
...
[render] sunset · 1080x1920 @ 30fps · 52.30s · 24 cards -> short.mp4
[done] short.mp4  (6.4 MB)
```

## How the scenes are decided

`lyric_short/scenes.py` does three things:

1. **Words** — takes Whisper's word timestamps when available; otherwise spreads
   the words of the segment evenly across its duration.
2. **Chunks** — greedily packs words into cards of at most `--max-words` words and
   `--max-chars` characters, so a card never holds a whole paragraph.
3. **Timing** — stretches a card to at least `min_scene` seconds, trims it to at
   most `max_scene`, and never lets it overlap the next card. Cards alternate
   palette from `--start-color`.

Reveal timing inside a card comes straight from the word timestamps, which is why
the text lands on the beat instead of drifting.

## Use it as an agent skill

[SKILL.md](SKILL.md) is written for an AI agent: when to reach for the tool, how
to pick a style from the mood of the audio, the exact commands, a verification
checklist, and what to do when the transcript comes back wrong. Drop the folder
into an agent's skills directory, or point the agent at `SKILL.md`.

## Layout of the repo

```
SKILL.md         agent-facing instructions (when/how to run this)
lyric_short/
  cli.py         argument parsing and the pipeline
  media.py       ffmpeg: probe, extract, encode, mux
  transcribe.py  faster-whisper / openai-whisper backends, transcript io
  scenes.py      transcript -> cards
  render.py      frame loop, transitions, word reveals, grain
  art.py         backgrounds, cards, ornaments, text layout, heart
  config.py      Theme + Palette dataclasses, canvas presets
  styles.py      the six looks, auto-style and palette variation
tests/           unittest suite for the scene planner and styles
examples/        demo audio, demo transcript, rendered demos
scripts/         font download, demo audio generator, style previews
```

## Make it yours

Everything visual is a `Theme` in `lyric_short/styles.py`:

```python
from lyric_short.config import Palette, Theme

def ocean() -> Theme:
    return Theme(
        name="ocean",
        palettes=[Palette((12, 48, 72), (238, 248, 255), (120, 200, 220)),
                  Palette((238, 248, 255), (12, 48, 72), (12, 48, 72))],
        bg_color=(3, 10, 18), glow_color=(10, 40, 70), bg_mode="stars",
        ornament="arcs", card_mode="rounded", transition="slide", grain=0.05,
    )
```

Register it in `BUILDERS` and it is available as `--style ocean`. Then:

```bash
python scripts/preview_styles.py     # one frame per style, in a few seconds
```

A different font is a `--font path/to/Serif.ttf` away (variable fonts get their
weight axis set automatically).

## Speed and memory

- Rendering is CPU-only; a 50-second short takes roughly 3–5 minutes on a laptop.
- The encoder runs with a single thread on purpose so it stays under ~1 GB of RAM.
  If a pipe encode still dies on a very small machine, the renderer automatically
  falls back to writing a PNG sequence and encoding from that.
- Whisper: `tiny` for drafts, `small` for real work, `medium`/`large-v3` when the
  lyrics matter and you have time. `--compute-type float16` with `--device cuda`
  is much faster on a GPU.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Notes on copyright

The tool is a renderer — what you feed it is your responsibility. Do not publish
lyrics or recordings you do not have the rights to. Whisper will happily
transcribe a commercial song; that does not make the result yours to post.

## License

MIT for the code. Playfair Display is under the SIL Open Font License
(`assets/fonts/OFL.txt`). The demo audio in `examples/` is generated by
`scripts/make_demo_audio.py`, so it is free to use.

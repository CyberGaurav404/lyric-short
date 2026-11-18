# lyric-short

Audio in → 9:16 lyric video out. Built for YouTube Shorts, Reels and TikTok.

Give it a song, a voice note or any audio file. It transcribes the words with
Whisper, cuts the transcript into short lyric cards, decides which card is green
and which is cream, and renders a vertical video in which every word appears in
sync with the voice.

```
audio.mp3 ──► ffmpeg ──► Whisper (word timestamps) ──► scene planner ──► renderer ──► short.mp4
```

![preview](assets/preview.jpg)

## What you get

- **1080×1920 @ 30fps**, H.264 + AAC, ready to upload
- serif lyric cards, alternating green / cream, floral corner ornaments
- one word at a time, timed from Whisper's word timestamps
- soft crossfades, slow card zoom, glowing heart intro, fade to black
- original audio muxed back in, delayed to match the intro card
- also renders 16:9 (`--preset landscape`) and 1:1 (`--preset square`)

## Install

```bash
git clone https://github.com/<you>/lyric-short.git
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

Useful flags:

| flag | what it does |
| --- | --- |
| `--preset shorts\|landscape\|square` | canvas shape (default `shorts` = 1080×1920) |
| `--model tiny\|base\|small\|medium\|large-v3` | Whisper model, bigger = better + slower (default `small`) |
| `--language hi` | force a language instead of auto-detect |
| `--max-words 4 --max-chars 26` | how much text one card may carry |
| `--min-scene 1.5 --max-scene 4` | how long one card stays on screen |
| `--start-color green\|cream` | colour of the first card |
| `--handle "@yourname"` | small watermark near the bottom |
| `--limit 45` | only use the first 45 seconds (handy for shorts) |
| `--transcript out.json` | skip Whisper and use a saved transcript |
| `--save-transcript t.json` | keep the Whisper output for reuse |
| `--dry-run` | print the card plan, render nothing |
| `--crf 20` | quality vs size, lower is better |
| `--x264-preset veryfast` | encode faster with a slightly bigger file |

Typical run:

```
$ python -m lyric_short --audio song.mp3 --out short.mp4 --language hi
[whisper] loading faster-whisper model 'small' (auto, int8)
[whisper] language=hi (p=0.98)
[scenes] 24 cards:
01    1.50–  3.10  green  kahani meri
02    3.12–  5.40  cream  adhoori si
...
[render] 1080x1920 @ 30fps, 52.30s, 24 cards -> short.mp4
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
   colour from `--start-color`.

Reveal timing inside a card comes straight from the word timestamps, which is why
the text lands on the beat instead of drifting.

## Layout of the repo

```
lyric_short/
  cli.py         argument parsing and the pipeline
  media.py       ffmpeg: probe, extract, encode, mux
  transcribe.py  faster-whisper / openai-whisper backends, transcript io
  scenes.py      transcript -> cards
  render.py      frame loop, crossfades, word reveals
  art.py         background, cards, ornaments, text layout, heart
  config.py      Theme dataclass + presets (shorts / landscape / square)
tests/           unittest suite for the scene planner
examples/        demo audio, demo transcript, rendered demo
scripts/         font download, demo audio generator
```

## Make it yours

Everything visual is in `lyric_short/config.py`:

```python
from lyric_short.config import Theme
theme = Theme(green=(30, 90, 120), cream=(245, 240, 230), card_ratio=0.92)
```

Change `green`, `cream`, `bg_color`, `card_ratio`, `card_aspect`, `text_size`,
`font_path`, `zoom`, `crossfade`, `intro`… then pass the theme to `Renderer`
directly, or add a preset to `PRESETS`.

A different font is a `--font path/to/Serif.ttf` away (variable fonts get their
weight axis set automatically).

## Speed and memory

- Rendering is CPU-only; a 50-second short takes roughly 3–5 minutes on a laptop.
- The encoder runs with a single thread on purpose so it stays under ~1 GB of RAM.
  If a pipe encode still dies on a very small machine, the renderer automatically
  falls back to writing a PNG sequence and encoding from that.
- Whisper: `tiny` for drafts, `small` for real work, `medium`/`large-v3` when the
  lyrics matter and you have time. `--compute-type float16` plus `--device cuda`
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

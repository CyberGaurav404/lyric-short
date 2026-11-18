"""Turn transcript segments into cards ("scenes").

Rules of thumb for a short that reads well:

* one card carries one short phrase — at most `max_words` words / `max_chars` chars
* a card lives for `min_scene`..`max_scene` seconds
* words are revealed one after another, synced to the audio when the ASR gave
  word timestamps, and evenly spread over the segment when it did not
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

PUNCT = ",.!?;:-–—\"'()[]{}"


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Scene:
    text: str
    start: float
    end: float
    words: List[Word] = field(default_factory=list)
    kind: str = "a"

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _words_of(segment: dict) -> List[Word]:
    raw = [w for w in segment.get("words") or [] if str(w.get("word", "")).strip()]
    if raw:
        words = []
        for w in raw:
            start = float(w.get("start") or 0.0)
            end = float(w.get("end") or start + 0.25)
            words.append(Word(str(w["word"]).strip(), start, max(end, start + 0.08)))
        return words

    # no word timings: spread the words evenly across the segment
    tokens = [t for t in str(segment.get("text", "")).split() if t]
    if not tokens:
        return []
    start = float(segment.get("start", 0.0))
    end = float(segment.get("end", start + len(tokens) * 0.35))
    step = max(0.12, (end - start) / len(tokens))
    return [Word(t, start + i * step, start + (i + 1) * step) for i, t in enumerate(tokens)]


def _chunk(words: Sequence[Word], max_words: int, max_chars: int) -> List[List[Word]]:
    chunks: List[List[Word]] = []
    cur: List[Word] = []
    for w in words:
        trial = cur + [w]
        text = " ".join(x.text for x in trial)
        if cur and (len(trial) > max_words or len(text) > max_chars):
            chunks.append(cur)
            cur = [w]
        else:
            cur = trial
    if cur:
        chunks.append(cur)
    return chunks


def build_scenes(segments: Iterable[dict], max_words: int = 4, max_chars: int = 26,
                 min_scene: float = 1.5, max_scene: float = 4.0,
                 start_color: str = "a", offset: float = 0.0,
                 total_duration: Optional[float] = None) -> List[Scene]:
    scenes: List[Scene] = []

    for segment in segments:
        words = _words_of(segment)
        if not words:
            continue
        for chunk in _chunk(words, max_words, max_chars):
            text = " ".join(w.text for w in chunk).strip(PUNCT + " ")
            if not text:
                continue
            scenes.append(Scene(text=text, start=chunk[0].start + offset,
                                end=chunk[-1].end + offset, words=chunk))

    if not scenes:
        return scenes

    scenes.sort(key=lambda s: s.start)
    scenes = _fit_durations(scenes, min_scene, max_scene, total_duration)

    first = _kind(start_color)
    for i, scene in enumerate(scenes):
        scene.kind = first if i % 2 == 0 else _other(first)
    return scenes


def _kind(name: str) -> str:
    """Accept 'a'/'b' and the older 'green'/'cream' names."""
    name = (name or "a").lower()
    if name in ("a", "green", "first"):
        return "a"
    if name in ("b", "cream", "second"):
        return "b"
    raise SystemExit(f"start_color must be a/b (or green/cream), got {name!r}")


def _other(kind: str) -> str:
    return "b" if kind == "a" else "a"


def _fit_durations(scenes: List[Scene], min_scene: float, max_scene: float,
                   total_duration: Optional[float]) -> List[Scene]:
    """Stretch / trim cards so each one is on screen for a comfortable time."""
    for i, scene in enumerate(scenes):
        nxt = scenes[i + 1].start if i + 1 < len(scenes) else (total_duration or scene.end + min_scene)
        if scene.duration < min_scene:
            scene.end = min(scene.start + min_scene, max(scene.end, nxt - 0.02))
        if scene.duration > max_scene:
            scene.end = scene.start + max_scene
        # never run into the next card
        scene.end = min(scene.end, nxt - 0.02) if nxt > scene.start else scene.end
        if scene.end <= scene.start:
            scene.end = scene.start + 0.6
    return scenes


def describe(scenes: Sequence[Scene]) -> str:
    lines = []
    for i, s in enumerate(scenes, 1):
        lines.append(f"{i:02d}  {s.start:6.2f}–{s.end:6.2f}  {s.kind:<5}  {s.text}")
    return "\n".join(lines)

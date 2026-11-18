"""Speech-to-text with word timestamps, plus transcript (de)serialisation.

Two backends are supported:

* faster-whisper  (default, 4-8x faster on CPU, `pip install faster-whisper`)
* openai-whisper  (the reference implementation, `pip install openai-whisper`)

Both return the same shape:

    [{"start": 0.0, "end": 2.4, "text": "kahani meri",
      "words": [{"start": 0.0, "end": 0.6, "word": "kahani"}, ...]}, ...]
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

Segment = Dict


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def transcribe(audio_path: str, model: str = "small", language: Optional[str] = None,
               backend: str = "faster-whisper", device: str = "auto",
               compute_type: str = "int8", verbose: bool = True) -> List[Segment]:
    if backend == "faster-whisper":
        return _faster_whisper(audio_path, model, language, device, compute_type, verbose)
    if backend == "openai-whisper":
        return _openai_whisper(audio_path, model, language, verbose)
    raise SystemExit(f"unknown backend {backend!r} (use faster-whisper or openai-whisper)")


def read_wav_float32(path: str, sample_rate: int = 16000):
    """Load a PCM wav as float32 mono in [-1, 1] (no PyAV needed)."""
    import wave

    import numpy as np

    with wave.open(path, "rb") as fh:
        if fh.getframerate() != sample_rate:
            raise SystemExit(f"expected a {sample_rate} Hz wav, got {fh.getframerate()} Hz")
        if fh.getsampwidth() != 2:
            raise SystemExit("expected 16-bit PCM wav")
        channels = fh.getnchannels()
        raw = fh.readframes(fh.getnframes())
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data


def _faster_whisper(audio_path, model, language, device, compute_type, verbose) -> List[Segment]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper is not installed: pip install faster-whisper")

    if verbose:
        print(f"[whisper] loading faster-whisper model {model!r} ({device}, {compute_type})")
    wm = WhisperModel(model, device=device, compute_type=compute_type)
    # Decode the wav ourselves instead of letting faster-whisper use PyAV:
    # the av API changes between releases and breaks the audio loader.
    audio = read_wav_float32(audio_path)
    segments, info = wm.transcribe(
        audio, language=language, vad_filter=True,
        word_timestamps=True, beam_size=5,
        condition_on_previous_text=False,
    )
    if verbose:
        print(f"[whisper] language={info.language} (p={info.language_probability:.2f})")

    out: List[Segment] = []
    for seg in segments:
        words = [{"start": float(w.start), "end": float(w.end), "word": _clean(w.word)}
                 for w in (seg.words or []) if w.word and w.word.strip()]
        text = _clean(seg.text)
        if not text:
            continue
        out.append({"start": float(seg.start), "end": float(seg.end), "text": text, "words": words})
    return out


def _openai_whisper(audio_path, model, language, verbose) -> List[Segment]:
    try:
        import whisper
    except ImportError:
        raise SystemExit("openai-whisper is not installed: pip install openai-whisper")

    if verbose:
        print(f"[whisper] loading openai-whisper model {model!r}")
    wm = whisper.load_model(model)
    result = wm.transcribe(audio_path, language=language, word_timestamps=True, verbose=None)
    out: List[Segment] = []
    for seg in result.get("segments", []):
        words = [{"start": float(w["start"]), "end": float(w["end"]), "word": _clean(w["word"])}
                 for w in seg.get("words", []) if w.get("word", "").strip()]
        text = _clean(seg.get("text", ""))
        if text:
            out.append({"start": float(seg["start"]), "end": float(seg["end"]),
                        "text": text, "words": words})
    return out


# --------------------------------------------------------------------------
# transcript io
# --------------------------------------------------------------------------
def save_transcript(segments: List[Segment], path: str) -> None:
    with open(path, "w", encoding="utf8") as fh:
        json.dump({"segments": segments}, fh, ensure_ascii=False, indent=2)


def load_transcript(path: str) -> List[Segment]:
    """Load a transcript from our JSON, or from a plain .srt file."""
    if path.lower().endswith(".srt"):
        return _load_srt(path)
    with open(path, encoding="utf8") as fh:
        data = json.load(fh)
    segments = data["segments"] if isinstance(data, dict) else data
    cleaned = []
    for seg in segments:
        text = _clean(seg.get("text", ""))
        if not text:
            continue
        cleaned.append({
            "start": float(seg.get("start", 0.0)),
            "end": float(seg.get("end", seg.get("start", 0.0) + 1.0)),
            "text": text,
            "words": [{"start": float(w.get("start", 0.0)),
                       "end": float(w.get("end", 0.0)),
                       "word": _clean(w.get("word", w.get("text", "")))}
                      for w in seg.get("words", []) if (w.get("word") or w.get("text"))],
        })
    return cleaned


def _load_srt(path: str) -> List[Segment]:
    def ts(v: str) -> float:
        h, m, rest = v.strip().replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(rest)

    blocks = re.split(r"\n\s*\n", open(path, encoding="utf8").read().strip())
    out: List[Segment] = []
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        idx = 0 if "-->" not in lines[0] else 0
        for i, ln in enumerate(lines):
            if "-->" in ln:
                idx = i
                break
        start, end = [ts(p) for p in lines[idx].split("-->")[:2]]
        text = _clean(" ".join(lines[idx + 1:]))
        if text:
            out.append({"start": start, "end": end, "text": text, "words": []})
    return out

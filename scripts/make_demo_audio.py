#!/usr/bin/env python3
"""Generate the royalty-free ambient bed used by examples/demo_audio.wav.

    python scripts/make_demo_audio.py

Nothing is sampled or downloaded: four chords of sine partials plus a soft bell
per line, written straight to a wav file. Swap in your own song for real work.
"""
from __future__ import annotations

import os
import wave

import numpy as np

SR = 44100
DUR = 20.0
CHORDS = [(220.00, 261.63, 329.63), (174.61, 220.00, 261.63),
          (261.63, 329.63, 392.00), (196.00, 246.94, 293.66)]
BELLS = [0.0, 2.4, 4.8, 7.2, 9.6, 12.0, 14.4, 16.8]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "examples", "demo_audio.wav")


def main() -> int:
    n = int(DUR * SR)
    t = np.arange(n) / SR
    mix = np.zeros(n)

    seg = DUR / len(CHORDS)
    for i, chord in enumerate(CHORDS):
        s0 = i * seg
        env = np.clip((t - s0) / 1.2, 0, 1) * np.clip((s0 + seg + 0.9 - t) / 1.2, 0, 1)
        env = np.clip(env, 0, 1) ** 1.5
        sig = np.zeros(n)
        for j, f in enumerate(chord):
            for det, amp in ((1.0, 1.0), (1.0025, 0.5), (0.9975, 0.5)):
                vib = 1 + 0.0012 * np.sin(2 * np.pi * 0.18 * t + j)
                sig += amp * np.sin(2 * np.pi * f * det * vib * t + j * 1.7)
            sig += 0.18 * np.sin(2 * np.pi * f * 2 * t)
        mix += 0.055 * env * sig

    for i, b0 in enumerate(BELLS):
        idx = t >= b0
        tt = t[idx] - b0
        f = [880.0, 987.77, 1174.66, 1318.51][i % 4]
        mix[idx] += 0.05 * np.exp(-tt * 3.2) * (tt < 2.2) * (
            np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2.01 * tt))

    # one-pole low-pass, then fades
    out, prev = np.zeros(n), 0.0
    for i in range(n):
        prev += 0.16 * (mix[i] - prev)
        out[i] = prev
    out *= np.clip(t / 1.2, 0, 1) * np.clip((DUR - t) / 1.4, 0, 1)
    out = out / max(1e-9, np.abs(out).max()) * 0.55

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with wave.open(OUT, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SR)
        fh.writeframes((out * 32767).astype(np.int16).tobytes())
    print(f"wrote {OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB, {DUR:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

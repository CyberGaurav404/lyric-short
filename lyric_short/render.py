"""Frame renderer: backgrounds, cards, transitions and word reveals -> ffmpeg."""
from __future__ import annotations

import os
import shutil
import tempfile
from typing import Iterator, Optional, Sequence

from PIL import Image

from . import art, media
from .config import Theme
from .scenes import Scene


def smooth(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


class Renderer:
    def __init__(self, scenes: Sequence[Scene], theme: Theme,
                 font_path: Optional[str] = None, duration: Optional[float] = None,
                 seed: int = 7):
        self.theme = theme
        self.scenes = list(scenes)
        self.font_path = art.resolve_font(font_path)
        self.seed = seed
        self.bg = art.build_background(theme, seed=seed)
        self.cards = {kind: art.build_card(theme, kind) for kind in ("a", "b")}
        self.card_w, self.card_h = theme.card_size()
        self.shadow = art.build_shadow(theme)
        self.grain = art.build_grain(theme, seed=seed) if theme.grain > 0 else []
        self.text_cache = {
            (s.text, s.kind): art.build_text_layers(
                s.text, self.cards[s.kind][1], self.card_w, self.card_h,
                self.font_path, theme)
            for s in self.scenes
        }
        self.handle = art.build_handle(theme.handle, theme, self.font_path)
        heart_size = int(min(theme.width, theme.height) * 0.22)
        self.heart = art.build_heart(heart_size, (250, 246, 236, 235))
        self.heart_glow = art.build_heart(int(heart_size * 1.2), (200, 235, 220, 120), blur=26)

        last_end = max([s.end for s in self.scenes], default=0.0)
        self.duration = float(duration if duration is not None
                              else max(last_end + theme.outro, theme.intro + 2.0))

    # ------------------------------------------------------------------
    def frame_at(self, t: float) -> Image.Image:
        theme = self.theme
        frame = self.bg.copy()

        if t < theme.intro + 0.5:
            self._draw_intro(frame, t)

        for scene in self.scenes:
            if t < scene.start - 0.05 or t > scene.end + theme.crossfade + 0.05:
                continue
            alpha, offset, scale = self._transition_state(scene, t)
            if alpha <= 0.01:
                continue
            frame = self._draw_card(frame, scene, t, alpha, offset, scale)

        if self.handle is not None and t > theme.intro * 0.5:
            ha = smooth((t - theme.intro * 0.5) / 0.8)
            layer = self.handle.copy()
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * ha)))
            frame.paste(layer, (int(theme.width / 2 - layer.width / 2),
                                int(theme.height * 0.915)), layer)

        if self.grain and theme.grain > 0:
            plate = self.grain[int(t * 12) % len(self.grain)]
            frame = Image.blend(frame, plate, theme.grain)

        if t < 0.45:
            frame = Image.blend(Image.new("RGB", frame.size, (0, 0, 0)), frame, smooth(t / 0.45))
        if t > self.duration - 0.9:
            frame = Image.blend(frame, Image.new("RGB", frame.size, (0, 0, 0)),
                                smooth((t - (self.duration - 0.9)) / 0.9))
        return frame

    # ------------------------------------------------------------------
    def _draw_intro(self, frame: Image.Image, t: float) -> None:
        theme = self.theme
        alpha = smooth(t / 0.7) * (1.0 - smooth((t - (theme.intro - 0.6)) / 0.6))
        if alpha <= 0.01:
            return
        scale = 0.92 + 0.10 * smooth(t / 1.4)
        for img, weight in ((self.heart_glow, 0.55), (self.heart, 0.95)):
            size = int(img.width * scale)
            layer = img.resize((size, size), Image.LANCZOS)
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha * weight)))
            frame.paste(layer, (int(theme.width / 2 - size / 2),
                                int(theme.height / 2 - size / 2)), layer)

    def _transition_state(self, scene: Scene, t: float):
        """(alpha, y offset in px, extra scale) for this card at time t."""
        theme = self.theme
        cf = max(0.08, theme.crossfade)
        enter = smooth((t - scene.start) / cf)
        leave = smooth((t - scene.end) / cf)
        alpha = enter * (1.0 - leave)

        if theme.transition == "slide":
            dy = (1 - ease_out((t - scene.start) / cf)) * theme.height * 0.05
            dy -= ease_out(leave) * theme.height * 0.05
            return alpha, dy, 1.0
        if theme.transition == "pop":
            scale = 0.94 + 0.06 * ease_out((t - scene.start) / cf)
            scale += 0.02 * ease_out(leave)
            return alpha, 0.0, scale
        return alpha, 0.0, 1.0

    def _draw_card(self, frame: Image.Image, scene: Scene, t: float,
                   alpha: float, offset: float, extra_scale: float) -> Image.Image:
        theme = self.theme
        life = max(0.001, scene.end - scene.start + theme.crossfade)
        progress = min(max(t - scene.start, 0.0), life) / life
        zoom = (1.0 + theme.zoom * progress) * extra_scale
        dw, dh = int(self.card_w * zoom), int(self.card_h * zoom)
        layer = self.cards[scene.kind][0].resize((dw, dh), Image.BILINEAR)
        k = zoom / theme.supersample

        x = int(theme.width / 2 - dw / 2)
        y = int(theme.height * theme.card_center_y - dh / 2 + offset)

        if self.shadow is not None and theme.card_mode != "fullbleed":
            sh = self.shadow.resize((int(self.shadow.width * zoom / theme.supersample),
                                     int(self.shadow.height * zoom / theme.supersample)),
                                    Image.BILINEAR)
            sh.putalpha(sh.getchannel("A").point(lambda v: int(v * alpha)))
            frame.paste(sh, (int(x - (sh.width - dw) / 2),
                             int(y - (sh.height - dh) / 2)), sh)

        for word, wl in zip(scene.words, self.text_cache[(scene.text, scene.kind)]):
            t0 = max(0.0, word.start - scene.start)
            wa = smooth((t - scene.start - t0) / theme.word_fade)
            if wa <= 0.01:
                continue
            size = (max(1, int(wl.image.width * k)), max(1, int(wl.image.height * k)))
            img = wl.image.resize(size, Image.BILINEAR)
            img.putalpha(img.getchannel("A").point(lambda v: int(v * wa * alpha)))
            dy = int((1 - wa) * theme.rise)
            layer.alpha_composite(img, (int(wl.x * k), int(wl.y * k) + dy))

        if alpha < 0.999:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        frame.paste(layer, (x, y), layer)
        return frame

    # ------------------------------------------------------------------
    def frames(self) -> Iterator[Image.Image]:
        n = int(round(self.duration * self.theme.fps))
        for i in range(n):
            yield self.frame_at(i / self.theme.fps)

    def render(self, out_path: str, audio_path: Optional[str] = None,
               crf: int = 20, preset: str = "medium", verbose: bool = True) -> str:
        theme = self.theme
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        if verbose:
            print(f"[render] {theme.name} · {theme.width}x{theme.height} @ {theme.fps}fps · "
                  f"{self.duration:.2f}s · {len(self.scenes)} cards -> {out_path}")
        try:
            media.encode_video(self.frames(), out_path, theme.width, theme.height,
                               theme.fps, crf=crf, preset=preset, audio=audio_path,
                               audio_delay=theme.intro)
        except RuntimeError:
            # Very small machines can run out of memory on a long pipe; a PNG
            # sequence on disk always works.
            if verbose:
                print("[render] pipe encode failed, retrying via a PNG sequence")
            tmp = tempfile.mkdtemp(prefix="lyricshort-")
            try:
                for i, frame in enumerate(self.frames()):
                    frame.save(os.path.join(tmp, f"{i:05d}.png"))
                media.encode_from_dir(tmp, out_path, theme.fps, crf=crf,
                                      preset=preset, audio=audio_path,
                                      audio_delay=theme.intro)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        return out_path

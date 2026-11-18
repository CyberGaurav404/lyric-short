"""Drawing primitives: backgrounds, cards, ornaments, text and the intro heart.

Everything is drawn with Pillow, so the project has no native UI dependency and
the same code renders on Linux, macOS and Windows.
"""
from __future__ import annotations

import math
import os
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import RGB, Theme

FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/TTF/DejaVuSerif.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "C:/Windows/Fonts/times.ttf",
]

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED_FONT = os.path.join(HERE, "..", "assets", "fonts", "Playfair.ttf")


def resolve_font(path: Optional[str] = None) -> str:
    """Explicit path > bundled Playfair > any serif installed on the machine."""
    for candidate in (path, BUNDLED_FONT, *FALLBACK_FONTS):
        if candidate and os.path.exists(candidate):
            return os.path.abspath(candidate)
    raise SystemExit(
        "No serif font found. Run `python scripts/fetch_fonts.py` or pass --font.")


def load_font(path: str, size: int, weight: int = 500) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(path, size)
    try:  # variable fonts (Playfair, Cormorant, ...) expose a weight axis
        font.set_variation_by_axes([weight])
    except Exception:
        pass
    return font


# --------------------------------------------------------------------------
# backgrounds
# --------------------------------------------------------------------------
def _radial(w: int, h: int, cx: float, cy: float, rx: float, ry: float) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - cx) / (w * rx)) ** 2 + ((yy - cy) / (h * ry)) ** 2)
    return np.clip(1.0 - r, 0, 1)


def _base(theme: Theme, glow: np.ndarray) -> np.ndarray:
    base = np.zeros((theme.height, theme.width, 3), np.float32)
    for i, c in enumerate(theme.bg_color):
        base[..., i] = c + glow * theme.glow_color[i]
    return base


def build_background(theme: Theme, seed: int = 7) -> Image.Image:
    w, h = theme.width, theme.height
    rng = np.random.default_rng(seed)
    cy = h * theme.card_center_y
    glow = _radial(w, h, w / 2, cy, 0.72, 0.52) ** 2.2

    if theme.bg_mode == "paper":
        base = _base(theme, glow * 0.9)
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
        fibre = rng.normal(0, 7, (h, w, 1)).repeat(3, axis=2)
        arr = np.clip(np.asarray(img.convert("RGB"), np.float32) + fibre, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
        img = Image.alpha_composite(img, _speckles(w, h, rng, 140, (120, 110, 95), (5, 18)))
        return _finish(img, theme, light=True)

    if theme.bg_mode == "gradient":
        base = _base(theme, glow)
        # a soft diagonal wash so the frame is not a flat disc
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        diag = np.clip((xx / w * 0.6 + yy / h * 0.4), 0, 1)[..., None]
        base *= (0.86 + 0.30 * diag)
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
        img = Image.alpha_composite(img, _speckles(w, h, rng, 120, (255, 245, 235), (4, 14)))
        return _finish(img, theme)

    # bokeh / stars share the same base, different particles
    base = _base(theme, glow)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")

    if theme.bg_mode == "stars":
        img = Image.alpha_composite(img, _speckles(w, h, rng, int(420 * w * h / (1920 * 1080)),
                                                   (235, 240, 255), (40, 150), radius=(0.6, 1.8)))
        img = Image.alpha_composite(img, _speckles(w, h, rng, 26, (200, 220, 255), (18, 55),
                                                   radius=(6, 18), blur=7))
    else:
        bokeh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(bokeh)
        for _ in range(90):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            rad = rng.uniform(6, 42) * (w / 1920)
            d.ellipse([x - rad, y - rad, x + rad, y + rad],
                      fill=(214, 230, 220, int(rng.uniform(4, 16))))
        img = Image.alpha_composite(img, bokeh.filter(ImageFilter.GaussianBlur(9)))
        img = Image.alpha_composite(img, _speckles(w, h, rng, int(220 * w * h / (1920 * 1080)),
                                                   (240, 245, 235), (25, 95)))
    return _finish(img, theme)


def _speckles(w, h, rng, count, color, alpha_range, radius=(0.8, 2.4), blur=0.7) -> Image.Image:
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(int(count)):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        rad = rng.uniform(*radius)
        d.ellipse([x - rad, y - rad, x + rad, y + rad],
                  fill=color + (int(rng.uniform(*alpha_range)),))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def _finish(img: Image.Image, theme: Theme, light: bool = False) -> Image.Image:
    w, h = theme.width, theme.height
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w * 0.72)) ** 2 + ((yy - h * theme.card_center_y) / (h * 0.52)) ** 2)
    lo, hi = (0.90, 1.04) if light else (0.25, 1.0)
    vig = np.clip(1.35 - 1.15 * r, lo, hi)[..., None]
    arr = np.clip(np.asarray(img.convert("RGB"), np.float32) * vig, 0, 255)
    return Image.fromarray(arr.astype(np.uint8)).convert("RGB")


# --------------------------------------------------------------------------
# ornaments
# --------------------------------------------------------------------------
def _leaf_mask(length: float, width: float) -> Image.Image:
    pad = 3
    top, bot = [], []
    for i in range(41):
        u = i / 40.0
        y = (width / 2) * (math.sin(math.pi * u) ** 0.75)
        top.append((u * length, -y))
        bot.append((u * length, y))
    img = Image.new("L", (int(length + 2 * pad), int(width + 2 * pad)), 0)
    ImageDraw.Draw(img).polygon([(x + pad, y + pad) for x, y in top + bot[::-1]], fill=255)
    return img


def leaf(base: Image.Image, cx: float, cy: float, length: float, width: float,
         angle: float, fill: Tuple[int, int, int, int]) -> None:
    mask = _leaf_mask(length, width).rotate(-angle, resample=Image.BICUBIC, expand=True)
    tint = Image.new("RGBA", mask.size, fill[:3] + (0,))
    tint.putalpha(mask.point(lambda v: int(v * fill[3] / 255)))
    base.alpha_composite(tint, (int(cx - mask.width / 2), int(cy - mask.height / 2)))


def rosette(base: Image.Image, cx: float, cy: float, rad: float,
            fill: Tuple[int, int, int, int], petals: int = 12,
            petal_w: float = 0.15, petal_l: float = 0.52,
            inner: float = 0.26, center: bool = True) -> None:
    for i in range(petals):
        a = 2 * math.pi * i / petals - math.pi / 2
        pr = rad * (inner + petal_l / 2)
        leaf(base, cx + math.cos(a) * pr, cy + math.sin(a) * pr,
             rad * petal_l, rad * petal_w * 2, math.degrees(a), fill)
    if center:
        r = rad * inner * 0.72
        ImageDraw.Draw(base).ellipse([cx - r, cy - r, cx + r, cy + r],
                                     outline=fill[:3] + (fill[3],),
                                     width=max(2, int(rad * 0.075)))


def _orn_botanical(orn: Image.Image, w: int, h: int, c: Tuple[int, int, int], a1, a2) -> None:
    leaf(orn, w * 0.048, h * 0.985, h * 0.145, h * 0.055, -62, a1)
    leaf(orn, w * 0.062, h * 0.980, h * 0.105, h * 0.040, -34, a2)
    leaf(orn, w * 0.055, h * 0.985, h * 0.080, h * 0.030, -88, a2)
    leaf(orn, w * 0.098, h * 0.972, h * 0.060, h * 0.024, -18, a2)
    rosette(orn, w * 0.895, h * 0.098, h * 0.082, a1, petals=12, petal_w=0.15, petal_l=0.52)
    rosette(orn, w * 0.935, h * 0.180, h * 0.034, a2, petals=8, petal_w=0.20, petal_l=0.5, center=False)
    rosette(orn, w * 0.5, h * 0.945, h * 0.028, a1, petals=6, petal_w=0.30, petal_l=0.6, inner=0.22)


def _orn_arcs(orn: Image.Image, w: int, h: int, c: Tuple[int, int, int], a1, a2) -> None:
    d = ImageDraw.Draw(orn)
    cx, cy, rad = w * 0.90, h * 0.10, h * 0.085
    for i, (k, alpha) in enumerate(((1.0, a1[3]), (0.72, a2[3]), (0.44, a2[3]))):
        r = rad * k
        d.arc([cx - r, cy - r, cx + r, cy + r], start=150, end=350,
              fill=c + (alpha,), width=max(2, int(h * 0.004)))
    for i in range(3):
        x = w * (0.07 + i * 0.018)
        d.ellipse([x - h * 0.004, h * 0.945 - h * 0.004, x + h * 0.004, h * 0.945 + h * 0.004],
                  fill=c + (a1[3],))


def _orn_lines(orn: Image.Image, w: int, h: int, c: Tuple[int, int, int], a1, a2) -> None:
    d = ImageDraw.Draw(orn)
    t = max(2, int(h * 0.0035))
    d.line([(w * 0.06, h * 0.075), (w * 0.16, h * 0.075)], fill=c + (a1[3],), width=t)
    d.line([(w * 0.06, h * 0.075), (w * 0.06, h * 0.135)], fill=c + (a1[3],), width=t)
    d.line([(w * 0.94, h * 0.925), (w * 0.84, h * 0.925)], fill=c + (a2[3],), width=t)
    d.line([(w * 0.94, h * 0.925), (w * 0.94, h * 0.865)], fill=c + (a2[3],), width=t)


ORNAMENTS = {
    "botanical": _orn_botanical,
    "arcs": _orn_arcs,
    "lines": _orn_lines,
    "none": lambda *a, **k: None,
}


# --------------------------------------------------------------------------
# cards
# --------------------------------------------------------------------------
def build_card(theme: Theme, kind: str) -> Tuple[Image.Image, RGB]:
    """Bake one card at supersample scale: fill, ornaments and edge treatment."""
    s = theme.supersample
    cw, ch = theme.card_size()
    w, h = int(cw * s), int(ch * s)
    fill, text_color, orn_color = theme.colors_for(kind)

    top = tuple(min(255, int(c * 1.07)) for c in fill)
    bot = tuple(max(0, int(c * 0.90)) for c in fill)
    grad = np.zeros((h, w, 3), np.uint8)
    for i in range(3):
        grad[..., i] = np.linspace(top[i], bot[i], h)[:, None].astype(np.uint8)
    img = Image.fromarray(grad).convert("RGBA")

    orn = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    a1 = orn_color + (theme.ornament_alpha,)
    a2 = orn_color + (int(theme.ornament_alpha * 0.7),)
    ORNAMENTS.get(theme.ornament, ORNAMENTS["none"])(orn, w, h, orn_color, a1, a2)
    img = Image.alpha_composite(img, orn)

    d = ImageDraw.Draw(img)
    if theme.card_mode == "frame":
        m = int(11 * s)
        d.rounded_rectangle([m, m, w - m, h - m], radius=int(3 * s),
                            outline=orn_color + (theme.border_alpha,),
                            width=max(1, int(1.6 * s)))
        img = img.filter(ImageFilter.GaussianBlur(0.4))
    elif theme.card_mode == "rounded":
        radius = int(h * 0.035)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
        img.putalpha(mask)
        if theme.border_alpha > 20:
            d.rounded_rectangle([int(1.5 * s), int(1.5 * s), w - int(1.5 * s), h - int(1.5 * s)],
                                radius=radius, outline=orn_color + (theme.border_alpha,),
                                width=max(1, int(1.4 * s)))
    return img, text_color


def build_shadow(theme: Theme) -> Optional[Image.Image]:
    """Soft drop shadow that sits under a floating card."""
    if not theme.shadow:
        return None
    s = theme.supersample
    cw, ch = theme.card_size()
    w, h = int(cw * s), int(ch * s)
    pad = int(min(w, h) * 0.10)
    shadow = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    radius = int(h * 0.035) if theme.card_mode == "rounded" else int(3 * s)
    ImageDraw.Draw(shadow).rounded_rectangle(
        [pad, pad + int(h * 0.012), pad + w, pad + h + int(h * 0.012)],
        radius=radius, fill=(0, 0, 0, 175))
    return shadow.filter(ImageFilter.GaussianBlur(int(pad * 0.55)))


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------
class WordLayer:
    __slots__ = ("image", "x", "y")

    def __init__(self, image: Image.Image, x: float, y: float):
        self.image, self.x, self.y = image, x, y


def build_text_layers(text: str, color: RGB, card_w: int, card_h: int,
                      font_path: str, theme: Theme, max_lines: int = 3) -> List[WordLayer]:
    """Lay the line out (wrapping if needed) and return one RGBA layer per word."""
    s = theme.supersample
    cw, ch = card_w * s, card_h * s
    max_width = cw * theme.max_text_width
    size = int(ch * theme.text_size)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))

    def wrap(font) -> List[str]:
        lines, cur = [], ""
        for word in text.split():
            trial = f"{cur} {word}".strip()
            if probe.textbbox((0, 0), trial, font=font)[2] <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    font = load_font(font_path, size, theme.font_weight)
    lines = wrap(font)
    while (len(lines) > max_lines or
           any(probe.textbbox((0, 0), ln, font=font)[2] > max_width for ln in lines)) and size > 18:
        size = int(size * 0.92)
        font = load_font(font_path, size, theme.font_weight)
        lines = wrap(font)

    asc, desc = font.getmetrics()
    line_h = (asc + desc) * 1.18
    space = max(int(size * 0.28),
                probe.textbbox((0, 0), "i i", font=font)[2] - 2 * probe.textbbox((0, 0), "i", font=font)[2])

    layers: List[WordLayer] = []
    block_h = line_h * len(lines)
    y0 = ch / 2 - block_h / 2
    for li, line in enumerate(lines):
        widths = [probe.textbbox((0, 0), wd, font=font)[2] for wd in line.split()]
        total = sum(widths) + space * (len(widths) - 1)
        x = cw / 2 - total / 2
        for word, wd in zip(line.split(), widths):
            pad = int(theme.glow * s) + int(size * 0.2)
            tw, th = int(wd + 2 * pad), int(asc + desc + 2 * pad)
            core = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            ImageDraw.Draw(core).text((pad, pad * 0.9), word, font=font, fill=color + (255,))
            if theme.glow > 0:
                glow = core.filter(ImageFilter.GaussianBlur(theme.glow * s * 0.6))
                glow.putalpha(glow.getchannel("A").point(lambda v: int(v * 0.75)))
                core = Image.alpha_composite(glow, core)
            layers.append(WordLayer(core, x - pad, y0 + li * line_h - pad))
            x += wd + space
    return layers


def build_handle(text: str, theme: Theme, font_path: str) -> Optional[Image.Image]:
    if not text:
        return None
    size = max(14, int(theme.height * theme.handle_size))
    font = load_font(font_path, size, 400)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    w = probe.textbbox((0, 0), text, font=font)[2]
    layer = Image.new("RGBA", (int(w + size), int(size * 2)), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((size / 2, size * 0.3), text, font=font,
                               fill=theme.handle_color + (215,))
    return layer


def build_heart(size: int, color: Tuple[int, int, int, int], blur: float = 0) -> Image.Image:
    s = size / 34.0
    pts = []
    for i in range(240):
        t = 2 * math.pi * i / 240
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((size / 2 + x * s * 0.62, size / 2 + y * s * 0.62))
    img = Image.new("RGBA", (int(size), int(size)), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon(pts, fill=color)
    return img.filter(ImageFilter.GaussianBlur(blur)) if blur else img


def build_grain(theme: Theme, count: int = 4, seed: int = 3) -> List[Image.Image]:
    """A few noise plates to cycle through, so grain does not look frozen."""
    rng = np.random.default_rng(seed)
    plates = []
    for _ in range(count):
        noise = rng.normal(128, 26, (theme.height, theme.width)).clip(0, 255).astype(np.uint8)
        plates.append(Image.fromarray(noise, "L").convert("RGB"))
    return plates

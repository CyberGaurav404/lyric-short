"""Drawing primitives: background, cards, ornaments, text and the intro heart.

Everything is drawn with Pillow so the project has no native UI dependency.
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
    """Find a usable serif font: explicit path > bundled > system fallback."""
    for candidate in (path, BUNDLED_FONT, *FALLBACK_FONTS):
        if candidate and os.path.exists(candidate):
            return os.path.abspath(candidate)
    raise SystemExit(
        "No serif font found. Run `python scripts/fetch_fonts.py` or pass --font."
    )


def load_font(path: str, size: int, weight: int = 500) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(path, size)
    try:  # variable fonts (Playfair, Cormorant, ...) accept a weight axis
        font.set_variation_by_axes([weight])
    except Exception:
        pass
    return font


# --------------------------------------------------------------------------
# background
# --------------------------------------------------------------------------
def build_background(theme: Theme, seed: int = 7) -> Image.Image:
    w, h = theme.width, theme.height
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h * theme.card_center_y
    r = np.sqrt(((xx - cx) / (w * 0.72)) ** 2 + ((yy - cy) / (h * 0.52)) ** 2)
    glow = np.clip(1.0 - r, 0, 1) ** 2.2

    base = np.zeros((h, w, 3), np.float32)
    for i, c in enumerate(theme.bg_color):
        base[..., i] = c + glow * theme.glow_color[i]
    vignette = np.clip(1.35 - 1.15 * r, 0.25, 1.0)[..., None]
    base *= vignette
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")

    bokeh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(bokeh)
    for _ in range(90):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        rad = rng.uniform(6, 42) * (w / 1920)
        d.ellipse([x - rad, y - rad, x + rad, y + rad],
                  fill=(214, 230, 220, int(rng.uniform(4, 16))))
    img = Image.alpha_composite(img, bokeh.filter(ImageFilter.GaussianBlur(9)))

    sparks = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(sparks)
    for _ in range(int(220 * (w * h) / (1920 * 1080))):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        rad = rng.uniform(0.8, 2.4)
        d.ellipse([x - rad, y - rad, x + rad, y + rad],
                  fill=(240, 245, 235, int(rng.uniform(25, 95))))
    img = Image.alpha_composite(img, sparks.filter(ImageFilter.GaussianBlur(0.7)))
    return img.convert("RGB")


# --------------------------------------------------------------------------
# ornaments
# --------------------------------------------------------------------------
def _leaf_mask(length: float, width: float) -> Image.Image:
    pad = 3
    pts_top, pts_bot = [], []
    for i in range(41):
        u = i / 40.0
        y = (width / 2) * (math.sin(math.pi * u) ** 0.75)
        pts_top.append((u * length, -y))
        pts_bot.append((u * length, y))
    img = Image.new("L", (int(length + 2 * pad), int(width + 2 * pad)), 0)
    ImageDraw.Draw(img).polygon([(x + pad, y + pad) for x, y in pts_top + pts_bot[::-1]], fill=255)
    return img


def leaf(base: Image.Image, cx: float, cy: float, length: float, width: float,
         angle: float, fill: Tuple[int, int, int, int]) -> None:
    mask = _leaf_mask(length, width).rotate(-angle, resample=Image.BICUBIC, expand=True)
    tint = Image.new("RGBA", mask.size, fill[:3] + (0,))
    alpha = mask.point(lambda v: int(v * fill[3] / 255))
    tint.putalpha(alpha)
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


def build_card(theme: Theme, kind: str) -> Tuple[Image.Image, RGB]:
    """Bake one card (fill + gradient + ornaments + border) at supersample scale."""
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

    # bottom-left leaf cluster
    leaf(orn, w * 0.048, h * 0.985, h * 0.145, h * 0.055, -62, a1)
    leaf(orn, w * 0.062, h * 0.980, h * 0.105, h * 0.040, -34, a2)
    leaf(orn, w * 0.055, h * 0.985, h * 0.080, h * 0.030, -88, a2)
    leaf(orn, w * 0.098, h * 0.972, h * 0.060, h * 0.024, -18, a2)

    # top-right rosette
    rosette(orn, w * 0.895, h * 0.098, h * 0.082, a1, petals=12, petal_w=0.15, petal_l=0.52)
    rosette(orn, w * 0.935, h * 0.180, h * 0.034, a2, petals=8, petal_w=0.20, petal_l=0.5, center=False)

    # bottom-centre blossom
    rosette(orn, w * 0.5, h * 0.945, h * 0.028, a1, petals=6, petal_w=0.30, petal_l=0.6, inner=0.22)

    img = Image.alpha_composite(img, orn)

    m = int(11 * s)
    ImageDraw.Draw(img).rounded_rectangle(
        [m, m, w - m, h - m], radius=int(3 * s),
        outline=orn_color + (theme.border_alpha,), width=max(1, int(1.6 * s)))
    return img.filter(ImageFilter.GaussianBlur(0.4)), text_color


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------
class WordLayer:
    __slots__ = ("image", "x", "y")

    def __init__(self, image: Image.Image, x: float, y: float):
        self.image, self.x, self.y = image, x, y


def build_text_layers(text: str, color: RGB, card_w: int, card_h: int,
                      font_path: str, theme: Theme,
                      max_lines: int = 3) -> List[WordLayer]:
    """Lay the line out (wrapping if needed) and return one RGBA layer per word."""
    s = theme.supersample
    cw, ch = card_w * s, card_h * s
    max_width = cw * theme.max_text_width
    size = int(ch * theme.text_size)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))

    def wrap(font) -> List[str]:
        words, lines, cur = text.split(), [], ""
        for word in words:
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
            tw, th = int(wd + size * 0.4), int(asc + desc + size * 0.3)
            layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((size * 0.2, size * 0.12), word, font=font, fill=color + (255,))
            layers.append(WordLayer(layer, x, y0 + li * line_h))
            x += wd + space
    return layers


def build_handle(text: str, theme: Theme, font_path: str) -> Optional[Image.Image]:
    if not text:
        return None
    size = max(14, int(theme.height * theme.handle_size))
    font = load_font(font_path, size, 400)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    w, h = probe.textbbox((0, 0), text, font=font)[2], size * 2
    layer = Image.new("RGBA", (int(w + size), int(h)), (0, 0, 0, 0))
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

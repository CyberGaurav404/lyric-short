"""Design generation — a fresh look for every video.

The six styles in styles.py are *reference points*, not the product. An agent
should design the scene for the audio it was given: read the mood from the words
and the track, then compose a design from these primitives.

Two ways in:

    # the tool invents a design from a seed (deterministic, so it can be re-run)
    spec = generate(seed="song.mp3", mood="warm")

    # or hand-write one as JSON and render exactly that
    spec = load("designs/neon_rain.json")

Everything a design can say is in DesignSpec; `to_theme()` turns it into the
Theme the renderer understands.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

from .config import Palette, Theme, apply_canvas

RGB = Tuple[int, int, int]

# moods bias the generator; they are suggestions, not templates
MOODS = ["calm", "warm", "dark", "bold", "minimal", "playful"]

# per mood: hue windows (degrees), saturation/lightness ranges for the two cards,
# which backgrounds and transitions suit it, ornament sets, type feel
MOOD_RULES: Dict[str, dict] = {
    "calm": dict(hues=[(120, 190), (30, 60)], sat=(0.18, 0.38), light=(0.30, 0.78),
                 bg=["bokeh", "paper"], trans=["fade"], orn=["botanical", "none"],
                 card=["frame", "rounded"], grain=(0.0, 0.04), glow=(0.0, 0.0),
                 weight=(400, 500), text=(0.095, 0.105)),
    "warm": dict(hues=[(350, 30), (15, 45)], sat=(0.35, 0.60), light=(0.25, 0.80),
                 bg=["gradient"], trans=["slide", "fade"], orn=["none", "arcs"],
                 card=["rounded", "frame"], grain=(0.03, 0.08), glow=(0.0, 0.0),
                 weight=(400, 600), text=(0.10, 0.115)),
    "dark": dict(hues=[(210, 280), (170, 200)], sat=(0.25, 0.55), light=(0.10, 0.30),
                 bg=["stars", "gradient"], trans=["fade", "pop"], orn=["arcs", "lines"],
                 card=["frame", "rounded"], grain=(0.02, 0.07), glow=(0.0, 16.0),
                 weight=(400, 600), text=(0.095, 0.11)),
    "bold": dict(hues=[(0, 25), (200, 240)], sat=(0.55, 0.85), light=(0.35, 0.55),
                 bg=["gradient", "stars"], trans=["pop"], orn=["lines", "none"],
                 card=["fullbleed", "rounded"], grain=(0.04, 0.10), glow=(0.0, 0.0),
                 weight=(600, 700), text=(0.11, 0.13)),
    "minimal": dict(hues=[(20, 60), (140, 190)], sat=(0.05, 0.18), light=(0.60, 0.92),
                    bg=["paper"], trans=["fade"], orn=["none"],
                    card=["rounded"], grain=(0.0, 0.03), glow=(0.0, 0.0),
                    weight=(400, 400), text=(0.085, 0.10)),
    "playful": dict(hues=[(280, 340), (150, 200)], sat=(0.45, 0.75), light=(0.30, 0.75),
                    bg=["bokeh", "stars", "gradient"], trans=["pop", "slide"],
                    orn=["lines", "arcs", "botanical"], card=["rounded", "frame"],
                    grain=(0.02, 0.07), glow=(0.0, 10.0),
                    weight=(500, 700), text=(0.10, 0.125)),
}


# --------------------------------------------------------------------------
# colour helpers
# --------------------------------------------------------------------------
def _hls_to_rgb(h: float, l: float, s: float) -> RGB:
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h % 1.0, min(max(l, 0), 1), min(max(s, 0), 1))
    return (int(r * 255), int(g * 255), int(b * 255))


def luminance(rgb: RGB) -> float:
    """Perceived luminance, 0..1."""
    r, g, b = [c / 255 for c in rgb]
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: RGB, b: RGB) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def ensure_contrast(fill: RGB, text: RGB, target: float = 4.6) -> RGB:
    """Push the fill lighter or darker until the text clears `target`."""
    if contrast(fill, text) >= target:
        return fill
    import colorsys
    r, g, b = [c / 255 for c in fill]
    h, l, sat = colorsys.rgb_to_hls(r, g, b)
    toward_light = luminance(text) < 0.5          # dark text -> lighten the fill
    for _ in range(40):
        l = min(0.97, l + 0.02) if toward_light else max(0.03, l - 0.02)
        cand = _hls_to_rgb(h, l, sat)
        if contrast(cand, text) >= target:
            return cand
    return fill


def readable_text(fill: RGB, prefer_dark: bool = False) -> RGB:
    """Pick a text colour that actually reads on this fill."""
    light = (250, 248, 240)
    dark = (26, 30, 28)
    if prefer_dark:
        return dark if contrast(fill, dark) >= contrast(fill, light) else light
    return light if contrast(fill, light) >= contrast(fill, dark) else dark


# --------------------------------------------------------------------------
# the spec
# --------------------------------------------------------------------------
@dataclass
class DesignSpec:
    name: str = "custom"
    mood: str = "calm"

    palettes: List[Palette] = field(default_factory=list)
    bg_mode: str = "bokeh"
    bg_color: RGB = (5, 8, 7)
    glow_color: RGB = (16, 30, 25)

    card_mode: str = "frame"          # frame | rounded | fullbleed
    card_ratio: float = 0.88
    card_aspect: float = 1.34
    card_center_y: float = 0.47
    corner: float = 0.035             # corner radius as a fraction of card height

    ornament: str = "botanical"       # botanical | arcs | lines | none
    text_align: str = "center"        # center | left
    accent_rule: bool = False
    font_weight: int = 500
    text_size: float = 0.10

    transition: str = "fade"          # fade | slide | pop
    zoom: float = 0.03
    rise: int = 14
    grain: float = 0.0
    glow: float = 0.0
    shadow: bool = True

    handle_color: RGB = (200, 210, 205)
    notes: str = ""

    # ------------------------------------------------------------------
    def to_theme(self, canvas: str = "shorts") -> Theme:
        theme = Theme(
            name=self.name,
            palettes=[Palette(*p) if isinstance(p, (list, tuple)) else p
                      for p in (self.palettes or [Palette((74, 116, 99), (250, 248, 238), (234, 211, 195)),
                                                  Palette((234, 211, 195), (56, 82, 66), (74, 116, 99))])],
            bg_mode=self.bg_mode, bg_color=tuple(self.bg_color), glow_color=tuple(self.glow_color),
            card_mode=self.card_mode, card_ratio=self.card_ratio, card_aspect=self.card_aspect,
            card_center_y=self.card_center_y, ornament=self.ornament,
            text_align=self.text_align, accent_rule=self.accent_rule,
            font_weight=self.font_weight, text_size=self.text_size,
            transition=self.transition, zoom=self.zoom, rise=self.rise,
            grain=self.grain, glow=self.glow, shadow=self.shadow,
            handle_color=tuple(self.handle_color),
        )
        return apply_canvas(theme, canvas)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["palettes"] = [{"fill": list(p.fill), "text": list(p.text), "orn": list(p.orn)}
                         for p in self.palettes]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "DesignSpec":
        data = dict(data)
        palettes = [Palette(tuple(p["fill"]), tuple(p["text"]), tuple(p["orn"]))
                    for p in data.get("palettes", [])]
        data["palettes"] = palettes
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


# --------------------------------------------------------------------------
# generation
# --------------------------------------------------------------------------
def _rng(seed: str):
    import random
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _pick(rng, seq):
    return seq[rng.randrange(len(seq))]


def _pick_hue(rng, window) -> float:
    """A hue in degrees from a window that may wrap past 360 (e.g. 350..30)."""
    start, end = window
    if start <= end:
        return rng.uniform(start, end)
    span_a, span_b = 360 - start, end
    if rng.random() * (span_a + span_b) < span_a:
        return rng.uniform(start, 360)
    return rng.uniform(0, end)


def generate(seed: str = "", mood: Optional[str] = None, canvas: str = "shorts") -> DesignSpec:
    """Invent a design. Same seed + mood always gives the same design."""
    rng = _rng(f"{seed}:{mood or ''}")
    mood = mood or _pick(rng, MOODS)
    if mood not in MOOD_RULES:
        raise SystemExit(f"unknown mood {mood!r}; pick one of {', '.join(MOODS)}")
    rule = MOOD_RULES[mood]

    # two harmonious fills: one card leans light, the other dark or tinted
    h1 = _pick_hue(rng, rule["hues"][0]) / 360
    spread = rng.choice([0.03, 0.06, 0.10, 0.5])
    h2 = (h1 + spread) % 1.0
    s1 = rng.uniform(*rule["sat"])
    s2 = rng.uniform(*rule["sat"])
    l1, l2 = sorted((rng.uniform(*rule["light"]), rng.uniform(*rule["light"])))
    if abs(l1 - l2) < 0.18:                       # keep the two cards clearly apart
        l2 = min(0.94, l1 + 0.25)
    fill_a, fill_b = _hls_to_rgb(h1, l1, s1), _hls_to_rgb(h2, l2, s2)
    text_a = readable_text(fill_a)
    text_b = readable_text(fill_b, prefer_dark=l1 > 0.6)
    fill_a = ensure_contrast(fill_a, text_a)
    fill_b = ensure_contrast(fill_b, text_b)
    orn = _hls_to_rgb((h2 + 0.5) % 1.0, 0.78 if l1 < 0.5 else 0.42, min(0.9, s2 + 0.2))

    bg_mode = _pick(rng, rule["bg"])
    if bg_mode == "paper":
        bg_color = _hls_to_rgb(h1, rng.uniform(0.86, 0.92), rng.uniform(0.08, 0.18))
        glow_color = _hls_to_rgb(h1, 0.99, 0.05)
        handle = _hls_to_rgb(h1, 0.30, 0.12)
    else:
        bg_color = _hls_to_rgb(h1, rng.uniform(0.03, 0.08), rng.uniform(0.25, 0.55))
        glow_color = _hls_to_rgb(h1, rng.uniform(0.10, 0.22), rng.uniform(0.30, 0.60))
        handle = _hls_to_rgb(h1, 0.78, 0.25)

    card_mode = _pick(rng, rule["card"])
    spec = DesignSpec(
        name=f"{mood}-{seed[-6:] if seed else rng.randint(1000, 9999)}",
        mood=mood,
        palettes=[Palette(fill_a, text_a, orn), Palette(fill_b, text_b, orn)],
        bg_mode=bg_mode, bg_color=bg_color, glow_color=glow_color,
        card_mode=card_mode,
        card_ratio=round(rng.uniform(0.84, 0.94), 3) if card_mode != "fullbleed" else 1.0,
        card_aspect=round(rng.uniform(1.24, 1.42), 3),
        card_center_y=round(rng.uniform(0.44, 0.52), 3),
        corner=round(rng.uniform(0.0, 0.05), 3),
        ornament=_pick(rng, rule["orn"]),
        text_align=rng.choice(["center", "center", "left"]),
        accent_rule=rng.random() < 0.3,
        font_weight=rng.randrange(rule["weight"][0], rule["weight"][1] + 1, 100),
        text_size=round(rng.uniform(*rule["text"]), 3),
        transition=_pick(rng, rule["trans"]),
        zoom=round(rng.uniform(0.012, 0.04), 3),
        rise=rng.choice([10, 14, 18]),
        grain=round(rng.uniform(*rule["grain"]), 3),
        glow=round(rng.uniform(*rule["glow"]), 1),
        shadow=card_mode != "fullbleed",
        handle_color=handle,
        notes=f"generated for seed {seed!r}",
    )
    tag = hashlib.sha256(f"{seed}:{mood}:{canvas}".encode()).hexdigest()[:4]
    spec.name = f"{mood}-{tag}"
    return spec


# --------------------------------------------------------------------------
# io
# --------------------------------------------------------------------------
def load(path: str) -> DesignSpec:
    with open(path, encoding="utf8") as fh:
        return DesignSpec.from_dict(json.load(fh))


def save(spec: DesignSpec, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf8") as fh:
        json.dump(spec.to_dict(), fh, indent=2)


def describe(spec: DesignSpec) -> str:
    a, b = spec.palettes
    return (f"{spec.name} [{spec.mood}] bg={spec.bg_mode} card={spec.card_mode} "
            f"orn={spec.ornament} align={spec.text_align} trans={spec.transition} "
            f"a={a.fill} b={b.fill} grain={spec.grain} glow={spec.glow}")

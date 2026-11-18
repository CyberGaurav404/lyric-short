"""Theme = canvas + palette + card treatment + motion.

A "style" (see styles.py) is just a Theme with values filled in. Anything you can
see is a field here, so a new look never means touching the renderer.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List, Optional, Tuple

RGB = Tuple[int, int, int]


@dataclass
class Palette:
    """One card look: fill, text colour and ornament colour."""

    fill: RGB
    text: RGB
    orn: RGB


DEFAULT_PALETTES = [
    Palette((74, 116, 99), (250, 248, 238), (234, 211, 195)),   # green
    Palette((234, 211, 195), (56, 82, 66), (74, 116, 99)),      # cream
]


@dataclass
class Theme:
    name: str = "custom"

    # canvas
    width: int = 1080
    height: int = 1920
    fps: int = 30

    # card geometry
    card_ratio: float = 0.88          # card width / frame width
    card_aspect: float = 1.34         # card width / card height
    card_center_y: float = 0.47       # 0 = top, 1 = bottom
    max_text_width: float = 0.80      # fraction of card width used by text
    card_mode: str = "frame"          # frame | rounded | fullbleed

    # palette + background
    palettes: List[Palette] = field(default_factory=lambda: list(DEFAULT_PALETTES))
    bg_color: RGB = (5, 8, 7)
    glow_color: RGB = (16, 30, 25)
    bg_mode: str = "bokeh"            # bokeh | stars | gradient | paper
    ornament: str = "botanical"       # botanical | arcs | lines | none
    ornament_alpha: int = 215
    border_alpha: int = 110
    shadow: bool = True
    grain: float = 0.0                # 0..0.3 noise overlay
    glow: float = 0.0                 # text glow radius in px (baked once)

    # motion
    transition: str = "fade"          # fade | slide | pop
    zoom: float = 0.030
    rise: int = 14

    # type
    font_path: Optional[str] = None
    font_weight: int = 500
    text_size: float = 0.100          # fraction of card height
    handle: Optional[str] = None
    handle_size: float = 0.019
    handle_color: RGB = (196, 212, 202)

    # timing (seconds)
    intro: float = 1.5
    outro: float = 1.1
    crossfade: float = 0.35
    min_scene: float = 1.5
    max_scene: float = 4.0
    word_fade: float = 0.30

    # rendering
    supersample: float = 1.6

    # ------------------------------------------------------------------
    def colors_for(self, kind: str) -> Tuple[RGB, RGB, RGB]:
        """(fill, text, ornament) for card kind 'a' or 'b'."""
        palette = self.palettes[0 if kind == "a" else 1 % len(self.palettes)]
        return palette.fill, palette.text, palette.orn

    def card_size(self) -> Tuple[int, int]:
        if self.card_mode == "fullbleed":
            return self.width, self.height
        w = int(self.width * self.card_ratio)
        h = int(round(w / self.card_aspect))
        return w, h

    def with_(self, **kw) -> "Theme":
        return replace(self, **kw)


CANVAS_PRESETS = {
    "shorts": {"width": 1080, "height": 1920, "card_ratio": 0.88, "card_center_y": 0.47},
    "landscape": {"width": 1920, "height": 1080, "card_ratio": 0.58, "card_center_y": 0.5},
    "square": {"width": 1080, "height": 1080, "card_ratio": 0.80, "card_center_y": 0.5},
}


def apply_canvas(theme: Theme, preset: str) -> Theme:
    if preset not in CANVAS_PRESETS:
        raise SystemExit(f"unknown canvas {preset!r}; pick one of {', '.join(CANVAS_PRESETS)}")
    return theme.with_(**CANVAS_PRESETS[preset])

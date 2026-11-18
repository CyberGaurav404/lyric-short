"""Visual theme for the lyric short.

Everything the renderer needs to draw a card lives here, so a new look is
just a new Theme instance (or a new preset).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional, Tuple

RGB = Tuple[int, int, int]


@dataclass
class Theme:
    # canvas
    width: int = 1080
    height: int = 1920
    fps: int = 30

    # card
    card_ratio: float = 0.88          # card width as a fraction of frame width
    card_aspect: float = 1.34         # card width / card height
    card_center_y: float = 0.47       # 0 = top, 1 = bottom
    max_text_width: float = 0.80      # fraction of card width used by text
    border_alpha: int = 110
    ornament_alpha: int = 215

    # palette
    bg_color: RGB = (5, 8, 7)
    glow_color: RGB = (16, 30, 25)
    green: RGB = (74, 116, 99)
    cream: RGB = (234, 211, 195)
    text_on_green: RGB = (250, 248, 238)
    text_on_cream: RGB = (56, 82, 66)
    start_color: str = "green"        # "green" or "cream"

    # type
    font_path: Optional[str] = None
    font_weight: int = 500
    text_size: float = 0.100          # fraction of card height
    handle: Optional[str] = None
    handle_size: float = 0.019        # fraction of frame height
    handle_color: RGB = (196, 212, 202)

    # timing (seconds)
    intro: float = 1.5
    outro: float = 1.1
    crossfade: float = 0.35
    min_scene: float = 1.5
    max_scene: float = 4.0
    word_stagger: float = 0.16
    word_fade: float = 0.30

    # motion
    zoom: float = 0.030
    rise: int = 14                    # px the text rises while fading in

    # misc
    supersample: float = 1.6          # card baked at this scale, then downscaled

    def colors_for(self, kind: str) -> Tuple[RGB, RGB, RGB]:
        """Return (card fill, text colour, ornament colour) for a card kind."""
        if kind == "green":
            return self.green, self.text_on_green, self.cream
        return self.cream, self.text_on_cream, self.green

    def card_size(self) -> Tuple[int, int]:
        w = int(self.width * self.card_ratio)
        h = int(round(w / self.card_aspect))
        return w, h

    def with_(self, **kw) -> "Theme":
        return replace(self, **kw)


PRESETS = {
    # YouTube Shorts / Reels / TikTok
    "shorts": Theme(),
    # classic 16:9, same look as the reference clip
    "landscape": Theme(width=1920, height=1080, card_ratio=0.58, card_center_y=0.5,
                       text_size=0.09, max_text_width=0.74, handle_size=0.024),
    # 1:1 feed post
    "square": Theme(width=1080, height=1080, card_ratio=0.80, card_center_y=0.5,
                    text_size=0.09, handle_size=0.024),
}


def get_preset(name: str) -> Theme:
    try:
        return replace(PRESETS[name])
    except KeyError:
        raise SystemExit(
            f"unknown preset {name!r}; pick one of {', '.join(sorted(PRESETS))}"
        )

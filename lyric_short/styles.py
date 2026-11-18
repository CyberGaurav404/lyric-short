"""The look book.

Six ready-made styles, plus `auto` which picks one deterministically from a seed
so the same audio always renders the same way while a different song gets a
different look. `vary()` shifts the palette a little for extra variety.

    from lyric_short.styles import get_style, STYLE_NAMES
    theme = get_style("sunset")
"""
from __future__ import annotations

import colorsys
import hashlib
from typing import Dict, List

from .config import Palette, Theme

STYLE_NAMES = ["botanical", "midnight", "sunset", "paper", "poster", "neon"]


def _p(fill, text, orn) -> Palette:
    return Palette(tuple(fill), tuple(text), tuple(orn))


def botanical() -> Theme:
    """The original: cream and sage cards, floral corners, bokeh night."""
    return Theme(
        name="botanical",
        palettes=[_p((74, 116, 99), (250, 248, 238), (234, 211, 195)),
                  _p((234, 211, 195), (56, 82, 66), (74, 116, 99))],
        bg_color=(5, 8, 7), glow_color=(16, 30, 25), bg_mode="bokeh",
        ornament="botanical", card_mode="frame", transition="fade",
        shadow=True, handle_color=(196, 212, 202),
    )


def midnight() -> Theme:
    """Navy night, ivory type, thin brass ornaments."""
    return Theme(
        name="midnight",
        palettes=[_p((26, 30, 48), (243, 238, 226), (198, 168, 110)),
                  _p((243, 238, 226), (30, 34, 52), (198, 168, 110))],
        bg_color=(6, 8, 16), glow_color=(22, 26, 56), bg_mode="stars",
        ornament="arcs", card_mode="frame", transition="fade",
        grain=0.05, shadow=True, border_alpha=150,
        handle_color=(206, 190, 150),
    )


def sunset() -> Theme:
    """Warm dusk gradient, plum and peach cards, cards slide in."""
    return Theme(
        name="sunset",
        palettes=[_p((74, 28, 56), (255, 232, 214), (255, 170, 120)),
                  _p((255, 214, 180), (74, 30, 48), (226, 116, 88))],
        bg_color=(28, 12, 26), glow_color=(128, 54, 42), bg_mode="gradient",
        ornament="none", card_mode="rounded", transition="slide",
        grain=0.06, shadow=True, text_size=0.105,
        handle_color=(240, 190, 170),
    )


def paper() -> Theme:
    """Daylight, warm paper, ink-green type, almost no ornament."""
    return Theme(
        name="paper",
        palettes=[_p((252, 248, 238), (44, 62, 52), (128, 148, 128)),
                  _p((240, 234, 219), (44, 62, 52), (128, 148, 128))],
        bg_color=(223, 215, 199), glow_color=(255, 252, 245), bg_mode="paper",
        ornament="none", card_mode="rounded", transition="fade",
        grain=0.05, shadow=True, border_alpha=60, zoom=0.018,
        handle_color=(96, 112, 96),
    )


def poster() -> Theme:
    """Full-bleed colour panels, huge type, quick pop cuts."""
    return Theme(
        name="poster",
        palettes=[_p((226, 74, 58), (250, 244, 232), (250, 244, 232)),
                  _p((22, 22, 22), (250, 244, 232), (226, 74, 58))],
        bg_color=(10, 10, 10), glow_color=(20, 20, 20), bg_mode="gradient",
        ornament="lines", card_mode="fullbleed", transition="pop",
        grain=0.08, shadow=False, text_size=0.115, zoom=0.010,
        crossfade=0.28, handle_color=(250, 244, 232),
    )


def neon() -> Theme:
    """Dark glass, glowing type, cyan and magenta."""
    return Theme(
        name="neon",
        palettes=[_p((10, 12, 20), (150, 246, 255), (255, 88, 184)),
                  _p((10, 12, 20), (255, 150, 214), (150, 246, 255))],
        bg_color=(3, 4, 10), glow_color=(12, 20, 42), bg_mode="stars",
        ornament="lines", card_mode="frame", transition="pop",
        grain=0.04, glow=22, shadow=True, border_alpha=110,
        text_size=0.105, handle_color=(150, 220, 235),
    )


BUILDERS = {
    "botanical": botanical,
    "midnight": midnight,
    "sunset": sunset,
    "paper": paper,
    "poster": poster,
    "neon": neon,
}


def get_style(name: str) -> Theme:
    if name in ("auto", "random"):
        raise ValueError("use auto_style() for 'auto'")
    try:
        return BUILDERS[name]()
    except KeyError:
        raise SystemExit(f"unknown style {name!r}; pick one of {', '.join(STYLE_NAMES)} or auto")


def auto_style(seed: str = "", index: int = 0) -> Theme:
    """Pick a style from a stable hash, so the same audio always looks the same."""
    digest = hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()
    name = STYLE_NAMES[int(digest[:8], 16) % len(STYLE_NAMES)]
    return BUILDERS[name]()


def _shift(rgb, dh: float, ds: float = 0.0, dl: float = 0.0):
    r, g, b = [c / 255 for c in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + dh) % 1.0
    s = min(1.0, max(0.0, s + ds))
    l = min(1.0, max(0.0, l + dl))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def vary(theme: Theme, seed: str = "", amount: float = 0.05) -> Theme:
    """Nudge the palette so two videos in the same style do not look identical."""
    digest = hashlib.sha256(f"vary:{seed}".encode()).digest()
    dh = ((digest[0] / 255) - 0.5) * 2 * amount
    dl = ((digest[1] / 255) - 0.5) * 0.10
    palettes = [Palette(_shift(p.fill, dh, 0, dl), p.text, p.orn) for p in theme.palettes]
    return theme.with_(palettes=palettes)


def describe(theme: Theme) -> str:
    a, b = theme.palettes[0], theme.palettes[1]
    return (f"{theme.name}: bg={theme.bg_mode} card={theme.card_mode} "
            f"ornament={theme.ornament} transition={theme.transition} "
            f"a={a.fill} b={b.fill}")

#!/usr/bin/env python3
"""Download the Playfair Display font (SIL Open Font License) used by default.

    python scripts/fetch_fonts.py

The renderer falls back to any serif already installed on the machine if this
is skipped, but Playfair is what the look was designed around.
"""
from __future__ import annotations

import os
import sys
import urllib.request

URL = ("https://github.com/google/fonts/raw/main/ofl/playfairdisplay/"
       "PlayfairDisplay%5Bwght%5D.ttf")
DEST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "assets", "fonts", "Playfair.ttf")


def main() -> int:
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    if os.path.exists(DEST) and os.path.getsize(DEST) > 50_000:
        print(f"already there: {DEST}")
        return 0
    print(f"downloading Playfair Display -> {DEST}")
    try:
        urllib.request.urlretrieve(URL, DEST)
    except Exception as exc:  # noqa: BLE001 - network is best effort here
        print(f"download failed ({exc}).\n"
              "Grab Playfair Display manually from https://fonts.google.com/specimen/Playfair+Display\n"
              f"and save the .ttf as {DEST}", file=sys.stderr)
        return 1
    print(f"ok ({os.path.getsize(DEST) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

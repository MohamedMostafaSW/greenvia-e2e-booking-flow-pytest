"""
Test fixtures.

Only `valid_jpeg()` is used by the current flow — generates (once,
cached on disk) a small JPEG file used as both the passport and the
stamp upload during the passenger-form fill step.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "files"
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


def valid_jpeg() -> Path:
    """Return the path to a small valid JPEG; create it on first call."""
    path = FIXTURE_DIR / "passport.jpg"
    if not path.exists():
        img = Image.new("RGB", (200, 200), color=(128, 200, 230))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        path.write_bytes(buf.getvalue())
    return path

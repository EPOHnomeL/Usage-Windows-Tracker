"""Register bundled brand fonts so Tk can use them even if not installed.

The window uses Inter (the y-knot.io body font, bundled under assets/fonts).
On Windows we register it privately via GDI; on macOS/Linux we best-effort
copy it into the user font dir. If anything fails, Tk simply falls back to a
system sans-serif — the app still works, just not pixel-identical to the site.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(_HERE, "assets", "fonts")

# Preferred families in order. "Avenir Next" ships on macOS (y-knot.io's
# display font); "Inter" is the bundled body font; then generic fallbacks.
UI_FAMILY = "Inter"
DISPLAY_FAMILY = "Avenir Next" if sys.platform == "darwin" else "Inter"

_registered = False


def _ttfs() -> list[str]:
    if not os.path.isdir(_FONT_DIR):
        return []
    return [os.path.join(_FONT_DIR, f) for f in os.listdir(_FONT_DIR)
            if f.lower().endswith((".ttf", ".otf"))]


def register() -> None:
    """Register bundled fonts with the OS (idempotent, never raises)."""
    global _registered
    if _registered:
        return
    _registered = True
    try:
        if sys.platform == "win32":
            import ctypes
            FR_PRIVATE = 0x10
            for path in _ttfs():
                ctypes.windll.gdi32.AddFontResourceExW(
                    ctypes.c_wchar_p(path), FR_PRIVATE, 0)
        elif sys.platform == "darwin":
            import shutil
            dest = os.path.expanduser("~/Library/Fonts")
            os.makedirs(dest, exist_ok=True)
            for path in _ttfs():
                target = os.path.join(dest, os.path.basename(path))
                if not os.path.exists(target):
                    shutil.copy2(path, target)
        else:  # Linux: drop into the user font dir and refresh the cache
            import shutil
            import subprocess
            dest = os.path.expanduser("~/.local/share/fonts")
            os.makedirs(dest, exist_ok=True)
            changed = False
            for path in _ttfs():
                target = os.path.join(dest, os.path.basename(path))
                if not os.path.exists(target):
                    shutil.copy2(path, target)
                    changed = True
            if changed:
                try:
                    subprocess.run(["fc-cache", "-f", dest], timeout=20)
                except Exception:
                    pass
    except Exception:
        pass  # fall back to system fonts

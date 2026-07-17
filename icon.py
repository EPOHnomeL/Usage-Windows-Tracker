"""Render the tray icon: a small vertical/horizontal bar showing usage percentage.

The icon is drawn at a high resolution and scaled down so Windows renders it
crisply at tray size. Colour shifts from green -> amber -> red as usage climbs.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

# Rendered large, Windows scales down to ~16-24px in the tray.
SIZE = 64


def _bar_color(pct: float) -> tuple[int, int, int]:
    """Green below 50%, amber around 75%, red near 100%."""
    if pct >= 90:
        return (220, 53, 69)      # red
    if pct >= 75:
        return (255, 149, 0)      # orange
    if pct >= 50:
        return (255, 204, 0)      # amber
    return (52, 199, 89)          # green


# Tried in order; first that loads wins. Covers Windows, macOS and Linux.
_FONT_CANDIDATES = (
    "segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf",   # Windows
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",          # macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",       # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_icon(pct: float | None, *, error: bool = False) -> Image.Image:
    """Build an RGBA icon image.

    pct: 0-100 usage percentage, or None if unknown.
    error: draw a muted 'unknown' state (e.g. not signed in / network error).
    """
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded outer frame so it reads as a distinct little gauge.
    frame = (120, 120, 128, 255) if not error else (120, 120, 128, 160)
    margin = 6
    d.rounded_rectangle(
        [margin, margin, SIZE - margin, SIZE - margin],
        radius=10, outline=frame, width=4,
    )

    inner = margin + 6
    inner_bottom = SIZE - margin - 6
    inner_h = inner_bottom - inner

    if error or pct is None:
        # A dim dash to signal "no data".
        cy = SIZE // 2
        d.line([inner, cy, SIZE - inner, cy], fill=(150, 150, 150, 200), width=5)
        return img

    pct = max(0.0, min(100.0, float(pct)))
    fill_h = int(inner_h * pct / 100.0)
    color = _bar_color(pct) + (255,)

    # Fill grows from the bottom up.
    if fill_h > 0:
        d.rounded_rectangle(
            [inner, inner_bottom - fill_h, SIZE - inner, inner_bottom],
            radius=5, fill=color,
        )

    # Overlay the number so it's readable at a glance.
    label = "100" if pct >= 99.5 else str(int(round(pct)))
    font = _load_font(26 if len(label) < 3 else 20)
    tb = d.textbbox((0, 0), label, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tx = (SIZE - tw) / 2 - tb[0]
    ty = (SIZE - th) / 2 - tb[1]
    # Outline for contrast against any fill colour.
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                d.text((tx + dx, ty + dy), label, font=font, fill=(0, 0, 0, 220))
    d.text((tx, ty), label, font=font, fill=(255, 255, 255, 255))
    return img


if __name__ == "__main__":
    # Quick visual smoke test: dump sample icons to the scratch folder.
    import os
    out = os.path.join(os.path.dirname(__file__), "_preview")
    os.makedirs(out, exist_ok=True)
    for p in (0, 25, 50, 78, 95, 100, None):
        name = "err" if p is None else str(p)
        make_icon(p, error=(p is None)).save(os.path.join(out, f"icon_{name}.png"))
    print(f"wrote previews to {out}")

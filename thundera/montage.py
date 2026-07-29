"""Montage — per-group thumbnail grids + a master mosaic, for one-glance review.

Border colour encodes health: green = clean, amber = warnings, red = errors.
Needs Pillow; without it the sweep still runs and this is skipped.
"""
from __future__ import annotations

from pathlib import Path

THUMB_W = 360
PAD = 10
LABEL_H = 22
BORDER = 3
COLORS = {"ok": (46, 160, 67), "warn": (212, 153, 34), "error": (207, 34, 46)}


def available() -> bool:
    try:
        import PIL  # noqa: F401
    except Exception:
        return False
    return True


def _health(rec: dict) -> str:
    sevs = {f["severity"] for f in rec.get("findings", [])}
    return "error" if "error" in sevs else ("warn" if "warn" in sevs else "ok")


def build(records: list[dict], out_dir: Path) -> list[Path]:
    from PIL import Image, ImageDraw

    made: list[Path] = []
    groups: dict[str, list[dict]] = {}
    for rec in records:
        if rec.get("screenshot"):
            groups.setdefault(rec.get("group", "core"), []).append(rec)
    if not groups:
        return made

    def thumb(rec):
        im = Image.open(out_dir / rec["screenshot"]).convert("RGB")
        ratio = THUMB_W / im.width
        im = im.resize((THUMB_W, min(int(im.height * ratio), 640)))
        framed = Image.new(
            "RGB",
            (im.width + BORDER * 2, im.height + LABEL_H + BORDER * 2),
            COLORS[_health(rec)],
        )
        framed.paste(im, (BORDER, LABEL_H + BORDER))
        d = ImageDraw.Draw(framed)
        label = f"{rec['surface']} · {rec['profile']} · {rec['viewport']}"
        d.rectangle([0, 0, framed.width, LABEL_H], fill=(24, 26, 32))
        d.text((6, 5), label, fill=(230, 230, 230))
        return framed

    def grid(images, cols):
        rows = (len(images) + cols - 1) // cols
        cell_w = max(i.width for i in images) + PAD
        cell_h = max(i.height for i in images) + PAD
        canvas = Image.new("RGB", (cols * cell_w + PAD, rows * cell_h + PAD), (12, 14, 18))
        for i, im in enumerate(images):
            canvas.paste(im, (PAD + (i % cols) * cell_w, PAD + (i // cols) * cell_h))
        return canvas

    all_thumbs = []
    for group, recs in sorted(groups.items()):
        thumbs = [thumb(r) for r in recs]
        all_thumbs.extend(thumbs)
        out = out_dir / f"montage_{group}.png"
        grid(thumbs, cols=min(4, len(thumbs))).save(out, optimize=True)
        made.append(out)
    if len(all_thumbs) > 1:
        out = out_dir / "montage_master.png"
        grid(all_thumbs, cols=6).save(out, optimize=True)
        made.append(out)
    return made

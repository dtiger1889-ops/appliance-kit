#!/usr/bin/env python3
"""Draw numbered, color-coded care steps onto a parts diagram.

Usage:
    annotate_diagram.py SPEC.json OUT.png

SPEC.json (coordinates are pixels on the source image, or on a copy scaled to
"coord_width" pixels wide when you measured on a resized view):
{
  "source": "diagrams/parts.gif",          # relative to SPEC.json's folder or absolute
  "coord_width": 750,                      # optional
  "crop": [278, 95, 545, 405],             # optional, same coordinate space
  "width": 900,                            # output width
  "title": "Cleaning the dishwasher filter",
  "subtitle": "GE GSD5560G00SS - clean these 3 spots",
  "shapes": [
    {"kind": "ring", "center": [385, 275], "radius": [50, 26], "color": "#d62728"},
    {"kind": "polygon", "points": [[285, 330], [395, 298], [500, 340]], "color": "#1f77b4"},
    {"kind": "badge", "at": [318, 262], "label": "2", "color": "#d62728"}
  ],
  "steps": [
    {"label": "1", "color": "#555555", "text": "Power off ...", "source": "Manual p. 11"}
  ]
}
Every step should carry a source; steps without one are drawn with "(no source)"
so an unsourced step is visible rather than hidden.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = {
    "bold": ["segoeuib.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf",
             "LiberationSans-Bold.ttf", "Helvetica.ttc"],
    "regular": ["segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf", "arial.ttf",
                "LiberationSans-Regular.ttf", "Helvetica.ttc"],
}
FONT_DIRS = ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
             "/usr/share/fonts/TTF", "/usr/share/fonts", "/Library/Fonts", "/System/Library/Fonts",
             "/System/Library/Fonts/Supplemental"]


def font(style, size):
    for name in FONT_CANDIDATES[style]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
        for d in FONT_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def render(spec, base_dir, out):
    src = spec["source"]
    if not os.path.isabs(src):
        src = os.path.join(base_dir, src)
    im = Image.open(src).convert("RGB")
    k = im.width / spec["coord_width"] if spec.get("coord_width") else 1.0
    box = [int(v * k) for v in spec["crop"]] if spec.get("crop") else [0, 0, im.width, im.height]
    crop = im.crop(box)
    W = int(spec.get("width", 900))
    scale = W / crop.width
    crop = crop.resize((W, int(crop.height * scale)), Image.LANCZOS)

    big, mid, txt, small = font("bold", 34), font("bold", 26), font("regular", 25), font("regular", 20)
    title_h = 120 if spec.get("subtitle") else 80

    def P(x, y):
        return ((x * k - box[0]) * scale, (y * k - box[1]) * scale + title_h)

    tmp = ImageDraw.Draw(crop)
    blocks = []
    for s in spec.get("steps", []):
        lines = wrap(tmp, s["text"], txt, W - 110)
        src_line = s.get("source") or "(no source)"
        blocks.append((s.get("label", ""), s.get("color", "#555555"), lines, src_line))
    steps_h = sum(len(l) * 34 + 28 + 26 for _, _, l, _ in blocks) + 30
    canvas = Image.new("RGB", (W, title_h + crop.height + steps_h), "white")
    canvas.paste(crop, (0, title_h))
    d = ImageDraw.Draw(canvas)
    d.text((24, 18), spec.get("title", ""), font=big, fill="#111")
    if spec.get("subtitle"):
        d.text((24, 66), spec["subtitle"], font=txt, fill="#444")

    for sh in spec.get("shapes", []):
        c, w = sh.get("color", "#d62728"), int(sh.get("width", 6))
        if sh["kind"] == "ring":
            (cx, cy), (rx, ry) = sh["center"], sh["radius"]
            (x0, y0), (x1, y1) = P(cx - rx, cy - ry), P(cx + rx, cy + ry)
            d.ellipse([x0, y0, x1, y1], outline=c, width=w)
        elif sh["kind"] == "polygon":
            d.polygon([P(x, y) for x, y in sh["points"]], outline=c, width=w)
        elif sh["kind"] == "badge":
            cx, cy = P(*sh["at"])
            d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=c)
            d.text((cx, cy), str(sh["label"]), font=mid, fill="white", anchor="mm")

    y = title_h + crop.height + 20
    for n, c, lines, src_line in blocks:
        d.ellipse([24, y + 2, 64, y + 42], fill=c)
        d.text((44, y + 22), n, font=mid, fill="white", anchor="mm")
        for i, line in enumerate(lines):
            d.text((84, y + 4 + i * 34), line, font=txt, fill="#111")
        d.text((84, y + 4 + len(lines) * 34), "Source: " + src_line, font=small, fill="#777")
        y += len(lines) * 34 + 28 + 26

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    canvas.save(out)
    return canvas.size


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    spec_path, out = sys.argv[1], sys.argv[2]
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    size = render(spec, os.path.dirname(os.path.abspath(spec_path)), out)
    unsourced = [s.get("label") for s in spec.get("steps", []) if not s.get("source")]
    json.dump({"saved": out, "size": size, "unsourced_steps": unsourced}, sys.stdout)
    print()


if __name__ == "__main__":
    main()

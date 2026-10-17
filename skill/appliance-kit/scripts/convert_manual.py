#!/usr/bin/env python3
"""Convert a manual PDF to Markdown plus one PNG per page.

Usage:
    convert_manual.py MANUAL.pdf --out-dir KIT/manual [--title "GE dishwasher owner's manual"] [--dpi 150]

Writes KIT/manual/manual.md and KIT/manual/pages/page-NN.png. The Markdown keeps
the text page by page with a link to that page's image, because scanned or
garbled pages are only trustworthy as pictures. Pages with almost no text are
flagged so the briefing can say "read the page image". Prints a JSON summary.
"""
import argparse
import json
import os
import sys

import pymupdf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--dpi", type=int, default=150)
    a = ap.parse_args()

    pages_dir = os.path.join(a.out_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    doc = pymupdf.open(a.pdf)
    title = a.title or (doc.metadata or {}).get("title") or os.path.splitext(os.path.basename(a.pdf))[0]
    width = len(str(doc.page_count))
    image_only = []
    lines = [f"# {title}", "",
             f"Converted from `{os.path.basename(a.pdf)}` ({doc.page_count} pages). "
             "Each page's text is followed by a picture of the page; when the two disagree, trust the picture.", ""]
    for i, page in enumerate(doc, 1):
        n = str(i).zfill(width)
        img = f"page-{n}.png"
        page.get_pixmap(dpi=a.dpi).save(os.path.join(pages_dir, img))
        text = page.get_text().strip()
        lines += [f"<!-- page {i} -->", f"## Page {i}", ""]
        if len(text) < 40:
            image_only.append(i)
            lines += ["_This page is mostly pictures or a scan; read the image below._", ""]
        if text:
            lines += [text, ""]
        lines += [f"![Page {i}](pages/{img})", ""]
    count = doc.page_count
    doc.close()
    md = os.path.join(a.out_dir, "manual.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    json.dump({"markdown": md, "pages_dir": pages_dir, "pages": count,
               "image_only_pages": image_only}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()

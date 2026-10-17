#!/usr/bin/env python3
"""Download a candidate manual URL and check it is really the manual.

Usage:
    fetch_manual.py URL --out-dir KIT/manual --model GSD5560G00SS [--name "GE GSD5560G owner's manual"]

Checks: the response is a PDF (magic bytes, not just the content type), it opens
with pymupdf, and its text names the model or its series stem (GSD5560G -> GSD5500
counts too: manuals often list the series). Prints JSON with the saved path, page
count, which model strings were found, and a verdict: ok / wrong-model / not-pdf / failed.
A wrong-model file is kept under its name with a .unverified suffix so nothing is lost.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def model_patterns(model):
    """The full model, trimmed no shorter than its core (GSD5560G00SS -> ... GSD5560G), plus the series.

    Never a bare prefix like GSD55: that would accept a different model's manual (GSD5599).
    """
    m = re.sub(r"[^A-Z0-9]", "", model.upper())
    core = re.match(r"[A-Z]*\d+[A-Z]?", m)
    floor = max(len(core.group(0)) if core else len(m), 5)
    pats = {m[:n] for n in range(len(m), floor - 1, -1)}
    # Series form: GSD5560G -> GSD55 + "00" (GSD5500), the way manuals list families.
    d = re.match(r"([A-Z]+)(\d{2})(\d{2})", m)
    if d:
        pats.add(d.group(1) + d.group(2) + "00")
    return sorted(pats, key=len, reverse=True)


def safe_name(s):
    return re.sub(r'[<>:"/\\|?*]+', "", s).strip() or "manual"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    out = {"url": a.url, "path": None, "pages": 0, "found": [], "verdict": "failed", "error": None}
    try:
        req = urllib.request.Request(a.url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        if not data.startswith(b"%PDF"):
            out["verdict"] = "not-pdf"
            out["error"] = "The link did not return a PDF (often a web page that loads the manual with JavaScript)."
        else:
            base = a.name or os.path.basename(urllib.parse.urlparse(a.url).path) or "manual.pdf"
            base = safe_name(base)
            if not base.lower().endswith(".pdf"):
                base += ".pdf"
            path = os.path.join(a.out_dir, base)
            with open(path, "wb") as f:
                f.write(data)
            import pymupdf
            doc = pymupdf.open(path)
            out["pages"] = doc.page_count
            text = re.sub(r"[\s\-]", "", "".join(p.get_text() for p in doc)).upper()
            doc.close()
            out["found"] = [p for p in model_patterns(a.model) if p in text]
            if out["found"]:
                out["verdict"] = "ok"
                out["path"] = path
            else:
                bad = path + ".unverified"
                os.replace(path, bad)
                out["path"] = bad
                out["verdict"] = "wrong-model"
                out["error"] = "The PDF does not mention this model or its series."
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()

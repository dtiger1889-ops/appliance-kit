#!/usr/bin/env python3
"""Check the US CPSC recall database for an appliance model and serial.

Usage:
    recall_check.py --model GSD5560G00SS --serial DF123456A [--brand GE] [--type dishwasher]

Prints JSON: every recall whose text names the model (or a shorter stem of it),
and for each one whether the serial falls inside the recalled range.

Serial ranges are written in free text, so the matcher only handles the common
phrasings. Anything it cannot parse comes back as "unclear" with the recall's own
words, so the person (or the agent) can read it. Stdlib only.
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

API = "https://www.saferproducts.gov/RestWebServices/Recall"
UA = "appliance-kit/1.0 (+https://github.com/dtiger1889-ops/appliance-kit)"


def query(**params):
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def stems(model):
    """GSD5560G00SS -> GSD5560G00SS, GSD5560G00S, ... down to 5 characters.

    Recall notices usually list the series (GSD5560G), not the color/revision suffix.
    """
    m = re.sub(r"[^A-Z0-9]", "", model.upper())
    return [m[:n] for n in range(len(m), 4, -1)]


def text_of(r):
    parts = [r.get("Title") or "", r.get("Description") or ""]
    for p in r.get("Products") or []:
        parts += [p.get("Name") or "", p.get("Model") or "", p.get("Description") or ""]
    return " ".join(parts)


def serial_verdict(text, serial):
    """Return (verdict, clause) where verdict is covered / not covered / unclear."""
    s = re.sub(r"[^A-Z0-9]", "", serial.upper())
    t = " ".join(text.split())
    rules = []

    # "first letter A through T and the second letter G"
    for m in re.finditer(r"first letter ([A-Z]) through ([A-Z]) and (?:the )?second letter ([A-Z])", t, re.I):
        a, b, c = (g.upper() for g in m.groups())
        rules.append((m.group(0), len(s) >= 2 and a <= s[0] <= b and s[1] == c))
    # "the serial letters VF" / "serial numbers beginning with VF" / "starting with"
    # A list of prefixes ("VF or VG", "VF, VG and VH") counts every item.
    code = r"[A-Z0-9]{1,4}"
    for m in re.finditer(rf"serial (?:number )?(?:letters|numbers? (?:beginning|starting) with|prefix(?:es)?) "
                         rf"({code}(?:(?:,\s*|,?\s+or\s+|,?\s+and\s+){code}\b)*)\b", t, re.I):
        prefixes = [p.upper() for p in re.split(r",\s*|,?\s+or\s+|,?\s+and\s+", m.group(1), flags=re.I)]
        rules.append((m.group(0), any(s.startswith(p) for p in prefixes)))
    # "serial numbers 1234 through 5678" / "from X to Y" (same length, compared as text)
    for m in re.finditer(r"serial numbers? (?:from |between |ranging from )?([A-Z0-9]{4,}) (?:through|to|and) ([A-Z0-9]{4,})", t, re.I):
        lo, hi = m.group(1).upper(), m.group(2).upper()
        if len(lo) == len(hi) == len(s):
            rules.append((m.group(0), lo <= s <= hi))
        else:
            rules.append((m.group(0), None))

    if not rules:
        return "unclear", None
    if any(hit for _, hit in rules if hit):
        return "covered", "; ".join(c for c, hit in rules if hit)
    if all(hit is False for _, hit in rules):
        return "not covered", "; ".join(c for c, _ in rules)
    return "unclear", "; ".join(c for c, _ in rules)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--serial", default="")
    ap.add_argument("--brand", default="")
    ap.add_argument("--type", default="", help="appliance type, e.g. dishwasher")
    a = ap.parse_args()

    out = {"source": "US CPSC recall database (saferproducts.gov)", "model": a.model,
           "serial": a.serial, "matched_stem": None, "recalls": [], "brand_type_recalls": [],
           "verdict": "no recall found", "error": None}
    try:
        for stem in stems(a.model):
            hits = query(RecallDescription=stem)
            if hits:
                out["matched_stem"] = stem
                break
        else:
            hits = []
        for r in hits:
            verdict, clause = serial_verdict(text_of(r), a.serial) if a.serial else ("unclear", None)
            out["recalls"].append({
                "number": r.get("RecallNumber"), "date": (r.get("RecallDate") or "")[:10],
                "title": r.get("Title"), "url": r.get("URL"),
                "description": r.get("Description"),
                "hazard": "; ".join(h.get("Name", "") for h in r.get("Hazards") or []),
                "remedy": "; ".join(h.get("Name", "") for h in r.get("Remedies") or []),
                "serial_verdict": verdict, "serial_clause": clause})
        # Broader list for a human glance: same brand + type, any model.
        if a.brand and a.type:
            for r in query(ProductName=a.type, RecallTitle=a.brand):
                if not any(x["number"] == r.get("RecallNumber") for x in out["recalls"]):
                    out["brand_type_recalls"].append({
                        "number": r.get("RecallNumber"), "date": (r.get("RecallDate") or "")[:10],
                        "title": r.get("Title"), "url": r.get("URL")})
    except Exception as e:  # fail open: the kit still gets built
        out["error"] = f"{type(e).__name__}: {e}"
        out["verdict"] = "check failed"

    vs = [r["serial_verdict"] for r in out["recalls"]]
    if "covered" in vs:
        out["verdict"] = "covered"
    elif "unclear" in vs:
        out["verdict"] = "unclear"
    elif vs:
        out["verdict"] = "not covered"
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()

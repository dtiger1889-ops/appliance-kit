#!/usr/bin/env python3
"""Make the appliance folder and write its briefing.

Three commands:

  build_kit.py init --brand GE --type Dishwasher --model GSD5560G00SS [--root DIR] [--photo PATH ...]
      Creates ROOT/<Brand Type Model>/ with label/, manual/, diagrams/ and copies
      the label photos in. ROOT defaults to $APPLIANCE_KIT_ROOT, else
      ~/Documents/Appliances. Prints the kit folder path as JSON.

  build_kit.py render KIT_DIR
      Reads KIT_DIR/kit.json (written by the agent; schema in references/kit-schema.md)
      and writes briefing.md, briefing.html, briefing.pdf, then refreshes
      ROOT/index.md. Anything the kit lacks is added to the Missing list, so a
      half-finished run still produces a usable folder.

  build_kit.py zip KIT_DIR
      Zips the kit folder next to itself, for runtimes where the person downloads
      files from the chat.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
import zipfile


def default_root():
    env = os.environ.get("APPLIANCE_KIT_ROOT")
    if env:
        return os.path.expanduser(env)
    return os.path.join(os.path.expanduser("~"), "Documents", "Appliances")


def folder_name(brand, kind, model):
    name = " ".join(x.strip() for x in (brand, kind, model) if x and x.strip())
    return re.sub(r'[<>:"/\\|?*]+', "-", name) or "Unknown appliance"


def cmd_init(a):
    root = os.path.abspath(a.root or default_root())
    kit = os.path.join(root, folder_name(a.brand, a.type, a.model))
    for sub in ("label", "manual", "diagrams"):
        os.makedirs(os.path.join(kit, sub), exist_ok=True)
    copied = []
    for p in a.photo or []:
        dst = os.path.join(kit, "label", os.path.basename(p))
        if os.path.abspath(p) != os.path.abspath(dst):
            shutil.copy2(p, dst)
        copied.append(os.path.relpath(dst, kit).replace(os.sep, "/"))
    print(json.dumps({"kit_dir": kit, "root": root, "photos": copied}))


# ---------------------------------------------------------------- rendering

def rel_exists(kit, rel):
    return bool(rel) and os.path.exists(os.path.join(kit, rel))


def auto_missing(kit, k):
    """Add a Missing entry for every expected piece that isn't there."""
    have = {m.get("what", "").lower() for m in k.get("missing", [])}
    found = []

    def add(what, why, try_):
        if not any(what.lower() in h or h in what.lower() for h in have if h):
            found.append({"what": what, "why": why, "try": try_})

    ap = k.get("appliance", {})
    if not ap.get("model"):
        add("Model number", "It couldn't be read from the photo.",
            "Send a sharper, straight-on photo of the label in good light.")
    if not ap.get("serial"):
        add("Serial number", "It couldn't be read from the photo.",
            "Send a closer photo of just the serial line.")
    m = k.get("manual", {})
    if not rel_exists(kit, m.get("pdf")):
        add("Owner's manual (PDF)", "No official PDF was found or downloaded.",
            "Search the maker's website for the model number plus \"owner's manual\".")
    if not rel_exists(kit, m.get("markdown")):
        add("Manual as text", "There was no PDF to convert.", "Once you have the PDF, ask to convert it.")
    if not k.get("age", {}).get("year"):
        add("Build date", k.get("age", {}).get("note") or "The serial's date code isn't decoded for this brand.",
            "The maker's customer line can tell you from the serial number.")
    r = k.get("recall", {}).get("verdict", "")
    if r in ("", "check failed", "unclear"):
        add("Recall check", "The recall check didn't give a clear answer.",
            "Search cpsc.gov/Recalls for the model number, or call the maker.")
    if not any(rel_exists(kit, c.get("guide")) for c in k.get("care", [])):
        add("Care diagram", "No parts diagram was found to mark up.",
            "The care steps below still come from the manual.")
    return k.get("missing", []) + found


def facts_rows(k):
    rows = [(f.get("field", ""), f.get("value", ""), f.get("confidence", "")) for f in k.get("label", {}).get("fields", [])]
    if not rows:
        ap = k.get("appliance", {})
        rows = [(f, ap.get(f.lower(), ""), "") for f in ("Brand", "Model", "Serial")]
    return rows


def is_url(s):
    return bool(re.match(r"https?://\S", str(s or ""), re.I))


def md_link(label, url):
    return f"[{label}]({url})" if url else label


def briefing_md(kit, k, missing):
    ap, age, rc, man = k.get("appliance", {}), k.get("age", {}), k.get("recall", {}), k.get("manual", {})
    name, brand = ap.get("name") or ap.get("model"), ap.get("brand")
    # A full product name usually starts with the brand already ("Whirlpool 1.7 cu. ft. ...").
    # Only a name counts, as a whole word: model GE123 or name "Genesis range" keeps brand GE.
    if brand and ap.get("name") and re.match(rf"{re.escape(brand)}\b", ap["name"], re.I):
        brand = None
    title = " ".join(x for x in (brand, name) if x)
    L = [f"# {ap.get('type', 'Appliance')}: {title}", "",
         f"_Kit made {k.get('created') or dt.date.today().isoformat()}._", ""]
    if k.get("summary"):
        L += [k["summary"], ""]

    L += ["## The label", ""]
    if k.get("label", {}).get("location"):
        L += [f"Where it is: {k['label']['location']}.", ""]
    L += ["| What | Value |", "|---|---|"]
    for f, v, c in facts_rows(k):
        flag = " (check this: hard to read)" if c == "low" else ""
        L.append(f"| {f} | {v}{flag} |")
    for u in k.get("label", {}).get("uncertain", []):
        L.append(f"\n> Check: {u}")
    for p in k.get("label", {}).get("photos", []):
        L.append(f"\n![Label photo]({p})")
    L.append("")

    L += ["## What that tells you", ""]
    if age.get("summary"):
        L.append(f"- **Age:** {age['summary']}")
    if rc.get("summary"):
        L.append(f"- **Recalls:** {rc['summary']}")
    for f in k.get("facts", []):
        s = f.get("source")
        # Only a web address becomes a link; "Manual p. 5" stays plain text.
        src = (f" ({md_link('source', s)})" if is_url(s) else f" _(Source: {s})_") if s else ""
        L.append(f"- {f.get('text', '')}{src}")
    L.append("")

    for c in k.get("care", []):
        L += [f"## {c.get('title', 'Routine care')}", ""]
        if rel_exists(kit, c.get("guide")):
            L += [f"![{c.get('title', '')}]({c['guide']})", ""]
        if c.get("intro"):
            L += [c["intro"], ""]
        for i, s in enumerate(c.get("steps", []), 1):
            L.append(f"{i}. {s.get('text', '')} _(Source: {s.get('source') or 'none given'})_")
        if c.get("when_to_call"):
            # The label already says "if", so drop a leading "If " the writer added.
            w = c["when_to_call"]
            w = "; ".join(map(str, w)) if isinstance(w, list) else str(w)  # agent JSON isn't validated
            when = re.sub(r"^\s*if\s+", "", w, flags=re.I)
            L += ["", f"**Stop and call for service if:** {when}"]
        L.append("")

    L += ["## The manual", ""]
    if rel_exists(kit, man.get("pdf")):
        L.append(f"- Original PDF: [{man.get('title') or os.path.basename(man['pdf'])}]({man['pdf']})"
                 + (f", {man['publication']}" if man.get("publication") else ""))
    if rel_exists(kit, man.get("markdown")):
        L.append(f"- Searchable text with page pictures: [manual.md]({man['markdown']})")
    if man.get("url"):
        L.append(f"- Downloaded from: {man['url']}")
    L.append("")

    if k.get("links"):
        L += ["## Useful links", ""] + [f"- {md_link(l.get('label', ''), l.get('url'))}" for l in k["links"]] + [""]

    if missing:
        L += ["## Missing", "", "| What | Why | The one thing to try |", "|---|---|---|"]
        L += [f"| {m.get('what', '')} | {m.get('why', '')} | {m.get('try', '')} |" for m in missing]
        L.append("")

    L += ["## Sources", ""]
    for s in sorted(set(src_urls(k))):
        L.append(f"- {s}")
    L += ["", "_Owner care only. For anything electrical, gas or water-line, call a technician._", ""]
    return "\n".join(L)


def src_urls(k):
    out = []
    for c in k.get("care", []):
        out += [s.get("source_url") for s in c.get("steps", [])]
    out += [f.get("source") for f in k.get("facts", [])]
    out += [k.get("manual", {}).get("url"), k.get("recall", {}).get("url")]
    out += (k.get("age", {}).get("source") or []) if isinstance(k.get("age", {}).get("source"), list) else [k.get("age", {}).get("source")]
    return [u for u in out if is_url(u)]


CSS = """
body{font-family:Helvetica,Arial,sans-serif;color:#111;margin:24px;font-size:11pt;line-height:1.35}
h1{font-size:18pt;margin:0 0 4px}h2{font-size:13pt;margin:14px 0 6px;border-bottom:1px solid #ccc}
table{border-collapse:collapse;width:100%}td{border:1px solid #ccc;padding:3px 6px;vertical-align:top}
.small{color:#555;font-size:9pt}img{max-width:100%}li{margin-bottom:3px}
"""


def briefing_html(kit, k, missing):
    """One printable page: label facts, the age/recall lines, the first care guide."""
    e = html.escape
    ap, age, rc = k.get("appliance", {}), k.get("age", {}), k.get("recall", {})
    title = " ".join(x for x in (ap.get("brand"), ap.get("type"), ap.get("model")) if x)
    H = [f"<html><head><meta charset='utf-8'><title>{e(title)}</title><style>{CSS}</style></head><body>",
         f"<h1>{e(title)}</h1>"]
    rows = "".join(f"<tr><td><b>{e(f)}</b></td><td>{e(str(v))}{' (check)' if c == 'low' else ''}</td></tr>"
                   for f, v, c in facts_rows(k))
    H.append(f"<table>{rows}</table>")
    lines = [x for x in (age.get("summary") and "Age: " + age["summary"],
                         rc.get("summary") and "Recalls: " + rc["summary"]) if x]
    if lines:
        H.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in lines) + "</ul>")
    care = next((c for c in k.get("care", []) if rel_exists(kit, c.get("guide"))), None)
    if care:
        H.append(f"<h2>{e(care.get('title', 'Routine care'))}</h2><img src='{e(care['guide'])}'/>")
    elif k.get("care"):
        c = k["care"][0]
        H.append(f"<h2>{e(c.get('title', 'Routine care'))}</h2><ol>"
                 + "".join(f"<li>{e(s.get('text', ''))} <span class='small'>({e(s.get('source') or 'no source')})</span></li>"
                           for s in c.get("steps", [])) + "</ol>")
    if missing:
        H.append("<h2>Missing</h2><ul>" + "".join(f"<li><b>{e(m.get('what', ''))}</b>: {e(m.get('try', ''))}</li>"
                                                  for m in missing) + "</ul>")
    H.append("<p class='small'>Full details: briefing.md in this folder. Owner care only.</p></body></html>")
    return "".join(H)


def html_to_pdf(kit, html_text, out):
    """Render the printable page to PDF with pymupdf's Story; scale the guide to fit."""
    import pymupdf
    page = pymupdf.paper_rect("letter")
    where = page + (36, 36, -36, -36)
    story = pymupdf.Story(html=html_text, archive=kit)
    w = pymupdf.DocumentWriter(out)
    more = True
    while more:
        dev = w.begin_page(page)
        more, _ = story.place(where)
        story.draw(dev)
        w.end_page()
    w.close()


def refresh_index(root):
    rows = []
    for name in sorted(os.listdir(root)):
        kj = os.path.join(root, name, "kit.json")
        if not os.path.isfile(kj):
            continue
        try:
            with open(kj, encoding="utf-8") as f:
                k = json.load(f)
        except (OSError, ValueError):
            continue
        ap = k.get("appliance", {})
        built = k.get("age", {}).get("year") or "?"
        recall = k.get("recall", {}).get("verdict") or "not checked"
        link = name.replace(" ", "%20") + "/briefing.md"
        rows.append(f"| [{name}]({link}) | {ap.get('serial', '')} | {built} | {recall} | {k.get('created', '')} |")
    text = "\n".join(["# My appliances", "",
                      "| Appliance | Serial | Built | Recall | Kit made |", "|---|---|---|---|---|"] + rows) + "\n"
    with open(os.path.join(root, "index.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return len(rows)


def cmd_render(a):
    kit = os.path.abspath(a.kit_dir)
    with open(os.path.join(kit, "kit.json"), encoding="utf-8") as f:
        k = json.load(f)
    k.setdefault("created", dt.date.today().isoformat())
    missing = auto_missing(kit, k)
    out = {"kit_dir": kit, "written": [], "missing": [m["what"] for m in missing], "errors": []}

    # The PDF goes first so a failure can join the Missing list the other two files show.
    try:
        html_to_pdf(kit, briefing_html(kit, k, missing), os.path.join(kit, "briefing.pdf"))
        out["written"].append("briefing.pdf")
    except Exception as e:  # fail open: the HTML page still prints from a browser
        out["errors"].append(f"briefing.pdf: {type(e).__name__}: {e}")
        missing.append({"what": "Printable PDF", "why": "The PDF couldn't be made here.",
                        "try": "Open briefing.html in a browser and print it."})
        out["missing"].append("Printable PDF")
    with open(os.path.join(kit, "briefing.md"), "w", encoding="utf-8") as f:
        f.write(briefing_md(kit, k, missing))
    out["written"].append("briefing.md")
    with open(os.path.join(kit, "briefing.html"), "w", encoding="utf-8") as f:
        f.write(briefing_html(kit, k, missing))
    out["written"].append("briefing.html")
    unsourced = [s.get("text", "")[:60] for c in k.get("care", []) for s in c.get("steps", []) if not s.get("source")]
    if unsourced:
        out["errors"].append("Care steps with no source: " + "; ".join(unsourced))
    out["index_entries"] = refresh_index(os.path.dirname(kit))
    print(json.dumps(out, indent=2))


def cmd_zip(a):
    kit = os.path.abspath(a.kit_dir)
    dst = kit + ".zip"
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(kit):
            for fn in files:
                p = os.path.join(base, fn)
                z.write(p, os.path.relpath(p, os.path.dirname(kit)))
    print(json.dumps({"zip": dst}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--brand", default="")
    i.add_argument("--type", default="")
    i.add_argument("--model", default="")
    i.add_argument("--root")
    i.add_argument("--photo", action="append")
    r = sub.add_parser("render")
    r.add_argument("kit_dir")
    z = sub.add_parser("zip")
    z.add_argument("kit_dir")
    a = ap.parse_args()
    {"init": cmd_init, "render": cmd_render, "zip": cmd_zip}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

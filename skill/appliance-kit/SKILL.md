---
name: appliance-kit
description: >-
  Turns a photo of a home appliance's rating label (the sticker with the model and
  serial number, usually inside the door, on the back or under the lid) into an
  appliance kit, a folder holding the label facts, how old the appliance is, a US
  recall check, the official owner's manual as a PDF and as searchable text, and a
  plain-words care briefing with a marked-up parts diagram. Use this skill whenever
  someone sends a photo of an appliance label, model plate, service tag or serial
  sticker, or asks how old their dishwasher, washer, dryer, fridge, range, microwave
  or water heater is, where its manual is, whether it is recalled, or how to clean its
  filter, even if they don't say "kit". Do NOT use for repairs beyond owner care
  (wiring, gas, water lines, opening panels), for ordering parts, or for electronics
  and vehicles.
---

# Appliance kit

Most people who send a label photo are not technical: they want to know what they own, whether it's safe, and how to look after it, without reading a 40-page manual. So speak plainly, keep the chat short, put the detail in the folder, and never present a guess as a fact, because a wrong model number sends them to the wrong manual and the wrong recall.

## What you produce

`Appliances/<Brand Type Model>/` (for example `Appliances/GE Dishwasher GSD5560G00SS/`):

- `briefing.md` (plain-words briefing), `briefing.html` + `briefing.pdf` (one printable page)
- `kit.json`: every fact with where it came from (schema: `references/kit-schema.md`)
- `label/` photos; `manual/` original PDF, `manual.md`, `pages/*.png`; `diagrams/` parts diagram + marked-up care guide

Plus `Appliances/index.md`, a list of every kit made so far.

**Fail open.** Always finish with a folder, even when a step fails. What is missing goes in `kit.json` `missing` with why, and the one thing the person can try. Never stop at "I couldn't find the manual".

## Checklist

Copy this into your reply as you work and tick each item:

```
- [ ] 1 Read the label, echo model + serial
- [ ] 2 Age (serial_decode.py)
- [ ] 3 Recalls (recall_check.py)
- [ ] 4 Manual found, downloaded, converted (or linked mode)
- [ ] 5 Care guide: diagram + sourced steps (annotate_diagram.py)
- [ ] 6 kit.json written, build_kit.py render, chat report
```

## Setup

- Scripts live in `scripts/` next to this file. Python 3.9+ with `pymupdf` and `Pillow` (`pip install -r requirements.txt` if an import fails).
- Folder location: on a computer, `~/Documents/Appliances` (the default; `APPLIANCE_KIT_ROOT` overrides). In a chat sandbox with an outputs folder (for example `/mnt/user-data/outputs`), use `--root <outputs>/Appliances` and zip the kit at the end.
- **Can the sandbox download files?** The first `fetch_manual.py` run tells you. A connection, DNS or proxy error (not a 404) means the sandbox can't reach that site: switch to **linked mode** for the rest of the run. Use your own web search and web fetch tools to find and read pages, and record links instead of downloaded files.

## Steps

### 1. Read the label

Look at the photo yourself. Write down every field you can read: brand or maker, model, serial, and any of type, volts, amps, watts, gas type, capacity, date, listing marks.

- Copy model and serial **character by character**; watch 0/O, 1/I/L, 5/S, 8/B, 2/Z, 6/G. Mark an unsure field `"confidence": "low"` and name the character in `label.uncertain`.
- Unreadable model or serial: carry on with what you have, and ask at the end for a closer, straight-on photo in good light.
- Echo the model and serial in the chat reply so the person can check them against the sticker.

`build_kit.py init --brand <B> --type <Type> --model <M> --photo <photo> [--root <dir>]` makes the folder.

### 2. Age

`serial_decode.py --brand <B> --serial <S>` (Bosch, Thermador, Gaggenau: add `--fd <FD number>` from the label). Year codes repeat every 10 to 20 years; when several years fit, rerun with `--hint-year` from what you know (the manual's print date, when the model was sold) and say that reasoning in one sentence in `age.summary`. Brand not decoded: say so, don't guess. Rules and sources: `references/serial-codes.md`.

### 3. Recalls

`recall_check.py --model <M> --serial <S> --brand <B> --type <type>` asks the US CPSC recall database and, for each recall naming the model, reports `covered`, `not covered` or `unclear` (range text it couldn't parse: read `description` yourself and decide). In linked mode, web-fetch `https://www.saferproducts.gov/RestWebServices/Recall?format=json&RecallDescription=<stem>`, shortening the model one character at a time (GSD5560G00SS, GSD5560G00S ... GSD5560G) until a match or 5 characters.

Covered: it leads the chat reply and the briefing (hazard, what to do, phone or link). No match: write "no US recall found for this model", never "it's safe".

### 4. Manual

Search order and brand tips: `references/finding-manuals.md`.

- `fetch_manual.py <url> --out-dir <kit>/manual --model <M> --name "<Brand model owner's manual>"` checks it is a PDF naming the model or its series; `wrong-model` means keep looking.
- `convert_manual.py <pdf> --out-dir <kit>/manual --title "<title>"` writes `manual.md` and page images.
- **Linked mode:** put the PDF link in `manual.url`, read it with web fetch to source the care steps, and add to `missing`: what = "Owner's manual (PDF)", why = "This chat can't download files from the maker's site", try = "Tap the link, save the PDF and send it here; I'll add it with searchable text." When the PDF arrives, convert it and render again.

### 5. Care guide

Pick the routine job owners most need: dishwasher filter; washer filter or door gasket; dryer lint screen and vent; fridge water filter and coils; range hood filter; microwave grease filter. Read what the manual says about it.

- Get a parts diagram showing those parts: a parts site (PartSelect, AppliancePartsPros, RepairClinic, Sears PartsDirect) or a manual page image. Save it in `diagrams/`.
- Look at it, pick rings, outlines and numbered badges, write the steps as a spec (format: `scripts/annotate_diagram.py` docstring), then `annotate_diagram.py <spec.json> <kit>/diagrams/<job>-guide.png`. Open the PNG and check each ring sits on its part.
- **Every step names its source** (a manual page like "Manual p. 11", or a named site), because an unsourced step can't be checked and may be wrong for this model. Unsourceable step: leave it out.
- Owner care only. Anything that opens panels or touches wiring, gas or water lines becomes "call for service" with the reason.
- No diagram: write the steps anyway; the briefing lists the diagram as missing.

### 6. Build and report

Write `<kit>/kit.json` (schema `references/kit-schema.md`, tone `references/briefing-style.md`), then `build_kit.py render <kit>`. It writes the briefing, printable page and index, and adds anything still absent to Missing. If it lists care steps with no source, fix them and render again. In a chat sandbox, `build_kit.py zip <kit>` and offer the zip.

Chat reply, about 10 lines at most:
1. What it is: brand, type, model, serial, "check these against your sticker".
2. Age and recall, one line each (a covered recall goes first).
3. The top care tip in one line, pointing to the guide picture.
4. What's in the folder; each Missing item with its one thing to try.

### 7. Add-ons

If another installed skill says it files finished appliance kits somewhere (a notes app, a home inventory), run it now. The kit never depends on one.

## Example

Photo: a dishwasher door-frame sticker, slightly angled. Read: GE, model GSD5560G00SS, serial DF123456A, 120 V 60 Hz 8.2 A. `serial_decode.py --brand GE --serial DF123456A` gives February with years 1991/2003/2015; the manual found is dated November 2002, so `--hint-year 2002` gives February 2003. `recall_check.py` finds CPSC 05-116 for GSD5560G but the serial is outside its range: not covered. Manual: GE pub. 49-5943-1 (GSD5500 series). Care guide: no pull-out filter; ring the mesh screen, the coarse dome and the spray arm, with steps from manual pages 11 and 14.

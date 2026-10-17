# Finding the owner's manual

Goal: the maker's own owner's manual ("Use and Care Guide", "Owner's Manual") as a PDF, for this model or its series. Installation instructions, spec sheets and service manuals are not it (keep a service sheet only as an extra link).

## Search order

1. **The maker's support page for the model.** Search `<brand> <model> owner's manual`. Many support pages build the document list with JavaScript, so a plain fetch may show no links. Then:
   - try the product page instead of the support page (it often carries a direct PDF link);
   - look in the page source for `.pdf` links (CDNs such as `images.salsify.com`, `media3.bosch-home.com`, `s7d9.scene7.com`);
   - use a browser-capable fetch if the runtime has one.
2. **Shorter model numbers.** Strip the color or revision suffix (GSD5560G00SS -> GSD5560GSS -> GSD5560G). Manuals usually cover a whole series (GSD5500 series).
3. **Parts sites**, which mirror maker manuals: PartSelect, AppliancePartsPros, RepairClinic, Sears PartsDirect, ManualsLib (last resort; check it is the maker's document).

Always run `fetch_manual.py`: it confirms the file is a PDF and mentions the model or series.

## Brand tips

Starting points only: sites move. The GE route was confirmed on a real run; treat the rest as where to look first.

- **GE / Hotpoint / Café / Monogram:** `products.geappliances.com/appliance/gea-specs/<MODEL>` lists "Use and Care Manual" and often a direct PDF. Older models: drop the color letters (GSD5560G00SS -> GSD5560GSS).
- **Whirlpool / Maytag / KitchenAid / Amana / Jenn-Air:** `<brand>.com/owners` search by model; PDFs on `whirlpool.com` / `kitchenaid.com` paths ending `.pdf`. Manuals are shared across brands for the same platform.
- **Frigidaire / Electrolux:** model page "Manuals & Guides"; PDFs often on `electrolux-na` or `frigidaire.com` CDN.
- **Samsung:** `samsung.com/us/support/` model page, "Manuals & Downloads".
- **LG:** `lg.com/us/support/product/<model>`, "Manuals & Documents".
- **Bosch / Thermador / Gaggenau:** `bosch-home.com/us` (or the brand site) model page; PDFs on `media3.bosch-home.com`. The E-Nr is the model (for example SHX68T55UC/01).

## Parts diagrams (for the care guide)

PartSelect model pages (`partselect.com/Models/<MODEL>/`) group diagrams by section; the diagram images are plain GIF/JPG files that download directly even when the page itself blocks plain fetches. Note each part's diagram number and name for the steps.

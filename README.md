# Appliance Kit

Take a photo of the sticker on your appliance (the one with the model and serial number) and get back:

- what it is and how old it is
- whether it's been recalled in the US
- the official owner's manual, as the original PDF and as searchable text
- a short, plain guide to looking after it, with a marked-up picture showing exactly where to clean

Everything lands in one folder you can keep.

![A kit's printable page: the label facts, the build date, the recall check and a marked-up care guide](assets/briefing-page.png)

This repo supplies an agent skill with Python helpers, rather than a standalone appliance app. Install the supplied skill using one of the routes below. A successful run produces a kit folder or download; missing facts and files are listed explicitly. Image reading, web research and script execution must be available in the agent you choose.

## Set it up

### If you use Claude (claude.ai or the Claude app)

Use the skill-upload route if Skills and code execution are available for your account. Workspace policy and product availability can affect access; the instructions below are not a guarantee for every plan.

1. Download **appliance-kit.zip** from the [latest release](../../releases/latest). Don't unzip it.
2. Open Claude in a web browser at [claude.ai](https://claude.ai) and sign in.
3. Go to **Settings > Capabilities** and turn on **Code execution and file creation**.
4. Go to **Customize > Skills**, tap **+**, then **+ Create skill**, then **Upload a skill**. Choose the **appliance-kit.zip** file you downloaded.
5. Start a new chat. Take a photo of the sticker and send it with a message like:

   > Here's the label on my dishwasher. Make me an appliance kit.

One thing to know: depending on your account's settings, Claude may not be allowed to download files from manufacturers' websites inside a chat. If it can't, it finds the manual and sends you the link instead. Tap the link, save the PDF, and send the PDF back in the same chat; Claude then adds it to your kit with a searchable version. Either way, at the end Claude gives you the whole folder as one download.

On a Team or Enterprise plan, an owner has to allow skills first (Organization settings > Plugins & skills).

### If you use ChatGPT

This repo supplies a standalone skill folder and a ZIP, not a ChatGPT plugin. OpenAI documents different loading routes for standalone skills and plugins; use the [current skill instructions](https://learn.chatgpt.com/docs/build-skills) for your ChatGPT or Codex surface and check workspace policy. The local Codex folder route is below.

The full workflow needs image reading, web research, Python execution and file creation. Once the skill is loaded with those tools available, send the label photo and ask it to make an appliance kit. A product's ability to read `SKILL.md` does not by itself verify the full workflow. If you cannot load the skill, use the request below for a narrower result.

### Without the skill

With image reading and web research available, send the photo with this message:

> Read the model and serial number from this appliance label and repeat them back to me. Tell me how old it is from the serial number, check cpsc.gov for any recall of this model, find the official owner's manual PDF and give me the link, and write me a short, plain guide to the routine cleaning the manual recommends, with the manual page for each step.

That request asks for facts, links and care guidance; it does not install or run the kit-building scripts.

## If you use Claude Code or Codex

The skill is the folder `skill/appliance-kit/`. It needs Python 3.9 or newer with `pymupdf` and `Pillow`:

```
pip install -r skill/appliance-kit/requirements.txt
```

- **Claude Code:** copy or link `skill/appliance-kit` to `~/.claude/skills/appliance-kit`.
- **Codex:** copy or link it to `~/.agents/skills/appliance-kit`.

Then give it a photo: "Make an appliance kit from label.jpg". Kits go to `~/Documents/Appliances/<Brand Type Model>/` (set `APPLIANCE_KIT_ROOT` to change that), with an `index.md` listing every appliance.

## What's in a kit

```
Appliances/
  index.md                       every appliance you've added
  GE Dishwasher GSD5560G00SS/
    briefing.md                  the plain guide
    briefing.html, briefing.pdf  one page to print and stick inside a cupboard
    kit.json                     every fact, with where it came from
    label/                       your photos
    manual/                      the original PDF, manual.md and page pictures
    diagrams/                    the parts diagram and the marked-up care guide
```

If something can't be found (a blurry photo, a brand whose dates aren't decoded, a manual that isn't online), you still get the folder, with a **Missing** list saying what's absent and the one thing to try.

## What it covers, and what it doesn't

- Build dates from serial numbers for GE, Whirlpool (with Maytag, KitchenAid, Amana and Jenn-Air), Frigidaire and Electrolux, LG, and Bosch (with Thermador and Gaggenau). Samsung and other brands say "not decoded" rather than guess.
- Recalls come from the US Consumer Product Safety Commission only.
- Care means owner care: cleaning filters, screens, gaskets and vents. It never tells you to open panels or touch wiring, gas or water lines; for those it says to call for service.
- No manuals or diagrams are included in this repository. The skill fetches them from the maker and parts sites when you run it.

## Help

For setup questions or missing kit output, [open an issue](https://github.com/dtiger1889-ops/appliance-kit/issues) with the agent/runtime and a redacted error description. Keep appliance serial numbers and label photos private unless you choose to share them.

## For developers

```
pip install pytest pymupdf Pillow
python -m pytest tests           # APPLIANCE_KIT_NETWORK=1 adds the live recall lookup
python tools/package.py          # builds dist/appliance-kit.zip for the release
```

"""Offline tests for the kit pipeline (recall parsing, rendering, diagram, public-core hygiene).

Set APPLIANCE_KIT_NETWORK=1 to also run the live CPSC lookup.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "appliance-kit"
SCRIPTS = SKILL / "scripts"
FIX = ROOT / "tests" / "fixtures" / "ge_gsd5560g"
sys.path.insert(0, str(SCRIPTS))

import recall_check  # noqa: E402

CPSC_05116 = ("The following models are included in this recall and were sold after January 20, 2004: "
              "GE dishwasher models GSD5500G, GSD5560G, GSD5800G, GSD5900G, GSD5960G, EDW3000G, and "
              "EDW3060G, with serial numbers with the first letter A through T and the second letter G, "
              "or the serial letters VF.")


def run(*args):
    out = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize("serial,verdict", [
    ("DF123456A", "not covered"),   # the fixture: built Feb 2003, outside the range
    ("AG123456", "covered"),        # second letter G
    ("VF123456", "covered"),        # serial letters VF
    ("ZG123456", "not covered"),    # first letter outside A-T
])
def test_recall_05116_serial_ranges(serial, verdict):
    assert recall_check.serial_verdict(CPSC_05116, serial)[0] == verdict


@pytest.mark.parametrize("text", ["serial numbers beginning with VF or VG", "the serial letters VF, VG and VH"])
def test_recall_prefix_lists_count_every_item(text):
    assert recall_check.serial_verdict(text, "VG123456")[0] == "covered"
    assert recall_check.serial_verdict(text, "DF123456")[0] == "not covered"


def test_recall_unparseable_is_unclear():
    assert recall_check.serial_verdict("Units made in spring 2004 are affected.", "DF123456A")[0] == "unclear"


def test_manual_check_rejects_a_different_model_sharing_a_prefix():
    import fetch_manual
    pats = fetch_manual.model_patterns("GSD5560G00SS")
    assert "GSD5560G" in pats and "GSD5500" in pats
    assert not any(p in "GSD5599" for p in pats)


def test_model_stems_reach_series():
    assert "GSD5560G" in recall_check.stems("GSD5560G00SS")


@pytest.mark.skipif(os.environ.get("APPLIANCE_KIT_NETWORK") != "1", reason="network test")
def test_recall_live_fixture():
    d = run(SCRIPTS / "recall_check.py", "--model", "GSD5560G00SS", "--serial", "DF123456A")
    assert d["verdict"] == "not covered"
    assert any(r["number"] == "05116" for r in d["recalls"])


def fake_kit(tmp_path):
    """The fixture kit with placeholder files standing in for the downloaded manual and images."""
    from PIL import Image
    kit = tmp_path / "Appliances" / "GE Dishwasher GSD5560G00SS"
    for sub in ("label", "manual/pages", "diagrams"):
        (kit / sub).mkdir(parents=True)
    k = json.loads((FIX / "kit.json").read_text(encoding="utf-8"))
    for p in k["label"]["photos"]:
        Image.new("RGB", (40, 30), "gray").save(kit / p, "JPEG")
    import pymupdf
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "GSD5500 series owner's manual")
    doc.save(str(kit / k["manual"]["pdf"]))
    (kit / k["manual"]["markdown"]).write_text("# manual\n", encoding="utf-8")
    Image.new("RGB", (750, 800), "white").save(kit / "diagrams" / "partselect-00113478i03.gif")
    shutil.copy(FIX / "guide.json", kit / "diagrams" / "guide.json")
    (kit / "kit.json").write_text(json.dumps(k), encoding="utf-8")
    return kit


def test_render_fixture_produces_every_file(tmp_path):
    kit = fake_kit(tmp_path)
    g = run(SCRIPTS / "annotate_diagram.py", kit / "diagrams" / "guide.json", kit / "diagrams" / "filter-cleaning-guide.png")
    assert g["unsourced_steps"] == []
    out = run(SCRIPTS / "build_kit.py", "render", kit)
    assert out["errors"] == [] and out["missing"] == []
    for f in ("briefing.md", "briefing.html", "briefing.pdf"):
        assert (kit / f).stat().st_size > 0
    md = (kit / "briefing.md").read_text(encoding="utf-8")
    assert "February 2003" in md and "05-116" in md and "Manual p. 14" in md
    assert "GSD5560G00SS" in (kit.parent / "index.md").read_text(encoding="utf-8")


def test_briefing_text_from_a_phone_run():
    # Shapes a Claude app run wrote for a microwave: brand already in the name, a manual page as a
    # fact source, and a service line that starts with "If".
    import build_kit
    k = {"appliance": {"brand": "Whirlpool", "type": "Microwave", "name": "Whirlpool 1.7 cu. ft. hood WMH1"},
         "facts": [{"text": "Arcing means food buildup.", "source": "Manual p. 5"}],
         "care": [{"title": "Filter", "steps": [{"text": "Wash it.", "source": "Manual p. 4"}],
                   "when_to_call": "If the filter is bent, replace it."}]}
    md = build_kit.briefing_md("", k, [])
    assert "# Microwave: Whirlpool 1.7 cu. ft." in md and "Whirlpool Whirlpool" not in md
    assert "](Manual p. 5)" not in md and "_(Source: Manual p. 5)_" in md
    assert "call for service if:** the filter is bent" in md


@pytest.mark.parametrize("ap,title", [
    ({"brand": "GE", "model": "GE123"}, "GE GE123"),              # a model number is not a full name
    ({"brand": "GE", "name": "Genesis range"}, "GE Genesis range"),  # brand must be a whole word
])
def test_title_keeps_a_brand_the_name_does_not_start_with(ap, title):
    import build_kit
    assert build_kit.briefing_md("", {"appliance": {"type": "Range", **ap}}, []).startswith(f"# Range: {title}\n")


def test_service_condition_as_a_list_still_renders():
    import build_kit
    k = {"appliance": {"type": "Range"}, "care": [{"title": "Hob", "when_to_call": ["sparks appear", "the cord is damaged"]}]}
    assert "call for service if:** sparks appear; the cord is damaged" in build_kit.briefing_md("", k, [])


def test_only_real_web_addresses_become_links():
    import build_kit
    k = {"appliance": {"type": "Range"}, "facts": [{"text": "A", "source": "http manual p. 5"},
                                                   {"text": "B", "source": "HTTPS://example.com/m"}]}
    md = build_kit.briefing_md("", k, [])
    assert "- A _(Source: http manual p. 5)_" in md and "- B ([source](HTTPS://example.com/m))" in md
    assert build_kit.src_urls(k) == ["HTTPS://example.com/m"]


def test_pdf_failure_lands_in_missing_list(tmp_path, monkeypatch, capsys):
    import build_kit
    kit = fake_kit(tmp_path)

    def boom(*a):
        raise RuntimeError("no Story support")
    monkeypatch.setattr(build_kit, "html_to_pdf", boom)
    build_kit.cmd_render(type("A", (), {"kit_dir": str(kit)})())
    out = json.loads(capsys.readouterr().out)
    assert "Printable PDF" in out["missing"]
    assert "briefing.html in a browser" in (kit / "briefing.md").read_text(encoding="utf-8")
    assert "Printable PDF" in (kit / "briefing.html").read_text(encoding="utf-8")


def test_blurry_unknown_brand_still_builds_with_missing_list(tmp_path):
    init = run(SCRIPTS / "build_kit.py", "init", "--root", tmp_path / "Appliances", "--brand", "Acme", "--type", "Washer")
    kit = pathlib.Path(init["kit_dir"])
    (kit / "kit.json").write_text(json.dumps({"appliance": {"brand": "Acme", "type": "Washer"},
                                              "age": run(SCRIPTS / "serial_decode.py", "--brand", "Acme", "--serial", "X1")}),
                                  encoding="utf-8")
    out = run(SCRIPTS / "build_kit.py", "render", kit)
    assert {"Model number", "Serial number", "Owner's manual (PDF)", "Build date", "Recall check"} <= set(out["missing"])
    md = (kit / "briefing.md").read_text(encoding="utf-8")
    assert "## Missing" in md and "sharper" in md


# A Windows home folder, with any slash style, including the doubled backslashes of JSON and Python text.
HOME_FOLDER = r"[a-z]:[\\/]+users[\\/]+"


@pytest.mark.parametrize("sep", ["/", "\\", "\\\\"])
def test_home_folder_pattern_catches_every_slash_style(sep):
    import re
    assert re.search(HOME_FOLDER, f"c:{sep}users{sep}x")


def home_paths():
    """This machine's home folder, in both slash styles (never a bare short name like "user")."""
    h = str(pathlib.Path.home()).lower().rstrip("\\/")
    # A trailing separator keeps "/user" from matching "/mnt/user-data".
    return {h.replace("\\", "/") + "/", h.replace("/", "\\") + "\\"} if len(h) > 3 else set()


def test_public_core_has_no_personal_references():
    # Home folders are matched by pattern and by this machine's own path,
    # so the test never spells out a real one.
    import re
    banned = {"obsidian", "checkpoint", "vault"} | home_paths()
    for p in SKILL.rglob("*"):
        if p.is_file() and p.suffix in {".md", ".py", ".txt", ".json"}:
            text = p.read_text(encoding="utf-8").lower()
            assert not re.search(HOME_FOLDER, text), f"a home folder path in {p.relative_to(ROOT)}"
            for b in banned:
                assert b not in text, f"{b!r} found in {p.relative_to(ROOT)}"


def test_home_check_ignores_short_or_empty_names(monkeypatch):
    for home in ("/", "/user", "C:\\"):
        monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls, h=home: pathlib.PurePath(h)))
        assert all(len(b) > 3 for b in home_paths())
        assert not any(b in "/mnt/user-data/outputs" for b in home_paths())


def test_repo_ships_no_manuals_or_diagrams():
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout.split()
    assert "skill/appliance-kit/SKILL.md" in tracked  # an empty listing proves nothing
    assert shipped_images(tracked) == []


# The one reviewed picture: the README's kit page, rendered from invented data and a plain drawing.
README_PICTURE = "assets/briefing-page.png"


def shipped_images(tracked):
    return [t for t in tracked if t.lower().endswith((".pdf", ".png", ".gif", ".jpg", ".jpeg"))
            and t != README_PICTURE]


def test_only_the_readme_picture_is_exempt():
    assert shipped_images([README_PICTURE, "assets/manual.pdf", "assets/label.jpg"]) == \
        ["assets/manual.pdf", "assets/label.jpg"]

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skill" / "appliance-kit" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from serial_decode import decode  # noqa: E402


def test_ge_fixture_with_hint():
    r = decode("GE", "DF123456A", hint_year=2002)
    assert r["month"] == 2
    assert 2003 in r["candidates"]
    assert r["year"] == 2003 and r["confidence"] == "high" and r["decoded"]


def test_ge_without_hint_is_ambiguous():
    r = decode("General Electric", "df-123456a")
    assert r["month"] == 2 and r["year"] is None
    assert r["candidates"][:3] == [1991, 2003, 2015]
    assert r["confidence"] == "medium"


def test_ge_published_example():
    r = decode("Hotpoint", "LT221102")
    assert r["month"] == 6 and 1998 in r["candidates"] and 1986 in r["candidates"]


def test_whirlpool_family():
    r = decode("KitchenAid", "CA24123456")
    assert (r["year"], r["month"]) == (2021, 6)
    r = decode("Maytag", "K905123")
    assert r["year"] == 2019 and r["month"] in (1, 2)
    assert not decode("Whirlpool", "9912345")["decoded"]


def test_frigidaire():
    r = decode("Frigidaire", "NF11910958", hint_year=2000)
    assert r["year"] == 2001 and r["confidence"] == "low"
    assert 1991 in r["candidates"]


def test_lg():
    r = decode("LG", "503KWAB12345")
    assert r["month"] == 3 and 2015 in r["candidates"]
    assert r["year"] is None
    assert decode("LG", "503KWAB12345", hint_year=2014)["year"] == 2015


def test_bosch_fd():
    r = decode("Bosch", "", fd="FD 9208")
    assert (r["year"], r["month"]) == (2012, 8) and r["decoded"]
    r = decode("Thermador", "", fd="7902")
    assert (r["year"], r["month"]) == (1999, 2)
    assert not decode("Bosch", "12345")["decoded"]
    assert not decode("Bosch", "92081234")["decoded"]  # a plain serial is never read as an FD
    assert decode("Bosch", "FD 9208")["month"] == 8


def test_samsung_not_decoded():
    r = decode("Samsung", "0A1B2C3D4E5F6G7")
    assert r["decoded"] is False and r["confidence"] == "none"


def test_unknown_brand():
    r = decode("Acme", "XYZ123")
    assert r["decoded"] is False and r["confidence"] == "none"
    assert r["note"] == "not decoded for this brand"


def test_cli_json():
    out = subprocess.run([sys.executable, str(SCRIPTS / "serial_decode.py"), "--brand", "GE",
                          "--serial", "DF123456A", "--hint-year", "2002"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["year"] == 2003

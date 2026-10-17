#!/usr/bin/env python3
"""Decode an appliance build date from its serial number (or Bosch FD number).

Usage:
  serial_decode.py --brand GE --serial DF123456A [--hint-year 2002] [--fd 9208]

Prints one JSON object. Also importable: decode(brand, serial, hint_year=None, fd=None).
Rules and sources: references/serial-codes.md. Stdlib only, Python 3.9+.
"""
import argparse
import json
import re
import sys
from datetime import date

FIRST_YEAR = 1980

GE_MONTHS = {"A": 1, "D": 2, "F": 3, "G": 4, "H": 5, "L": 6,
             "M": 7, "R": 8, "S": 9, "T": 10, "V": 11, "Z": 12}
# Year letters cycle every 12 years starting G = 1980.
GE_YEAR_ORDER = "GHLMRSTVZADF"

# Whirlpool-built appliances, 2010 onward: one year character, 2010..2026.
WHIRLPOOL_YEARS = {"0": 2010, "1": 2011, "2": 2012, "3": 2013, "4": 2014,
                   "5": 2015, "6": 2016, "7": 2017, "8": 2018, "9": 2019,
                   "X": 2020, "A": 2021, "B": 2022, "C": 2023, "D": 2024,
                   "E": 2025, "F": 2026}

GE_ALIASES = {"GE", "GENERALELECTRIC", "GEAPPLIANCES", "HOTPOINT", "GEPROFILE",
              "CAFE", "MONOGRAM"}
WHIRLPOOL_ALIASES = {"WHIRLPOOL", "MAYTAG", "KITCHENAID", "AMANA", "JENNAIR",
                     "ESTATE", "ROPER"}
FRIGIDAIRE_ALIASES = {"FRIGIDAIRE", "ELECTROLUX", "FRIGIDAIREGALLERY",
                      "FRIGIDAIREPROFESSIONAL"}
SAMSUNG_ALIASES = {"SAMSUNG"}
LG_ALIASES = {"LG", "LGELECTRONICS"}
BOSCH_ALIASES = {"BOSCH", "THERMADOR", "GAGGENAU", "SIEMENS"}


def _norm_brand(brand):
    return re.sub(r"[^A-Z0-9]", "", (brand or "").upper())


def _norm_serial(serial):
    return re.sub(r"[\s\-]", "", (serial or "")).upper()


def _family(brand):
    b = _norm_brand(brand)
    if b in GE_ALIASES:
        return "GE"
    if b in WHIRLPOOL_ALIASES:
        return "Whirlpool"
    if b in FRIGIDAIRE_ALIASES:
        return "Frigidaire"
    if b in SAMSUNG_ALIASES:
        return "Samsung"
    if b in LG_ALIASES:
        return "LG"
    if b in BOSCH_ALIASES:
        return "Bosch"
    return None


def _week_to_month(week):
    return min(12, int((week - 1) * 7 / 30.4375) + 1)


def _result(brand, family, serial, **kw):
    out = {"brand": brand, "family": family, "serial": serial,
           "decoded": False, "month": None, "year": None, "candidates": [],
           "confidence": "none", "rule": "", "source": [], "note": ""}
    out.update(kw)
    return out


def _finish(res, candidates, hint_year, cap):
    """Pick a year from candidates; apply hint; cap confidence."""
    res["candidates"] = candidates
    if not candidates:
        res.update(decoded=False, confidence="none",
                   note="The serial matched the pattern but gave no year in 1980 to now; "
                        "treat as not decoded.")
        return res
    if len(candidates) == 1:
        res.update(decoded=True, year=candidates[0], confidence=cap)
        return res
    if hint_year is not None:
        later = [y for y in candidates if y >= hint_year - 1]
        if later:
            res.update(decoded=True, year=later[0], confidence=cap)
            res["note"] = (res["note"] + " Year chosen as the earliest candidate at or after "
                           "the hint year minus 1; the code repeats on a cycle.").strip()
            return res
    res.update(decoded=True, year=None, confidence="medium" if cap != "low" else "low")
    res["note"] = (res["note"] + " The year code repeats on a cycle: choose among the "
                   "candidate years using the model's age or the manual's date.").strip()
    return res


def _decode_ge(brand, serial, hint_year, cur):
    src = ["https://www.appliancefactoryparts.com/blog/2010/02/how-to-find-the-age-of-your-appliance/",
           "https://servicemag.org/guides/read-appliance-model-serial-number"]
    rule = ("First letter = month (A Jan, D Feb, F Mar, G Apr, H May, L Jun, M Jul, R Aug, "
            "S Sep, T Oct, V Nov, Z Dec). Second letter = year, repeating every 12 years "
            "(G=1980, H=1981 ... F=1991, G=1992 ...).")
    res = _result(brand, "GE", serial, rule=rule, source=src)
    if len(serial) < 2 or serial[0] not in GE_MONTHS or serial[1] not in GE_YEAR_ORDER:
        res["note"] = ("Serial does not start with two GE date letters "
                       "(from A D F G H L M R S T V Z); not decoded. Some GE HVAC and "
                       "Canadian (Camco) serials use other layouts.")
        return res
    idx = GE_YEAR_ORDER.index(serial[1])
    cands = [y for y in range(FIRST_YEAR, cur + 1) if (y - FIRST_YEAR) % 12 == idx]
    res["month"] = GE_MONTHS[serial[0]]
    return _finish(res, cands, hint_year, "high")


def _decode_whirlpool(brand, serial, hint_year, cur):
    src = ["https://www.appliancepartspros.com/b/?p=24722",
           "https://servicemag.org/guides/read-appliance-model-serial-number"]
    rule = ("Serials from 2010 onward: 1-2 division letters, then one year character "
            "(0-9 = 2010-2019, X = 2020, A-F = 2021-2026), then a 2-digit week 01-53, "
            "then a sequence number.")
    res = _result(brand, "Whirlpool", serial, rule=rule, source=src)
    for n in (1, 2):
        m = re.match(r"^([A-Z]{%d})([0-9XA-F])(\d{2})" % n, serial)
        if m and 1 <= int(m.group(3)) <= 53 and m.group(2) in WHIRLPOOL_YEARS:
            year = WHIRLPOOL_YEARS[m.group(2)]
            if year > cur:
                continue
            week = int(m.group(3))
            res.update(decoded=True, year=year, candidates=[year], week=week,
                       month=_week_to_month(week), confidence="medium")
            res["note"] = ("Month is estimated from week %d (about +/- 1 month). "
                           "Year character X is also reported on some 2010 units; confirm "
                           "against the model's age." % week)
            return res
    res["note"] = ("Not in the 2010-and-later Whirlpool format; older Whirlpool, Maytag, "
                   "KitchenAid and Amana serials used different era-specific codes that "
                   "could not be verified from two sources. Not decoded.")
    return res


def _decode_frigidaire(brand, serial, hint_year, cur):
    src = ["https://www.appliancefactoryparts.com/blog/2010/02/how-to-find-the-age-of-your-appliance/"]
    rule = ("Community convention, not a manufacturer spec: 1-2 plant letters, then one "
            "year digit (repeats every 10 years), then a 2-digit week 01-53.")
    res = _result(brand, "Frigidaire", serial, rule=rule, source=src)
    for n in (2, 1):
        m = re.match(r"^([A-Z]{%d})(\d)(\d{2})" % n, serial)
        if m and 1 <= int(m.group(3)) <= 53:
            d, week = int(m.group(2)), int(m.group(3))
            cands = [y for y in range(FIRST_YEAR, cur + 1) if y % 10 == d]
            res["month"] = _week_to_month(week)
            res["week"] = week
            res["note"] = ("Single community source; Frigidaire publishes no decoder. Month "
                           "is estimated from week %d. Check the rating label for a printed "
                           "date first." % week)
            return _finish(res, cands, hint_year, "low")
    res["note"] = "Serial does not match the letters-digit-week layout; not decoded."
    return res


def _decode_samsung(brand, serial, hint_year, cur):
    return _result(
        brand, "Samsung", serial, confidence="none",
        rule="Not decoded: sources give conflicting year-letter tables.",
        source=["https://servicemag.org/guides/read-appliance-model-serial-number",
                "https://homespy.io/samsung-serial-lookup"],
        note="not decoded for this brand: Samsung year letters conflict between sources "
             "(one guide maps Q-Z to 2016-2025, another maps R-Z to 2001-2010), so no date "
             "is given. Use the printed manufacture date on the label or Samsung support.")


def _decode_lg(brand, serial, hint_year, cur):
    src = ["https://www.lg.com/ca_en/support/product-help/CT32001121-20152844733253",
           "https://servicemag.org/guides/read-appliance-model-serial-number"]
    rule = ("First 3 digits of the serial: 1st = last digit of the year (repeats every "
            "10 years), 2nd-3rd = month 01-12.")
    res = _result(brand, "LG", serial, rule=rule, source=src)
    m = re.match(r"^(\d)(\d{2})", serial)
    if not m or not 1 <= int(m.group(2)) <= 12:
        res["note"] = ("Serial does not start with year digit plus month 01-12 "
                       "(e.g. 503 = March of a year ending in 5); not decoded.")
        return res
    d = int(m.group(1))
    res["month"] = int(m.group(2))
    cands = [y for y in range(FIRST_YEAR, cur + 1) if y % 10 == d]
    return _finish(res, cands, hint_year, "high")


def _decode_bosch(brand, serial, hint_year, cur, fd):
    src = ["https://servicemag.org/guides/read-appliance-model-serial-number",
           "https://www.hunker.com/13407479/how-to-determine-what-year-my-bosch-shu5315-dishwasher-was-made",
           "https://homespy.io/bosch-serial-lookup"]
    rule = ("Uses the FD number printed on the label (not the serial): add 20 to the first "
            "two digits to get the two-digit year (92 + 20 = 112 = 2012); last two digits "
            "= month 01-12.")
    res = _result(brand, "Bosch", serial, rule=rule, source=src)
    # The serial carries no date; read it as an FD only when it is written as one ("FD 9208").
    raw = fd if fd else (serial if re.match(r"^\s*FD", str(serial or ""), re.I) else "")
    digits = re.sub(r"^FD", "", re.sub(r"[\s\-]", "", str(raw or "")).upper())
    m = re.match(r"^(\d{2})(\d{2})", digits)
    if not m or not 1 <= int(m.group(2)) <= 12:
        res["note"] = ("Needs the FD number from the label (e.g. FD 9208): four digits "
                       "with a month 01-12 at the end. Not decoded.")
        return res
    yy = (int(m.group(1)) + 20) % 100
    cands = [y for y in range(FIRST_YEAR, cur + 1) if y % 100 == yy]
    res["month"] = int(m.group(2))
    res["note"] = ("Unofficial but consistent across three consumer sources; Bosch does not "
                   "publish the rule. One site reads newer FD codes differently, so treat "
                   "as medium confidence.")
    return _finish(res, cands, hint_year, "medium")


def decode(brand, serial, hint_year=None, fd=None):
    cur = date.today().year
    s = _norm_serial(serial)
    fam = _family(brand)
    if fam is None:
        return _result(brand, None, s, note="not decoded for this brand",
                       rule="No verified rule for this brand.")
    if fam == "GE":
        return _decode_ge(brand, s, hint_year, cur)
    if fam == "Whirlpool":
        return _decode_whirlpool(brand, s, hint_year, cur)
    if fam == "Frigidaire":
        return _decode_frigidaire(brand, s, hint_year, cur)
    if fam == "Samsung":
        return _decode_samsung(brand, s, hint_year, cur)
    if fam == "LG":
        return _decode_lg(brand, s, hint_year, cur)
    return _decode_bosch(brand, s, hint_year, cur, fd)


def main(argv=None):
    p = argparse.ArgumentParser(description="Decode an appliance build date from its serial.")
    p.add_argument("--brand", required=True)
    p.add_argument("--serial", default="")
    p.add_argument("--hint-year", type=int, default=None,
                   help="Approximate year, e.g. the manual's publication year.")
    p.add_argument("--fd", default=None, help="Bosch/Siemens FD number from the label.")
    a = p.parse_args(argv)
    json.dump(decode(a.brand, a.serial, a.hint_year, a.fd), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

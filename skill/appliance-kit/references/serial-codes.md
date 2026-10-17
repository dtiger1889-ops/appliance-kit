# Serial-number date codes

Used by `scripts/serial_decode.py`. None of these rules are published by the manufacturers as
official consumer decoders; they are community and parts-site conventions. Every code with a
single-digit or single-letter year repeats on a cycle, so the script returns all plausible years
(1980 to now) and only picks one when there is one candidate or a hint year (the manual's
publication year, the model's era) settles it. The rating label sometimes prints a real
manufacture date: use that first.

Brands not listed here: report "not decoded".

## GE (also Hotpoint, GE Profile, Cafe, Monogram) - confidence high

- First letter = month: A Jan, D Feb, F Mar, G Apr, H May, L Jun, M Jul, R Aug, S Sep, T Oct, V Nov, Z Dec.
- Second letter = year, a 12-letter cycle: G=1980, H=1981, L=1982, M=1983, R=1984, S=1985, T=1986, V=1987, Z=1988, A=1989, D=1990, F=1991, then G=1992 and so on (F = 1991, 2003, 2015).
- Cycle caveat: the same letter recurs every 12 years.
- Not covered: GE HVAC and Canadian Camco serials use other layouts.
- Sources (agree, including the 2013-2025 years): https://www.appliancefactoryparts.com/blog/2010/02/how-to-find-the-age-of-your-appliance/ and https://servicemag.org/guides/read-appliance-model-serial-number

## Whirlpool, Maytag, KitchenAid, Amana, Jenn-Air - confidence medium, 2010 onward only

- Layout: 1-2 division letters, one year character, a 2-digit week (01-53), then a sequence number. Example KC1707945: K, C = 2023, week 17.
- Year character: 0-9 = 2010-2019, X = 2020, A = 2021, B = 2022, C = 2023, D = 2024, E = 2025, F = 2026.
- Month is estimated from the week (about plus or minus one month).
- Cycle caveat: X is also reported on some 2010 units. Pre-2010 serials use different era-specific codes; they are not decoded (one parts site gives old letter charts, but only one source, so not used).
- Sources (agree on layout and the year characters): https://www.appliancepartspros.com/b/?p=24722 and https://servicemag.org/guides/read-appliance-model-serial-number

## Frigidaire, Electrolux - confidence low

- Layout: 1-2 plant letters, one year digit, a 2-digit week. Example NF11910958: NF, year digit 1, week 19.
- Cycle caveat: the digit repeats every 10 years (1 = 1991, 2001, 2011, 2021).
- Only one source gives the layout with a worked example; others say Frigidaire publishes no consumer decoder and one Electrolux guide notes a decade ambiguity. Treat as a hint.
- Sources: https://www.appliancefactoryparts.com/blog/2010/02/how-to-find-the-age-of-your-appliance/ ; no-decoder warning: https://www.appliancepartspros.com/b/?p=24770

## LG - confidence high (month), year by cycle

- First 3 digits of the serial: first = last digit of the year, next two = month 01-12. 503 = March of a year ending in 5 (2015 or 2025).
- Cycle caveat: decade is not encoded, 10-year repeat.
- Another site reads the two digits as a week; LG's own support page says month, so month is used.
- Sources: https://www.lg.com/ca_en/support/product-help/CT32001121-20152844733253 and https://servicemag.org/guides/read-appliance-model-serial-number

## Bosch (also Thermador, Gaggenau, Siemens) - confidence medium

- Use the FD number on the label (written "FD 9208"), not the serial.
- First two digits plus 20 = two-digit year (92 + 20 = 112 = 2012); last two digits = month 01-12. FD 9208 = August 2012; FD 7902 = February 1999.
- Cycle caveat: the year repeats every 100 years, so within 1980 to now there is one answer. An FD number that gives no year in range is reported as not decoded.
- Disagreement: one site describes the first digit as a decade; its own example only works with the +20 rule, and one site reads a newer FD 4xxx as 2022, which the +20 rule would not give. Hence medium.
- Sources: https://servicemag.org/guides/read-appliance-model-serial-number , https://www.hunker.com/13407479/how-to-determine-what-year-my-bosch-shu5315-dishwasher-was-made (says "add 2" but its examples need +20), https://homespy.io/bosch-serial-lookup

## Samsung - NOT decoded

- Position rules agree across sources (15-character serial: 8th = year, 9th = month; 11-character: 4th and 5th; month 1-9 then A, B, C).
- The year-letter tables conflict (one maps Q-Z to 2016-2025; another maps R-Z to 2001-2010 and cycles every 20 years), so no table could be verified. The script returns decoded false with a note.
- Sources: https://servicemag.org/guides/read-appliance-model-serial-number , https://homespy.io/samsung-serial-lookup

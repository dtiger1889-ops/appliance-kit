#!/usr/bin/env python3
"""Build the release ZIP: dist/appliance-kit.zip holding the appliance-kit/ folder.

Claude.ai's upload wants a ZIP whose top folder matches the skill name and contains
SKILL.md. Caches and test output are left out.
"""
import os
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "skill" / "appliance-kit"
OUT = ROOT / "dist" / "appliance-kit.zip"
SKIP_DIRS = {"__pycache__", ".pytest_cache"}

OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for base, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in sorted(files):
            if fn.endswith(".pyc"):
                continue
            p = pathlib.Path(base) / fn
            z.write(p, pathlib.Path("appliance-kit") / p.relative_to(SRC))
with zipfile.ZipFile(OUT) as z:
    names = z.namelist()
assert "appliance-kit/SKILL.md" in names, "SKILL.md missing from the ZIP"
print(f"{OUT} ({len(names)} files)")

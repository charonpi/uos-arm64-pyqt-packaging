#!/usr/bin/env python3
"""Validate the skill package and build the two marketplace-ready ZIP files.

Part of the uos-arm64-pyqt-packaging release tooling (NOT shipped inside the skill).

    python3 tools/make_release.py

Produces in dist/:
    uos-arm64-pyqt-packaging.zip                  # top-level skill folder (WorkBuddy client "Upload skill")
    uos-arm64-pyqt-packaging-openplatform.zip    # flat root, SKILL.md at zip root (open.workbuddy.cn)
    SHA256SUMS.txt
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "uos-arm64-pyqt-packaging"
DIST = ROOT / "dist"
NAME = "uos-arm64-pyqt-packaging"
REQUIRED_FRONTMATTER = [
    "name", "display_name", "display_name_en", "description", "description_zh",
    "description_en", "examples_zh", "examples_en", "version", "author", "agent_created",
]
MAX_DEPTH = 2  # open platform: only two directory levels inside the package


def fail(msg: str):
    print("FAIL: " + msg, file=sys.stderr)
    sys.exit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_frontmatter() -> dict:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        fail("SKILL.md has no valid YAML frontmatter")
    fm = m.group(1)
    missing = [k for k in REQUIRED_FRONTMATTER if not re.search(r"^%s:" % re.escape(k), fm, re.MULTILINE)]
    if missing:
        fail("missing frontmatter fields: " + ", ".join(missing))
    vm = re.search(r"^version:\s*([^\s]+)", fm, re.MULTILINE)
    version = vm.group(1).strip().strip('"\'') if vm else "unknown"
    nm = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    if nm and nm.group(1).strip() != NAME:
        fail("frontmatter name != directory name")
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        fail("version must be semantic (x.y.z), got %s" % version)
    desc = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
    if desc and ("<" in desc.group(1) or ">" in desc.group(1)):
        fail("description must not contain angle brackets")
    return {"version": version, "body": text}


def check_structure():
    if not (SKILL / "SKILL.md").is_file():
        fail("SKILL.md missing")
    for path in SKILL.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(SKILL)
        if len(rel.parts) > MAX_DEPTH:
            fail("directory nesting exceeds 2 levels: %s" % rel.as_posix())
        if path.suffix in (".pyc", ".bak") or path.name.startswith("."):
            fail("unwanted file in package: %s" % rel.as_posix())
    # every resource referenced from SKILL.md must exist
    body = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for ref in sorted(set(re.findall(r"`((?:scripts|references|templates|assets)/[^`]+)`", body))):
        ref = ref.split()[0]
        if "*" in ref:  # glob-style reference such as `templates/*.tpl`
            matches = list(SKILL.glob(ref))
            if not matches:
                fail("SKILL.md references missing pattern: %s" % ref)
        elif not (SKILL / ref).exists():
            fail("SKILL.md references missing file: %s" % ref)
    print("OK  structure: two-level layout, all referenced resources present")


def check_icon():
    icon = SKILL / "assets" / "icon-512.png"
    if not icon.is_file():
        fail("assets/icon-512.png missing (run tools/make_icon.py)")
    try:
        from PIL import Image
        with Image.open(icon) as im:
            if im.size != (512, 512):
                fail("icon must be 512x512, got %s" % (im.size,))
    except ImportError:
        pass
    if icon.stat().st_size > 500 * 1024:
        fail("icon exceeds 500 KB")
    print("OK  icon: 512x512, %d bytes" % icon.stat().st_size)


def build_zips():
    DIST.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SKILL.rglob("*") if p.is_file())
    wrapped = DIST / (NAME + ".zip")
    flat = DIST / (NAME + "-openplatform.zip")

    with zipfile.ZipFile(wrapped, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, Path(NAME) / p.relative_to(SKILL))
    with zipfile.ZipFile(flat, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(SKILL))

    with zipfile.ZipFile(flat) as z:
        names = z.namelist()
        if "SKILL.md" not in names:
            fail("open-platform zip has no SKILL.md at root")
        if any(n.startswith(NAME + "/") for n in names):
            fail("open-platform zip must not have a wrapping folder")

    sums = []
    for p in (wrapped, flat):
        sums.append("%s  %s" % (sha256(p), p.name))
        print("OK  %s (%d bytes, %d files)" % (p.name, p.stat().st_size, len(files)))
    (DIST / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return wrapped, flat


def main():
    meta = check_frontmatter()
    check_structure()
    check_icon()
    wrapped, flat = build_zips()
    print("\nVersion: %s" % meta["version"])
    print("WorkBuddy client upload : %s" % wrapped)
    print("Open platform submission: %s" % flat)
    print("SHA256SUMS              : %s" % (DIST / "SHA256SUMS.txt"))
    print(json.dumps({"version": meta["version"], "client_zip": wrapped.name,
                      "platform_zip": flat.name}, ensure_ascii=False))


if __name__ == "__main__":
    main()

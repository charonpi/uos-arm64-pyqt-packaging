#!/usr/bin/env python3
"""Make binary release artifacts reproducible from a text-only Git repository.

Some GitHub integrations can only write text files through their API. This tool
stores the ZIPs and the icon as base64 inside `dist/binaries.b64.json`, so a
clone of the repository can restore byte-identical binaries with one command.

    python3 tools/make_binary_manifest.py --write-manifest   # maintainer, before release
    python3 tools/make_binary_manifest.py --restore          # anyone who cloned the repo

An alternative to --restore is regenerating everything from source:
    python3 tools/make_icon.py && python3 tools/make_release.py
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "dist" / "binaries.b64.json"
TARGETS = [
    "dist/uos-arm64-pyqt-packaging.zip",
    "dist/uos-arm64-pyqt-packaging-openplatform.zip",
    "uos-arm64-pyqt-packaging/assets/icon-512.png",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_manifest() -> None:
    files = {}
    for rel in TARGETS:
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit("missing artifact: %s (run tools/make_icon.py / make_release.py)" % rel)
        data = path.read_bytes()
        files[rel] = {"sha256": digest(data), "size": len(data),
                      "b64": base64.b64encode(data).decode("ascii")}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"version": 1, "files": files}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("wrote %s (%d bytes, %d artifacts)" % (MANIFEST, MANIFEST.stat().st_size, len(files)))


def restore() -> None:
    if not MANIFEST.is_file():
        raise SystemExit("manifest not found: %s" % MANIFEST)
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for rel, meta in payload["files"].items():
        data = base64.b64decode(meta["b64"])
        if digest(data) != meta["sha256"] or len(data) != meta["size"]:
            raise SystemExit("checksum mismatch for %s" % rel)
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print("restored %s (%d bytes, sha256 verified)" % (rel, len(data)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()
    if args.write_manifest:
        write_manifest()
    else:
        restore()

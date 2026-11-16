#!/usr/bin/env python3
"""Build an `Architecture: all` .deb for UOS 20 arm64 (system python3-pyqt5).

Part of the uos-arm64-pyqt-packaging skill. Runs on Python 3.7+ itself.

Typical use (Linux build host):

    python3 build_deb.py --src ./build-src --pkg file-organizer \
        --version 1.0.0 --entry main.py --app-name "文件整理工具" \
        --third-party ./build-src/third_party --out ./dist

On Windows / hosts without dpkg-deb it automatically produces only the staging
directory (same as --staging-only); ship that directory to Linux and run:

    dpkg-deb --build --root-owner-group _staging_<pkg> <pkg>_<ver>_all.deb

Templates are read from the sibling templates/ directory when available;
otherwise the built-in fallbacks below are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TPL_DIR = Path(__file__).resolve().parent.parent / "templates"
PKG_RE = re.compile(r"^[a-z0-9][a-z0-9.+-]*$")
IGNORE = (".git", "__pycache__", "*.pyc", "*.pyo", ".venv", "venv", "dist",
          "build", "*.bak", ".DS_Store", ".idea", ".vscode")

BUILTIN_TPL = {
    "control.tpl": """Package: {{PKG}}
Version: {{VERSION}}
Section: utils
Priority: optional
Architecture: all
Depends: {{DEPENDS}}
Maintainer: {{MAINTAINER}}
Description: {{DESCRIPTION}}
""",
    "launcher.tpl": """#!/bin/sh
exec python3 {{ENTRY_PATH}} "$@"
""",
    "desktop.tpl": """[Desktop Entry]
Type=Application
Name={{APP_NAME}}
Comment={{DESCRIPTION}}
Exec=/usr/bin/{{PKG}}
Icon={{PKG}}
Terminal=false
Categories=Utility;
""",
    "bootstrap.py.tpl": """# uos-arm64-pyqt-packaging bootstrap (generated) - keep before business imports
import os as _uos_os
import sys as _uos_sys
_UOS_HERE = _uos_os.path.dirname(_uos_os.path.abspath(__file__))
if _UOS_HERE not in _uos_sys.path:
    _uos_sys.path.insert(0, _UOS_HERE)
_UOS_VENDOR = _uos_os.path.join(_UOS_HERE, "third_party")
if _UOS_VENDOR not in _uos_sys.path:
    _uos_sys.path.insert(0, _UOS_VENDOR)
# end uos-arm64-pyqt-packaging bootstrap
""",
}


def render(name: str, values: dict) -> str:
    path = TPL_DIR / name
    text = path.read_text(encoding="utf-8") if path.is_file() else BUILTIN_TPL[name]
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    if "{{" in text:
        raise ValueError("unresolved placeholder in %s: %s" % (name, text))
    return text


def copy_tree(src: Path, dst: Path) -> None:
    """Python 3.7-compatible recursive copy (no dirs_exist_ok)."""
    skip = {".git", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".vscode"}
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in skip or item.suffix in (".pyc", ".pyo", ".bak") or item.name == ".DS_Store":
            continue
        target = dst / item.name
        if item.is_dir():
            copy_tree(item, target)
        else:
            shutil.copy2(item, target)


def copy_source(src: Path, dst: Path) -> None:
    copy_tree(src, dst)


def inject_bootstrap(entry_file: Path, snippet: str) -> bool:
    import ast
    source = entry_file.read_text(encoding="utf-8")
    if "uos-arm64-pyqt-packaging bootstrap (generated)" in source:
        return False
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    body = tree.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        insert_at = body[0].end_lineno
    elif body:
        insert_at = body[0].lineno - 1
    else:
        insert_at = len(lines)
    for node in body:  # future imports must stay first
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            insert_at = max(insert_at, node.end_lineno or insert_at)
        elif node.lineno - 1 >= insert_at:
            break
    lines.insert(insert_at, snippet + "\n")
    entry_file.write_text("".join(lines), encoding="utf-8")
    return True


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build an arch:all deb for UOS 20 arm64")
    ap.add_argument("--src", required=True, help="source directory (a COPY of the project)")
    ap.add_argument("--pkg", required=True, help="lowercase Debian package name, e.g. file-organizer")
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--entry", default="main.py", help="entry .py path relative to --src")
    ap.add_argument("--app-name", default=None, help="desktop display name")
    ap.add_argument("--maintainer", default="Unknown <unknown@example.com>")
    ap.add_argument("--description", default="Python desktop application")
    ap.add_argument("--depends", default="python3 (>= 3.7), python3-pyqt5")
    ap.add_argument("--third-party", default=None, help="external vendor dir to copy as third_party/")
    ap.add_argument("--icon", default=None, help="optional PNG icon (installed to hicolor/256x256/apps)")
    ap.add_argument("--out", default="./dist", help="output directory")
    ap.add_argument("--inject-bootstrap", action="store_true",
                    help="inject the sys.path bootstrap into the staged entry file")
    ap.add_argument("--staging-only", action="store_true", help="never call dpkg-deb")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    if not src.is_dir():
        print("ERROR: --src is not a directory: %s" % src, file=sys.stderr)
        return 2
    if not PKG_RE.match(args.pkg):
        print("ERROR: --pkg must match ^[a-z0-9][a-z0-9.+-]*$", file=sys.stderr)
        return 2
    entry_rel = Path(args.entry).as_posix().lstrip("/")
    if (src / entry_rel).is_dir() or not (src / entry_rel).is_file():
        print("ERROR: entry file not found: %s" % (src / entry_rel), file=sys.stderr)
        return 2

    out.mkdir(parents=True, exist_ok=True)
    staging = out / ("_staging_" + args.pkg)
    if staging.exists():
        shutil.rmtree(staging)
    share = staging / "usr" / "share" / args.pkg
    bindir = staging / "usr" / "bin"
    appdir = staging / "usr" / "share" / "applications"
    debian_dir = staging / "DEBIAN"
    for d in (share, bindir, appdir, debian_dir):
        d.mkdir(parents=True, exist_ok=True)

    values = {
        "PKG": args.pkg,
        "VERSION": args.version,
        "ENTRY_PATH": "/usr/share/%s/%s" % (args.pkg, entry_rel),
        "APP_NAME": args.app_name or args.pkg,
        "MAINTAINER": args.maintainer,
        "DESCRIPTION": args.description,
        "DEPENDS": args.depends,
    }

    copy_source(src, share)

    # Vendor dependencies: keep them next to the entry file so __file__-based
    # sys.path bootstrap always resolves, even when --entry is in a subdir.
    entry_parent = (share / entry_rel).parent
    vendored = share / "third_party"
    if args.third_party:
        ext = Path(args.third_party).resolve()
        if not ext.is_dir():
            print("ERROR: --third-party is not a directory: %s" % ext, file=sys.stderr)
            return 2
        if ext != vendored:
            if vendored.exists():
                shutil.rmtree(vendored)
            copy_tree(ext, vendored)
    if entry_parent != share and vendored.is_dir():
        copy_tree(vendored, entry_parent / "third_party")

    (debian_dir / "control").write_text(render("control.tpl", values), encoding="utf-8")
    launcher = bindir / args.pkg
    launcher.write_text(render("launcher.tpl", values), encoding="utf-8")
    (appdir / (args.pkg + ".desktop")).write_text(render("desktop.tpl", values), encoding="utf-8")

    if args.icon:
        icon = Path(args.icon).resolve()
        if not icon.is_file():
            print("ERROR: --icon not found: %s" % icon, file=sys.stderr)
            return 2
        icondir = staging / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        icondir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon, icondir / (args.pkg + ".png"))

    injected = False
    if args.inject_bootstrap:
        injected = inject_bootstrap(share / entry_rel, render("bootstrap.py.tpl", values))

    # Permissions (no-op on Windows, harmless).
    for p in (launcher,):
        try:
            os.chmod(str(p), 0o755)
        except OSError:
            pass
    try:
        os.chmod(str(debian_dir / "control"), 0o644)
    except OSError:
        pass

    deb_name = "%s_%s_all.deb" % (args.pkg, args.version)
    deb_path = out / deb_name
    dpkg_deb = shutil.which("dpkg-deb")
    need_finalize = args.staging_only or dpkg_deb is None

    if need_finalize:
        print("STAGING ONLY (dpkg-deb unavailable or --staging-only).")
        print("  staging: %s" % staging)
        print("  on Linux run: dpkg-deb --build --root-owner-group %s %s"
              % (staging.name, deb_name))
    else:
        cmd = [dpkg_deb, "--build", "--root-owner-group", str(staging), str(deb_path)]
        print("RUN: %s" % " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        if result.returncode != 0:
            print(result.stderr.strip(), file=sys.stderr)
            print("ERROR: dpkg-deb failed (%s)" % result.returncode, file=sys.stderr)
            return 1
        digest = sha256(deb_path)
        (out / (deb_name + ".sha256")).write_text("%s  %s\n" % (digest, deb_name), encoding="utf-8")
        print("OK: %s (%d bytes)" % (deb_path, deb_path.stat().st_size))
        print("sha256: %s" % digest)

    report = {
        "package": args.pkg, "version": args.version, "architecture": "all",
        "entry": entry_rel, "depends": args.depends,
        "staging": str(staging), "deb": None if need_finalize else str(deb_path),
        "bootstrap_injected": injected,
        "vendored_third_party": vendored.is_dir(),
        "need_finalize_on_linux": need_finalize,
    }
    (out / "build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("report: %s" % (out / "build-report.json"))
    print("NEXT: on the UOS target run `apt install -y python3-pyqt5` before `dpkg -i`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

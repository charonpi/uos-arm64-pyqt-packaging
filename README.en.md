# uos-arm64-pyqt-packaging

[中文说明](README.md) · [Marketplace publishing guide](docs/PUBLISH.md)

A WorkBuddy Skill **and** a standalone CLI toolkit that turns PyQt / pure-Python desktop apps into `Architecture: all` `.deb` installers for **UnionTech UOS 20 arm64** (glibc 2.28, system Python 3.7).

## Why

On UOS 20 arm64, every "pip-install and bundle Qt" route fails: PyQt6 aarch64 wheels carry Qt libraries linked against `GLIBC_2.29` despite a `manylinux_2_28` tag, PySide6 requires glibc 2.31, and older PyQt6 / PyQt5 wheels have no aarch64 build at all.

The reliable route used here:

1. Migrate source from PyQt6 to PyQt5 and make it Python 3.7-safe (`from __future__ import annotations`, flat enums, `exec_()`).
2. Vendor pure-Python dependencies into `third_party/` with a `sys.path` bootstrap.
3. Build an `Architecture: all` `.deb` that contains **no binaries**.
4. Install the distro-built `python3-pyqt5` on the target with apt.

## Install

- WorkBuddy client: **Skills → Add skill → Upload skill** → pick `dist/uos-arm64-pyqt-packaging.zip`.
- Manually: copy `uos-arm64-pyqt-packaging/` into `~/.workbuddy/skills/`.
- CLI only: run the scripts in `uos-arm64-pyqt-packaging/scripts/` directly.

## Quick start

```bash
S=uos-arm64-pyqt-packaging/scripts
cp -r myapp myapp-build
python3 $S/migrate_pyqt6_to_pyqt5.py myapp-build --dry-run
python3 $S/migrate_pyqt6_to_pyqt5.py myapp-build --apply --backup
python3 $S/check_py37_compat.py myapp-build          # must be 0 ERROR
python3 -m pip install --target=myapp-build/third_party openpyxl==3.1.2
python3 $S/build_deb.py --src myapp-build --pkg myapp --version 1.0.0 \
    --entry main.py --out ./dist --inject-bootstrap
# on the UOS target:
sudo apt install -y python3-pyqt5 fonts-noto-cjk
sudo dpkg -i myapp_1.0.0_all.deb && sudo apt install -f
```

## Contents

| Path | Purpose |
|---|---|
| `uos-arm64-pyqt-packaging/SKILL.md` | Skill definition and four-phase workflow |
| `uos-arm64-pyqt-packaging/references/` | Compatibility matrix, migration guide, build/deploy, troubleshooting |
| `uos-arm64-pyqt-packaging/scripts/` | migrate / check / build / preflight / apt-source fix |
| `uos-arm64-pyqt-packaging/templates/` | control, launcher, desktop, sys.path bootstrap |
| `examples/hello-pyqt5/` | Before/after runnable sample |
| `tools/make_release.py` | Validate and build both marketplace ZIPs |
| `docs/PUBLISH.md` | Step-by-step marketplace submission (Chinese) |

## Requirements & limits

Target must be aarch64, glibc 2.28, Python 3.7, and able to `apt install python3-pyqt5`. The project must be downgradeable to PyQt5. Not for x86_64, Qt6-only APIs, or RPM-based distros.

MIT License. Author: Wang Zizheng (charonpi).

#!/bin/sh
# uos-arm64-pyqt-packaging :: target machine preflight (POSIX sh, no bashisms)
# Run ON the UOS 20 arm64 target before installing the .deb.
# Exit 0 = all hard requirements met; 1 = at least one hard requirement failed.

fail=0
pass() { printf '  [PASS] %s\n' "$1"; }
warn() { printf '  [WARN] %s\n' "$1"; }
bad()  { printf '  [FAIL] %s\n' "$1"; fail=1; }

printf '=== UOS 20 arm64 preflight ===\n'
printf 'date        : %s\n' "$(date 2>/dev/null)"
printf 'hostname    : %s\n' "$(hostname 2>/dev/null)"

printf '\n-- architecture --\n'
arch=$(uname -m 2>/dev/null)
case "$arch" in
  aarch64|arm64) pass "aarch64 ($arch)" ;;
  *)             bad  "expected aarch64, got '$arch' - x86_64 builds cannot run here" ;;
esac

printf '\n-- kernel --\n'
uname -r 2>/dev/null || warn "uname -r unavailable"

printf '\n-- glibc --\n'
glibc=$(ldd --version 2>/dev/null | head -1 | grep -o '[0-9][0-9.]*$' | head -1)
if [ -n "$glibc" ]; then
  printf '  [INFO] %s\n' "$(ldd --version 2>/dev/null | head -1)"
  case "$glibc" in
    2.28*) pass "glibc $glibc (the exact constraint this skill targets)" ;;
    2.2[0-7]*) warn "glibc $glibc is older than 2.28 - verify wheel/system packages" ;;
    2.29*|2.3*|3.*) warn "glibc $glibc is newer - the PyQt5 route still works, but other routes may now be viable" ;;
    *) warn "glibc $glibc - verify manually" ;;
  esac
else
  warn "cannot determine glibc version (ldd --version)"
fi

printf '\n-- python3 --\n'
if command -v python3 >/dev/null 2>&1; then
  pyver=$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null)
  printf '  [INFO] Python %s at %s\n' "$pyver" "$(command -v python3)"
  case "$pyver" in
    3.7.*) pass "Python 3.7.x" ;;
    3.8.*|3.9.*|3.1*) warn "Python $pyver - source must STILL be written for 3.7 compatibility" ;;
    *) warn "Python $pyver - unexpected version" ;;
  esac
else
  bad "python3 not found"
fi

printf '\n-- PyQt5 (system package) --\n'
if python3 -c 'import PyQt5.QtCore' >/dev/null 2>&1; then
  pass "PyQt5 importable ($(python3 -c 'from PyQt5.QtCore import PYQT_VERSION_STR; print(PYQT_VERSION_STR)' 2>/dev/null))"
else
  warn "PyQt5 not importable yet - run: sudo apt install -y python3-pyqt5"
fi
if command -v apt-cache >/dev/null 2>&1; then
  if apt-cache show python3-pyqt5 >/dev/null 2>&1; then
    pass "python3-pyqt5 available in apt repository"
  else
    bad  "python3-pyqt5 NOT in apt repository - external prerequisite, fix software sources first"
  fi
fi
if command -v dpkg-query >/dev/null 2>&1; then
  if dpkg-query -W -f='${Status}' python3-pyqt5 2>/dev/null | grep -q 'install ok installed'; then
    pass "python3-pyqt5 installed"
  else
    warn "python3-pyqt5 not installed yet"
  fi
fi

printf '\n-- fonts / desktop --\n'
if command -v fc-list >/dev/null 2>&1 && fc-list :lang=zh 2>/dev/null | grep -q .; then
  pass "CJK font present"
else
  warn "no CJK font detected - run: sudo apt install -y fonts-noto-cjk"
fi
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
  pass "graphical session detected"
else
  warn "no DISPLAY - Qt app cannot start in this session (SSH/headless)"
fi

printf '\n-- packaging tools --\n'
command -v dpkg-deb >/dev/null 2>&1 && pass "dpkg-deb present" || warn "dpkg-deb missing (only needed on build host)"
command -v apt     >/dev/null 2>&1 && pass "apt present"        || warn "apt missing"

printf '\n=== result: %s ===\n' "$([ "$fail" -eq 0 ] && echo 'READY' || echo 'NOT READY')"
[ "$fail" -eq 0 ] || printf 'Fix every [FAIL] before installing the .deb. See references/troubleshooting.md\n'
exit "$fail"

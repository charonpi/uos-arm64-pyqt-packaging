#!/bin/sh
# uos-arm64-pyqt-packaging :: repair Debian 10 (buster) EOL apt sources.
# Run as root ON THE BUILD HOST only. Never run on the UOS target.
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root (sudo sh $0)" >&2
  exit 1
fi

SRC=/etc/apt/sources.list
stamp=$(date +%Y%m%d%H%M%S 2>/dev/null || echo backup)
cp "$SRC" "$SRC.bak.$stamp"
echo "backup: $SRC.bak.$stamp"

# 1) EOL host -> archive.debian.org
sed -i 's|deb.debian.org|archive.debian.org|g; s|security.debian.org|archive.debian.org/debian-security|g' "$SRC"

# 2) buster-updates no longer exists on the archive -> comment it out
sed -i 's|^deb \(.*\) buster-updates |# deb \1 buster-updates |' "$SRC"

echo "--- resulting sources.list ---"
cat "$SRC"

# 3) archived Release files are expired -> disable validity check
echo "--- apt-get update (Check-Valid-Until disabled) ---"
apt-get -o Acquire::Check-Valid-Until=false update

echo "--- installing build dependencies ---"
apt-get install -y python3 python3-pip dpkg-dev fonts-noto-cjk

echo "OK. Qt runtime libraries are NOT needed: the deb is Architecture: all."

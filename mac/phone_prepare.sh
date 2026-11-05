#!/bin/bash
# Put the iOS root on the Xiaomi 17 Pro Max (popsicle), from macOS: two pinned files in Android's
# /data and nothing else. No partition, no boot image, no Android file is changed.
#
#   mac/phone_prepare.sh IMAGE [--yes]
#
#   /data/local/tmp/pinfile       the tool (tools/pinfile, static arm64)
#   /data/local/tmp/iosroot.img   16 GiB, pinned (f2fs never moves it); IMAGE written into its blocks
#   /data/local/tmp/ioslog.img    8 MiB, pinned; the kernel's console log (patch 0129)
#
# Without --yes it only checks (phone, root, free space, image) and says what it would do.
# Undo: adb shell su -c 'rm /data/local/tmp/iosroot.img /data/local/tmp/ioslog.img /data/local/tmp/pinfile'
set -euo pipefail
IMG=${1:?image} YES=${2:-}
M="$(cd "$(dirname "$0")" && pwd)"
SRC="$M/.."
P=/data/local/tmp/pinfile ROOTF=/data/local/tmp/iosroot.img LOGF=/data/local/tmp/ioslog.img
su() { adb shell "su -c '$*'" | tr -d '\r'; }

echo "== checks"
[ "$(adb shell getprop ro.product.device | tr -d '\r')" = popsicle ] || { echo "no popsicle on adb"; exit 1; }
[ "$(su id -u)" = 0 ] || { echo "no root on the phone"; exit 1; }
size=$(stat -f %z "$IMG")
[ "$size" = 17179869184 ] || { echo "image is $size bytes, want 16 GiB"; exit 1; }
[ "$(dd if="$IMG" bs=1 skip=1024 count=2 2>/dev/null)" = HX ] || { echo "image has no HFSX signature"; exit 1; }
free_kb=$(adb shell df -k /data | tail -1 | awk '{print $4}' | tr -d '\r')
echo "free on /data: $((free_kb / 1048576)) GiB"
[ "$free_kb" -gt $((20 * 1048576)) ] || { echo "need 20 GiB free on /data"; exit 1; }
for f in $ROOTF $LOGF; do
	[ -z "$(su "ls $f 2>/dev/null")" ] || { echo "$f already exists: not touching it"; exit 1; }
done
echo "would: push pinfile, create $ROOTF (16384 MiB) and $LOGF (8 MiB), pinned; write the image"
echo "       into $ROOTF's blocks; check its SHA-256 read back raw from the phone"
[ "$YES" = --yes ] || { echo "checked only; --yes does it"; exit 0; }

echo "== pinfile"
adb push "$SRC/tools/pinfile/pinfile" $P >/dev/null
su "chmod 755 $P"
want=$(shasum -a 256 "$SRC/tools/pinfile/pinfile" | cut -c1-64)
[ "$(su "sha256sum $P" | cut -c1-64)" = "$want" ] || { echo "pinfile push corrupted"; exit 1; }

echo "== files"
su "$P create $ROOTF 16384"
su "$P create $LOGF 8"
su "$P status $ROOTF"
su "$P status $LOGF"
mkdir -p "$M/extents"
su "$P extents $ROOTF --json" > "$M/extents/iosroot.json"
su "$P extents $LOGF --json" > "$M/extents/ioslog.json"
echo "extents: $(grep -o '\],' "$M/extents/iosroot.json" | wc -l | tr -d ' ') (root)"

echo "== image -> phone (16 GiB over USB, ~10-15 min)"
DEV=$(su "readlink -f /dev/block/by-name/userdata")
echo "userdata is $DEV"
# shellcheck disable=SC2002
cat "$IMG" | adb exec-in "su -c '$P rawwrite $ROOTF $DEV all --yes'"
echo "== verify (SHA-256 of the image vs the phone's raw blocks)"
mac=$(shasum -a 256 "$IMG" | cut -c1-64)
phone=$(su "$P rawhash $ROOTF $DEV" | grep -oE '[0-9a-f]{64}' | head -1)
echo "mac   $mac"; echo "phone $phone"
[ "$mac" = "$phone" ] || { echo "MISMATCH: do not boot"; exit 1; }
echo "iOS root in place"

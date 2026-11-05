#!/bin/bash
# GPU on the phone (Android, root), from macOS: steps 0 and 4 of tools/gpu_test.sh.
#
#   mac/gpu_phone.sh fetch DIR     copy the GPU firmware out of Android (read only) into DIR
#   mac/gpu_phone.sh write [--yes] put mac/out-gpu/fwpack.img into the pinned /data/local/tmp/adspfw.img
#                                  (made once, 40 MiB, like iosroot.img); without --yes only checks
#
# Undo: adb shell su -c 'rm /data/local/tmp/adspfw.img'
set -euo pipefail
M="$(cd "$(dirname "$0")" && pwd)"
P=/data/local/tmp/pinfile F=/data/local/tmp/adspfw.img
su() { adb shell "su -c '$*'" | tr -d '\r'; }
[ "$(adb shell getprop ro.product.device | tr -d '\r')" = popsicle ] || { echo "no popsicle on adb"; exit 1; }

case ${1:-} in
fetch)
	D=${2:?dir}; mkdir -p "$D"
	for f in gen80200_gmu.bin gen80200_sqe.fw gen80200_zap.mbn; do
		src=$(su "ls /vendor/firmware/$f /odm/firmware/$f 2>/dev/null" | head -1 || true)
		[ -n "$src" ] || { echo "no $f on the phone"; exit 1; }
		adb exec-out "su -c 'cat $src'" > "$D/$f"
		echo "$f <- $src ($(stat -f %z "$D/$f") bytes, $(shasum -a 256 "$D/$f" | cut -c1-16))"
	done ;;
write)
	PACK="$M/out-gpu/fwpack.img"
	[ -f "$PACK" ] || { echo "no $PACK (mac/gpu_pack.sh)"; exit 1; }
	SZ=$(stat -f %z "$PACK"); N=$(( (SZ + 4095) / 4096 )); WANT=$(shasum -a 256 "$PACK" | cut -c1-64)
	if [ -z "$(su "ls $F 2>/dev/null")" ]; then
		echo "would create $F (40 MiB, pinned)"
		[ "${2:-}" = --yes ] || { echo "checked only; --yes does it"; exit 0; }
		su "$P create $F 40"
	fi
	su "$P status $F"
	case $(su "$P status $F") in *": pinned (GC move failures 0)"*) ;; *) echo "refused: $F not pinned"; exit 1 ;; esac
	mkdir -p "$M/extents"
	su "$P extents $F --json" > "$M/extents/adspfw.json"
	DEV=$(su "readlink -f /dev/block/by-name/userdata")
	HAVE=$(su "$P rawhash $F $DEV $SZ" | grep -oE '[0-9a-f]{64}' | head -1)
	if [ "$HAVE" != "$WANT" ]; then
		echo "would write the pack ($SZ bytes, $N blocks) into $F"
		[ "${2:-}" = --yes ] || { echo "checked only; --yes does it"; exit 0; }
		adb push "$PACK" /data/local/tmp/fwpack-new.img >/dev/null
		su "$P rawwrite $F $DEV $N --yes < /data/local/tmp/fwpack-new.img; rm /data/local/tmp/fwpack-new.img" | tail -1
		HAVE=$(su "$P rawhash $F $DEV $SZ" | grep -oE '[0-9a-f]{64}' | head -1)
		[ "$HAVE" = "$WANT" ] || { echo "written pack reads back as $HAVE"; exit 4; }
	fi
	echo "pack in place ($SZ bytes, sha256 ${WANT:0:16})" ;;
*) sed -n '2,9p' "$0"; exit 2 ;;
esac

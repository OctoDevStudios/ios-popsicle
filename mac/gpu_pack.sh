#!/bin/bash
# The GPU pack for the Xiaomi 17 Pro Max (popsicle), on macOS: steps 1-3 of tools/gpu_test.sh.
# Nothing here talks to the phone.
#
#   mac/gpu_pack.sh FWDIR [CLIENTS]
#
# FWDIR: gen80200_gmu.bin, gen80200_sqe.fw, gen80200_zap.mbn copied from the phone's Android
#        (/vendor/firmware), kept outside the repo.
# CLIENTS: processes NativeAdrenoMetal gives a Metal device (default "*": all, as the 17 Pro's post29).
# Turnip/NativeAdrenoMetal: the turnip-ci release, in $W/gpu/turnip (SHA256SUMS checked).
# Out: mac/out-gpu/fwpack.img (for the 40 MiB pinned adspfw.img) and gpu.tc (trust cache of the
# signed GPU binaries, merged into the static module by build_boot.sh via EXTRA_TC).
set -euo pipefail
FWDIR=${1:?firmware dir} CLIENTS=${2:-*}
M="$(cd "$(dirname "$0")" && pwd)"
SRC="$M/.."
W=${W:-$HOME/17pm-work}
T=$W/gpu/turnip
PY=/usr/bin/python3
O="$M/out-gpu"
rm -rf "$O" && mkdir -p "$O"
(cd "$T" && shasum -a 256 -c SHA256SUMS >/dev/null) || { echo "turnip files do not match SHA256SUMS"; exit 1; }
for f in gen80200_gmu.bin gen80200_sqe.fw gen80200_zap.mbn; do
	[ -f "$FWDIR/$f" ] || { echo "no $FWDIR/$f"; exit 1; }
done

# STANDINS (environment, optional): a directory with pandora_sink (tools/sink, built for iOS and signed) and
# launchd.plist (tools/launchd_noncellular.py output): the sink stands in for daemons the kernel does not run
# (sweetsink=2: also sweetnoexec's), the plist puts the non-cellular CommCenter job back (read at the next boot).
SIGNED=("$T/vktest" "$T/libvulkan_freedreno.dylib" "$T/NativeAdrenoMetal" "$T/mtltest")
EXTRA=() EXTRAFILES=""
if [ -n "${STANDINS:-}" ]; then
	SIGNED+=("$STANDINS/pandora_sink")
	EXTRA+=("$STANDINS/pandora_sink" "$STANDINS/launchd.plist")
	EXTRAFILES="pandora_sink 755 /usr/libexec/pandora_sink
launchd.plist 644 /System/Library/xpc/launchd.plist"
fi

# AUDIO (environment, optional): a directory with this phone's amplifier firmware, crus_calr.bin, spkgraph.bin and
# rcvgraph.bin (tools/spk_graph.py from its ACDB); TUNINGS: the strips of tools/spk_tunings.py. Phone and Apple files,
# kept outside the repo. VirtualAudio comes back from HAL.disabled (sweet-root-tweaks.py moved it).
AUDIOLINES=""
if [ -n "${AUDIO:-}" ]; then
	for f in cs35l43-dsp1-spk-prot.wmfw T-cs35l43-dsp1-spk-prot.bin B-cs35l43-dsp1-spk-prot.bin \
		T-cs35l43-delta-music-spk-prot.bin B-cs35l43-delta-music-spk-prot.bin crus_calr.bin spkgraph.bin rcvgraph.bin; do
		[ -f "$AUDIO/$f" ] || { echo "no $AUDIO/$f"; exit 1; }
		EXTRA+=("$AUDIO/$f")
	done
	for t in "${TUNINGS:?TUNINGS with AUDIO}"/*.austrip; do
		b=$(basename "$t")
		EXTRA+=("$t")
		AUDIOLINES="$AUDIOLINES$b 644 /Library/Audio/Tunings/${b%%.*}/VAD/${b#*.}
"
	done
	AUDIOLINES="$AUDIOLINES> /Library/Audio/Plug-Ins/HAL.disabled/VirtualAudio.plugin /Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin
"
fi

# Trust cache: the Turnip library, the Metal plugin, the two test programs (and the sink).
$PY -I "$SRC/tools/pgputest/mktc.py" "$O/gpu.tc" "${SIGNED[@]}" | tail -2

# files.txt for the kernel's installer (bsd/dev/pandora_files.c): NAME MODE DEST, "- MODE DIR" makes a folder.
E=/System/Library/Extensions
printf '%s\n' "$CLIENTS" > "$O/NativeAdrenoMetal.clients"
$PY -I "$SRC/tools/metal/backboardd_prefs.py" "$O/com.apple.backboardd.plist"
cat > "$O/files.txt" <<EOF
vktest 755 /usr/libexec/vktest
libvulkan_freedreno.dylib 755 /usr/lib/libvulkan_freedreno.dylib
- 755 $E/NativeAdrenoMetal.bundle
NativeAdrenoMetal 755 $E/NativeAdrenoMetal.bundle/NativeAdrenoMetal
NativeAdrenoMetal.Info.plist 644 $E/NativeAdrenoMetal.bundle/Info.plist
NativeAdrenoMetal.clients 644 $E/NativeAdrenoMetal.clients
mtltest 755 /usr/libexec/mtltest
com.apple.backboardd.plist 600 /private/var/mobile/Library/Preferences/com.apple.backboardd.plist
EOF
[ -n "$EXTRAFILES" ] && printf '%s\n' "$EXTRAFILES" >> "$O/files.txt"
[ -n "$AUDIOLINES" ] && printf '%s' "$AUDIOLINES" >> "$O/files.txt"
cat "$O/files.txt"

$PY -I "$SRC/tools/mkfwpack.py" "$O/fwpack.img" \
	"$FWDIR/gen80200_gmu.bin" "$FWDIR/gen80200_sqe.fw" "$FWDIR/gen80200_zap.mbn" \
	"$T/vktest" "$T/libvulkan_freedreno.dylib" "$T/NativeAdrenoMetal" "$T/NativeAdrenoMetal.Info.plist" \
	"$O/NativeAdrenoMetal.clients" "$T/mtltest" "$O/com.apple.backboardd.plist" ${EXTRA[@]+"${EXTRA[@]}"} \
	"$O/files.txt"
SZ=$(stat -f %z "$O/fwpack.img")
echo "pack $SZ bytes, sha256 $(shasum -a 256 "$O/fwpack.img" | cut -c1-16)"
[ "$SZ" -le 41943040 ] || { echo "the pack is larger than the 40 MiB pinned file"; exit 5; }

#!/bin/bash
# Build the image `fastboot boot` starts on the Xiaomi 17 Pro Max (popsicle), on macOS:
# prelinked kernel -> ADT (with the pinned files' extents) -> payload (+ IPSW trust caches)
# -> shim/loader -> mac/out/loader-boot.img. The macOS counterpart of wsl/make_phone_payload.sh
# and shim/loader/build.sh. Nothing here talks to the phone.
#
#   mac/build_boot.sh KERNEL ROOT.json LOG.json "extra boot-args"
#
# KERNEL: kernel.development.pandora from the xnu.yml CI run (MACHINE_CONFIG PANDORA, this branch).
# ROOT.json / LOG.json: `pinfile extents --json` of /data/local/tmp/iosroot.img and ioslog.img.
# CPUS (default 8) and DEBUG (default 0x8: a panic resets the phone) pass through.
set -euo pipefail
KERNEL=${1:?kernel} ROOTJ=${2:?root extents} LOGJ=${3:?log extents} EXTRA=${4:-}
M="$(cd "$(dirname "$0")" && pwd)"
SRC="$M/.."
W=${W:-$HOME/17pm-work}
SWEET=$W/src/ios-sweet/tools
IPSW=$W/ipsw/ext
PY=/usr/bin/python3
L=/opt/homebrew/opt/llvm/bin
LLD=/opt/homebrew/opt/lld/bin/ld.lld
CPUS=${CPUS:-8} DEBUG=${DEBUG:-0x8}
O="$M/out"
rm -rf "$O" && mkdir -p "$O/tools" "$O/loader"

# 1. Apple's original AMFI, AppleImage4 and their dependencies from the iPhone X kernelcache.
$PY -I "$SRC/tools/mkprelink.py" "$KERNEL" "$IPSW/kernelcache.thin.macho" "$O/kernel-plk.macho" | tail -3

# 2. Tools side by side (mkadt_pandora, addtrustcache and mkpayload import ios-sweet's adt.py).
cp "$SWEET/adt.py" "$SWEET/mkadt.py" "$SWEET/mkpayload.py" "$SRC/tools/mkadt_pandora.py" \
	"$SRC/tools/addtrustcache.py" "$O/tools/"
# Kernel VA that maps to phys_base: below the prelinked kexts too (as make_phone_payload.sh).
perl -pi -e "s/virt_base = text\['vmaddr'\] & ~\(0x2000000 - 1\)/virt_base = min(s['vmaddr'] for s in segs) & ~(0x2000000 - 1)/" "$O/tools/mkpayload.py"
grep -q "virt_base = min(s\['vmaddr'\] for s in segs) & ~(0x2000000 - 1)" "$O/tools/mkpayload.py"

# 3. ADT for popsicle (panel 1200x2608) with the pinned files. --amp: the kernel has patch 0320 (Edge
#    scheduler, P-spill), which recommends the P cluster to every thread group; without a second cluster in
#    the ADT those threads never run (lsd and MobileGestalt deadlocked on work items no thread picked up).
#    FWJ (environment): the pinned pack file's extents (GPU firmware and files, mac/gpu_pack.sh);
#    GPUPOOL: MiB of RAM carved for the GPU buffer pool (the 17 Pro's GPU runs use 1024).
ADTX=()
[ -n "${FWJ:-}" ] && ADTX+=(--fw-extents "$FWJ")
[ -n "${GPUPOOL:-}" ] && ADTX+=(--gpu-pool "$GPUPOOL")
D22AP_ADT="$IPSW/d22ap.adt" $PY -I "$O/tools/mkadt_pandora.py" "$O/phone.adt" \
	--root-extents "$ROOTJ" --log-extents "$LOGJ" --amp ${ADTX[@]+"${ADTX[@]}"} 2>&1 | tail -4

# 4. Payload: kernel segments + ADT + boot-args, then the IPSW trust caches (OS + both cryptexes,
#    merged into the static one).
$PY -I "$O/tools/mkpayload.py" "$O/kernel-plk.macho" "$O/phone.adt" "$O/payload0.bin" \
	--cmdline "debug=$DEBUG serial=3 cpus=$CPUS keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 $EXTRA" | tail -4
TC="$IPSW/Firmware"
$PY -I "$O/tools/addtrustcache.py" "$O/payload0.bin" "$O/loader/payload.bin" \
	"$TC/087-86698-044.dmg.trustcache+$TC/087-86593-047.dmg.trustcache+$TC/087-86715-047.dmg.trustcache${EXTRA_TC:++$EXTRA_TC}" | tail -2

# The loader keeps 607 characters of boot-args: the last one must have survived.
last=${EXTRA##* }
line=$(LC_ALL=C grep -a -o "debug=0x[0-9a-f]* serial=3 cpus=[0-9] [ -~]*" "$O/loader/payload.bin" | head -1)
case "$line" in
*" $last") ;;
*) echo "boot-args too long (${#line} characters kept): '$last' was cut" >&2; exit 6 ;;
esac
echo "boot-args: $line"

# 5. Apple's boot logo from the IPSW (the loader shows it until iOS draws).
$PY -I "$SRC/tools/bootlogo.py" "$IPSW/Firmware/all_flash/applelogo@3x~iphone.im4p" "$O/loader/logo.bin" | tail -1

# 6. shim/loader with the payload embedded, packed as a boot image v4.
cd "$SRC/shim/loader"
flags=(--target=aarch64-none-elf -O2 -ffreestanding -fno-builtin -nostdlib -fno-pic
       -fno-stack-protector -mgeneral-regs-only -mstrict-align -Wall -Wextra -Werror)
"$L/clang" "${flags[@]}" -c start.S -o "$O/loader/start.o"
"$L/clang" "${flags[@]}" -DPAYLOAD="\"$O/loader/payload.bin\"" -c payload.S -o "$O/loader/payload.o"
"$L/clang" "${flags[@]}" -DLOGO="\"$O/loader/logo.bin\"" -c logo.S -o "$O/loader/logo.o"
"$L/clang" "${flags[@]}" -c loader.c -o "$O/loader/loader.o"
if "$L/llvm-readelf" -r "$O/loader/loader.o" | grep -q R_AARCH64_ABS; then
	echo "absolute relocation in loader.c" >&2; exit 1
fi
"$LLD" -T loader.ld --build-id=none "$O/loader/start.o" "$O/loader/loader.o" "$O/loader/logo.o" \
	"$O/loader/payload.o" -o "$O/loader/loader.elf"
"$L/llvm-objcopy" -O binary "$O/loader/loader.elf" "$O/loader/Image"
$PY -I - "$O/loader/Image" "$O/loader/payload.bin" <<'PY'
import struct, sys
img = open(sys.argv[1], 'rb').read(); pl = open(sys.argv[2], 'rb').read()
size = struct.unpack_from('<Q', img, 16)[0]
assert img[0x38:0x3c] == b'ARM\x64', 'no arm64 Image magic'
assert size == len(img), (hex(size), hex(len(img)))
off = img.find(pl[:64])
assert off > 0 and off % 4096 == 0 and img[off:off + len(pl)] == pl, 'payload not embedded'
print('Image %d bytes, payload at 0x%x (%d bytes)' % (len(img), off, len(pl)))
PY
$PY -I "$SRC/tools/mkbootimg_v4.py" "$O/loader/Image" "$O/loader-boot.img"
shasum -a 256 "$O/loader-boot.img"

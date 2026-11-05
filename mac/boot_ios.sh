#!/bin/bash
# Start iOS on the Xiaomi 17 Pro Max (popsicle) from macOS, in RAM only (`fastboot boot`):
# the macOS counterpart of tools/boot_ios.sh + tools/ios_test.sh. Writes nothing to the phone;
# the iOS kernel itself writes only inside iosroot.img and ioslog.img (ufsrw=1, patch 0088/0129).
#
#   mac/boot_ios.sh KERNEL SECONDS ["extra boot-args"] [--dry-run]
#
# SECONDS: pandora_reboot_after, the kernel restarts the phone (back to Android) after that long.
# Any time: hold Power + Volume down ~10 s to force the restart.
set -euo pipefail
KERNEL=${1:?kernel} SECS=${2:?seconds} EXTRA=${3:-} DRY=${4:-}
M="$(cd "$(dirname "$0")" && pwd)"
P=/data/local/tmp/pinfile ROOTF=/data/local/tmp/iosroot.img LOGF=/data/local/tmp/ioslog.img
su() { adb shell "su -c '$*'" | tr -d '\r'; }

echo "== 1. phone (Android)"
[ "$(adb shell getprop ro.product.device | tr -d '\r')" = popsicle ] || { echo "no popsicle on adb"; exit 1; }
for f in $ROOTF $LOGF; do
	st=$(su "$P status $f"); echo "$st"
	case $st in *": pinned (GC move failures 0)"*) ;; *) echo "refused: $f not pinned"; exit 1 ;; esac
done
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
su "$P extents $ROOTF --json" > "$T/iosroot.json"
su "$P extents $LOGF --json" > "$T/ioslog.json"
cmp -s "$T/iosroot.json" "$M/extents/iosroot.json" || { echo "refused: iosroot.img moved since phone_prepare.sh"; exit 1; }
cmp -s "$T/ioslog.json" "$M/extents/ioslog.json" || { echo "refused: ioslog.img moved since phone_prepare.sh"; exit 1; }
DEV=$(su "readlink -f /dev/block/by-name/userdata")
off=$(/usr/bin/python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['extents'][0][1])" "$T/iosroot.json")
sig=$(su "dd if=$DEV bs=4096 skip=$((off / 4096)) count=1 2>/dev/null | dd bs=1 skip=1024 count=2 2>/dev/null")
[ "$sig" = HX ] || { echo "refused: no HFSX signature at the root's first block (got '$sig')"; exit 1; }
echo "root file: pinned, unmoved, HFSX"
args=""
read -r rtc now <<< "$(su "cat /sys/class/rtc/rtc0/since_epoch; date +%s" | tr '\n' ' ')"
case "$rtc$now" in *[!0-9]* | "") ;; *) args="$args pandora_rtc_offset=$((now - rtc))" ;; esac
slot=$(adb shell getprop ro.boot.slot_suffix | tr -d '\r_')
case "$slot" in a | b) args="$args pandora_slot=$slot" ;; esac

# GPU=1 (environment): the pinned GPU pack (mac/gpu_pack.sh + mac/gpu_phone.sh write), 1 GiB GPU pool,
# the GPU trust cache and pandora_gpu=15 (the 17 Pro's gpu_test.sh level).
GPUARGS=""
if [ "${GPU:-0}" = 1 ]; then
	FWF=/data/local/tmp/adspfw.img
	case $(su "$P status $FWF") in *": pinned (GC move failures 0)"*) ;; *) echo "refused: $FWF not pinned"; exit 1 ;; esac
	su "$P extents $FWF --json" > "$T/adspfw.json"
	cmp -s "$T/adspfw.json" "$M/extents/adspfw.json" || { echo "refused: adspfw.img moved since gpu_phone.sh"; exit 1; }
	export FWJ="$T/adspfw.json" GPUPOOL=1024 EXTRA_TC="$M/out-gpu/gpu.tc"
	# The 17 Pro's last run (HANDOFF.md, post31): Metal frames scanned out directly (pandora_gpu_metal), CPU
	# governor, board thermal limits (0333 ignores this board's open thermistors), gauge and battery, the sink for
	# stopped daemons. Audio (pandora_adsp, pandora_audio, amplifier firmware) is not set up here yet.
	GPUARGS="pandora_gpu=15 pandora_gpu_metal=1 pandora_cpu=2 pandora_therm=2 pandora_gauge=3 pandora_battery=1 sweetsink=2 pandora_therm_relax=13 pandora_gpu_min_mhz=578"
	HZ=60
	# AUDIO=1 (environment): the speakers (docs/AUDIO_SPEAKER.md; the pack needs AUDIO= and TUNINGS= in gpu_pack.sh).
	# pandora_spk_live must stay with pandora_spk, or the kernel plays its 18 s test tone.
	[ "${AUDIO:-0}" = 1 ] && GPUARGS="$GPUARGS pandora_adsp=2 pandora_audio=1 pandora_amp=3 pandora_spk=3 pandora_spk_live=1"
	# WIFI=1 (environment): the PCIe bring-up of the Wi-Fi chip, 35 s after boot (bsd/dev/pandora_wlan.c).
	[ "${WIFI:-0}" != 0 ] && GPUARGS="$GPUARGS pandora_wlan=${WIFI}"
	# MODEM=1 (environment): the modem's start, 60 s after boot, read only firmware partition (0347).
	[ "${MODEM:-0}" = 1 ] && GPUARGS="$GPUARGS pandora_mss=1"
	echo "GPU: pack pinned, pool 1024 MiB"
fi

echo "== 2. build"
# First-boot set (tools/ios_test.sh BASE): root and log writable inside their files only,
# CPU rendering, no GPU/audio/governor (their boot-args are off by default).
BASE="ufsrw=1 rootrw=1 ${SIMARG-unentitled_ios_sim_launch=1 }ignition_level=1 wdt_test=no_user_checkin launchd_unsecure_cache=1 wdt=-1 sweetfb_hz=${HZ:-30} sweetfb_fill=1 sweetnoexec=bluetoothd,fairplayd.H2"
bash "$M/build_boot.sh" "$KERNEL" "$T/iosroot.json" "$T/ioslog.json" "$BASE $GPUARGS $EXTRA pandora_reboot_after=$SECS$args"
[ "$DRY" = --dry-run ] && { echo "dry run: not booting"; exit 0; }

echo "== 3. fastboot boot (RAM only)"
adb reboot bootloader
seen=0
for _ in $(seq 1 30); do sleep 2; fastboot devices | grep -q fastboot && { seen=1; break; }; done
[ $seen = 1 ] || { echo "no fastboot device after 60 s: not booted"; exit 1; }
[ "$(fastboot getvar product 2>&1 | sed -n 's/^product: //p' | tr -d '\r')" = popsicle ] || { echo "fastboot device is not popsicle"; exit 1; }
fastboot boot "$M/out/loader-boot.img"
echo "booted at $(date +%H:%M:%S); back to Android after ${SECS}s (or hold Power + Volume down)"

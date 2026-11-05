#!/bin/bash
# autopilot: AUTO.sh RUNDIR NAME ID: wait for the kernel, boot 120 s in RAM, wait for Android, fetch the log.
K=$1
RUN=$1; NAME=$2; id=$3; R=OctoDevStudios/popsicle-ios
s=$(adb devices -l | awk '/device:popsicle/{print $1; exit}'); [ -n "$s" ] || { echo "KERNEL READY, PHONE NOT ON ADB"; exit 2; }
export ANDROID_SERIAL=$s; cd ~/17pm-work/src/popsicle-ios && GPU=1 AUDIO=1 WIFI=${WIFI_MODE:-2} MODEM=1 STANDINS=$HOME/17pm-work/standins bash mac/boot_ios.sh "$K" ${SECS:-90} "${LIVE_ARGS-pandora_usb=2 qcom-usb-debug=1}" </dev/null > $HOME/17pm-work/boot_$NAME.out 2>&1; tail -1 $HOME/17pm-work/boot_$NAME.out | cut -c1-160; grep -q '^booted at' $HOME/17pm-work/boot_$NAME.out || { echo "BOOT REFUSED, phone still on Android"; tail -4 $HOME/17pm-work/boot_$NAME.out | cut -c1-200; exit 4; }
# the live console over USB: read as long as the port exists
ARGS=(); IFS=$'\n'; for u in ${UNTIL:-}; do ARGS+=(--until "$u"); done; unset IFS
/usr/bin/python3 -I ~/17pm-work/src/popsicle-ios/mac/live.py ~/17pm-work/src/popsicle-ios/mac/logs/$NAME.live "${ARGS[@]}" --grace ${GRACE:-3} --wait 240 >&2 &
LIVE=$!
sleep 45; end=$((SECONDS+600)); ok=0; while [ $SECONDS -lt $end ]; do s=$(adb devices -l | awk '/device:popsicle/{print $1; exit}'); if [ -n "$s" ] && [ "$(adb -s "$s" shell -n getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; then ok=1; break; fi; sleep 5; done
[ $ok = 1 ] || { echo "PHONE NOT BACK ON ANDROID after 10 min"; exit 3; }
kill $LIVE 2>/dev/null; ls -la ~/17pm-work/src/popsicle-ios/mac/logs/$NAME.live 2>&1 | cut -c25-; echo "back at $(date +%H:%M:%S)"; export ANDROID_SERIAL=$s; cd ~/17pm-work/src/popsicle-ios; bash mac/fetch_log.sh $NAME </dev/null 2>&1 | tail -1 | cut -c1-90; wc -l mac/logs/$NAME.txt
L=mac/logs/$NAME.txt; grep -n 'PANDORA WLAN' $L | grep -E 'capability|MMIO|READY \+|MSI|BHI image|READY|M0 |SBL|BHIe|\+[0-9]+ s|at the end|SYSERR|IPCR|QRTR|event:|firmware step' | cut -c1-210 | head -70; grep -n 'PANDORA MODEM' $L | grep -E 'not ready|crash|TFTP|READY \+|memshare|file service: (read|write|open)|at [0-9]+ s slave' | cut -c1-170 | head -60; grep -n 'PANDORA NW' $L | cut -c1-200 | head -110; grep -n -i 'panic\b\|data abort\|SError' $L | grep -v DumpPanic | head -4 | cut -c1-180; tail -1 $L | cut -c1-100

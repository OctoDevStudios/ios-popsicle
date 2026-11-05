#!/bin/bash
# Read the iOS kernel's console log back from the phone (in Android) and decode it.
#   mac/fetch_log.sh NAME   -> mac/logs/NAME.txt
set -euo pipefail
NAME=${1:?name}
M="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$M/logs"
adb exec-out "su -c '/data/local/tmp/pinfile rawread /data/local/tmp/ioslog.img \$(readlink -f /dev/block/by-name/userdata) 2>/dev/null'" > "$M/logs/$NAME.raw"
/usr/bin/python3 -I "$M/../tools/pandora_log.py" "$M/logs/$NAME.raw" "$M/logs/$NAME.txt"
rm -f "$M/logs/$NAME.raw"
tail -40 "$M/logs/$NAME.txt"

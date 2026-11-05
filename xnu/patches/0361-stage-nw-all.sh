#!/bin/bash
# The Ath12kWifi module (tools/wlan/, built on the Mac with xnu/vendor/nw_all.o as result) in the kernel's link.
set -euo pipefail
[[ "${MACHINE_CONFIG:-}" == SWEET ]] || exit 0
cp "$GITHUB_WORKSPACE/xnu/vendor/nw_all.o" bsd/dev/nw_all.o
printf '\nLD_KERNEL_LIBS += $(SRCROOT)/bsd/dev/nw_all.o\n' >> makedefs/MakeInc.def
echo "Ath12kWifi object staged"

# Building

Requirements: a Xiaomi 17 Pro Max with an unlocked bootloader and root under Android, a Mac with `adb` and `fastboot`, and your own iPhone X iOS 16.7.16 IPSW. None of Apple's, Qualcomm's or Xiaomi's files are distributed here.

## 1. Kernel

Run `.github/workflows/xnu.yml` on your fork with `machine_config=PANDORA`. It builds xnu-8796 with `xnu/patches/` applied in order and needs `xnu/vendor/nw_all.o` (step 2) for the Wi-Fi driver. Its artifacts `xnu-kernel`, `xnu-objects` and `xnu-buildtree` allow local relinks.

## 2. Wi-Fi driver

The driver is [Ath12kWifi](https://github.com/UniXNU/Ath12kWifi) (Linux ath12k, mac80211, cfg80211, MHI and QRTR on XNU), adapted for the WCN7880 "peach" chip:

1. Prepare the Ath12kWifi tree and apply `tools/wlan/ath12kwifi-local.diff`.
2. Copy the `peach` firmware directory from your phone (`/vendor/firmware_mnt/image/peach/`). This stays on your machine.
3. Run `tools/wlan/peach.py`, then `tools/wlan/peach2.py`. Paths at the top of these scripts assume `~/17pm-work`.
4. Run `tools/wlan/build_nw.py`, link the objects with `ld -r`, and copy the result to `xnu/vendor/nw_all.o`.

To replace only the driver in an existing kernel, without rebuilding xnu: `mac/relink_kernel.py`.

## 3. Prepare the phone (Android)

`mac/phone_prepare.sh` creates the pinned files that hold the iOS root and the log, and records where they are on storage. `tools/pinfile` is the helper that runs on the phone. `mac/gpu_pack.sh` and `mac/gpu_phone.sh` build and install the GPU pack.

## 4. Boot (RAM only)

```bash
GPU=1 AUDIO=1 WIFI=2 MODEM=1 bash mac/boot_ios.sh KERNEL SECONDS "pandora_usb=2 qcom-usb-debug=1"
```

The kernel is loaded with `fastboot boot`, then the phone returns to Android after `SECONDS`. Hold Power + Volume Down for 10 seconds to force a restart.

`mac/live.py` reads the kernel log over USB and can order the restart when a log line appears. `mac/test_kernel.sh` and `mac/wifi_cycle.sh` chain all of this for tests, and `mac/log_summary.sh` summarises a run.

The boot line is limited to 607 characters.

<div align="center">

# iOS on the Xiaomi 17 Pro Max

**iOS 16.7.16 running natively on Snapdragon 8 Elite Gen 5 hardware, booted from RAM.**

![Device](https://img.shields.io/badge/device-popsicle-111111?style=for-the-badge)
![SoC](https://img.shields.io/badge/SoC-SM8850-3253DC?style=for-the-badge)
![Kernel](https://img.shields.io/badge/kernel-xnu--8796-555555?style=for-the-badge)
![Status](https://img.shields.io/badge/status-experimental-E5A00D?style=for-the-badge)

</div>

> [!WARNING]
> Research project, not a daily driver. You can lose data or damage your phone, and you are responsible for what you run. Back up everything first.

## What this is

A self-built XNU kernel with native drivers for the Xiaomi 17 Pro Max, running the unmodified userland of an iPhone X. There is no emulator and no virtual machine: iOS talks to the hardware through drivers compiled into the kernel.

Normal testing writes nothing to the phone's partitions. The kernel starts with `fastboot boot`, lives in RAM, and a restart returns to Android.

## Status

Percentages are the author's estimates of how far each part is from working as it does under Android. They are not measurements.

**Legend:** 🟢 works · 🟡 partly works · 🟠 in progress · ⚪ not started

### System

| Component | Progress | Status | Notes |
|---|---|---|---|
| Boot, lock screen, home screen, built-in apps | `████████░░` 80% | 🟢 | Slow boot, occasional UI freezes |
| Touch, power and volume buttons, brightness | `█████████░` 90% | 🟢 | |
| Display and GPU (Adreno 840, Metal) | `███████░░░` 70% | 🟡 | Whole UI composited by the GPU. Known glitches: text, pink Reachability, clipped icons |
| CPU (8 cores, frequency scaling, idle) | `████████░░` 85% | 🟢 | |
| Battery gauge and charging | `███████░░░` 70% | 🟡 | Real gauge values, power saving barely started |
| Thermal management | `█████░░░░░` 50% | 🟡 | Chip sensors only, no skin temperature model |
| App Store apps | `█░░░░░░░░░` 10% | 🟡 | Most do not open: they rely on Apple's hardware security |

### Connectivity

| Component | Progress | Status | Notes |
|---|---|---|---|
| Wi-Fi: chip and firmware (WCN7880) | `██████░░░░` 60% | 🟠 | Firmware boots, but crashes on about two boots out of three |
| Wi-Fi: scan | `████░░░░░░` 40% | 🟠 | Real networks seen on 2.4, 5 and 6 GHz, not yet reliable |
| Wi-Fi: connection and data | `░░░░░░░░░░` 0% | ⚪ | wpa_supplicant not connected yet |
| Wi-Fi: Settings panel and status icon | `░░░░░░░░░░` 0% | ⚪ | |
| Modem firmware | `███████░░░` 70% | 🟡 | Boots fully with its services, all writes kept in RAM |
| 4G/5G, calls, SMS, SIM | `░░░░░░░░░░` 0% | ⚪ | Not connected to iOS yet |
| Bluetooth | `░░░░░░░░░░` 0% | ⚪ | |
| USB | `██░░░░░░░░` 20% | 🟠 | Live kernel log and remote restart. No data or networking yet |
| NFC, GPS | `░░░░░░░░░░` 0% | ⚪ | |

### Media and sensors

| Component | Progress | Status | Notes |
|---|---|---|---|
| Speakers | `███████░░░` 75% | 🟢 | Plays sound through the ADSP and CS35L43 amplifiers, one crash seen under load |
| Microphones, earpiece | `░░░░░░░░░░` 0% | ⚪ | |
| Vibration motor | `░░░░░░░░░░` 0% | ⚪ | |
| Cameras | `░░░░░░░░░░` 0% | ⚪ | Hardest part: iOS expects Apple's ISP |
| Motion and light sensors | `░░░░░░░░░░` 0% | ⚪ | |
| Fingerprint reader | `░░░░░░░░░░` 0% | ⚪ | |
| Rear display | `░░░░░░░░░░` 0% | ⚪ | |

## Getting started

Nothing here is a ready-to-flash image. You build the kernel and the root filesystem yourself, from your own files. See **[BUILDING.md](BUILDING.md)**.

You need a Xiaomi 17 Pro Max with an unlocked bootloader and root, a Mac, and your own IPSW for the iPhone X.

## What's in the repo

| Path | Contents |
|---|---|
| `xnu/patches/` | Patches for xnu-8796, applied in order |
| `wsl/` | Drivers compiled into the kernel: GPU, display, touch, audio, storage, battery and more |
| `mac/` | Boot, live log, relink and test tools for macOS |
| `tools/` | Boot image, device tree, trust cache and firmware tools, GPU tests, Wi-Fi driver adaptation |
| `shim/` | The small loader started by `fastboot boot` |
| `bootmgr/` | Optional boot menu. **It writes to the `boot_b` partition**, read its README first |
| `docs/`, `device/` | Technical notes (in Chinese and English) |

## Not included

- Apple's iOS system files (IPSW, shared cache, SDK)
- Qualcomm and Xiaomi firmware
- Partition backups, logs and anything else read from a phone

Firmware is read from your own phone at run time, and modem writes never leave RAM.

## Credits

Built on the work of others:

- **[Data A Live](https://github.com/ShueiTsuki/data-a-live)** by ShueiTsuki: the Xiaomi 17 Pro port this project continues. Kernel drivers, GPU work and most of the tooling come from it.
- **[ios-sweet](https://github.com/dipa-studio/ios-sweet)** and **[ios-fuxi](https://github.com/bangprovn/ios-fuxi)**: the approach and the early kernel patches.
- **[UniXNU](https://github.com/UniXNU/UniXNU)**: 4K-page kernel, storage driver, NativeAdreno, NativeMetal, ArmSmmu4K, Ath12kWifi and Qualcomm components.
- **[Mesa](https://gitlab.freedesktop.org/mesa/mesa)** (Turnip) and **[metal2vulkan](https://github.com/steelbrain/metal2vulkan)**.
- The Linux kernel's Qualcomm drivers, including ath12k.

## License

Kernel patches and kernel drivers: APSL 2.0. Other code and documentation: MIT. Third-party files keep their own licenses. Full terms in [LICENSE](LICENSE).

Not affiliated with Apple, Xiaomi or Qualcomm. All trademarks belong to their owners.

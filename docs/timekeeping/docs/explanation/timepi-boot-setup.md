# timepi's boot setup

timepi boots from its SD card and runs from its NVMe drive. The firmware, kernel and `config.txt` come from the SD card's boot partition; the kernel then mounts the root filesystem from the NVMe. It looks odd, and it's the only arrangement that has worked with this drive.

```text
EEPROM  BOOT_ORDER=0xf1      SD card only (then retry)
SD p1   5c8ad903-01  bootfs  /boot/firmware: config.txt, cmdline.txt -> root=PARTUUID=2ec0a0c9-02
                             tryboot.txt (+ cmdline=cmdline-sd.txt), cmdline-sd.txt -> root=PARTUUID=5c8ad903-02
SD p2   5c8ad903-02  rootfs  fallback root, frozen at 2026-11-19
NVMe p1 2ec0a0c9-01  bootfs  unused
NVMe p2 2ec0a0c9-02  rootfs  /  (live)
```

## Why the NVMe at all

SD card wear. timepi writes logs, ntpsec's drift file and metrics textfiles every 30 s, around the clock, and it's the one machine the whole LAN takes its time from. On 2026-11-19 its 238.5 GB NVMe got a full copy of the SD system (rsync), with fstab and `cmdline.txt` pointing at the NVMe.

## What went wrong on 2026-11-19

The first attempt did it the usual way: the Pi 5's adapter has no HAT+ EEPROM, so the bootloader got updated (May 2025 to the Sep 2026 release) and set to `BOOT_ORDER=0xf416` with `PCIE_PROBE=1`, NVMe first. The bootloader loaded the kernel from the NVMe without trouble. Then the kernel hung on `nvme 0001:01:00.0: enabling device` (controller `17aa:0005`, a Lenovo drive), on warm and cold boots alike, and after ~100 s waited forever for its root filesystem. timepi, the only stratum 1 and PTP grandmaster, was down.

Booting with the NVMe disconnected got it back, and the EEPROM went back to `BOOT_ORDER=0xf461` without `PCIE_PROBE`.

The telling detail came from the day before: with the SD card booting and the kernel the first to touch the drive, the NVMe had worked as a data disk for over a day. Only an NVMe the bootloader never initialised comes up under this kernel.

## The arrangement since

The same evening, with the owner's approval, timepi moved to what it runs now:

- EEPROM `BOOT_ORDER=0xf1`: SD only. The bootloader never touches PCIe.
- The SD card's `cmdline.txt` has `root=PARTUUID=2ec0a0c9-02`, so the kernel brings up the NVMe itself (about 7 s on a clean start) and mounts it as `/`.
- The NVMe's fstab mounts `/boot/firmware` from the SD card (`5c8ad903-01`), so kernel and firmware updates land where the bootloader reads them.
- The fallback stays: `tryboot.txt` is `config.txt` plus `cmdline=cmdline-sd.txt`, and `cmdline-sd.txt` points at the SD's own root. `reboot '0 tryboot'` boots it once. It was tested that way before the NVMe root became the default.

Buckle's `pi-firmware` only adds and removes individual tokens in `cmdline.txt` (cgroups, NVMe power states, no serial console) and never touches `root=`, so it can't undo this. It doesn't manage `tryboot.txt` or `cmdline-sd.txt` either: they're hand-made, and a later change to `config.txt` doesn't reach `tryboot.txt` by itself. On 2026-11-26 the two still differed only by the `cmdline=` line.

## The rule that follows

Never NVMe-first boot or `PCIE_PROBE` on timepi with this drive. If timepi ever has to boot without the NVMe, it does so from the SD root, which is a snapshot of 2026-11-19; see [Recover timepi when it doesn't boot](../how-to/recover-timepi-when-it-doesnt-boot.md).

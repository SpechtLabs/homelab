# Recover timepi when it doesn't boot

Use this when timepi doesn't come back after a reboot or power loss, or you suspect its NVMe drive, and you want it running again from the SD card's own root filesystem.

**Before you start:** know the layout (details in [timepi's boot setup](../explanation/timepi-boot-setup.md)):

| | SD card | NVMe |
|---|---------|------|
| Boot files (`/boot/firmware`) | `mmcblk0p1`, PARTUUID `5c8ad903-01`: **used** | `nvme0n1p1`, `2ec0a0c9-01`: unused copy |
| Root filesystem | `mmcblk0p2`, `5c8ad903-02`: fallback, frozen at 2026-11-19 | `nvme0n1p2`, `2ec0a0c9-02`: **live** |

The bootloader reads only the SD card (`BOOT_ORDER=0xf1`). `cmdline.txt` on the SD card points the kernel at the NVMe root. `cmdline-sd.txt` next to it points at the SD root instead, and `tryboot.txt` is `config.txt` plus `cmdline=cmdline-sd.txt`.

While timepi is down, the LAN keeps time: NTP clients fall back to the public pool, and PTP clients' chrony falls back to it too once ptp4l loses the grandmaster.

!!! danger "Never boot timepi from the NVMe"
    Don't set an NVMe-first `BOOT_ORDER` or `PCIE_PROBE=1` in the EEPROM, whatever a guide on the internet says. With this drive (Lenovo, controller `17aa:0005`) the kernel hangs on `nvme 0001:01:00.0: enabling device` whenever the bootloader touched the drive first. That's how timepi went down on 2026-11-19.

## If timepi still boots: try the SD root once (tryboot)

Use this to test the fallback, or to get off a misbehaving NVMe root without touching the card.

1. Log in and reboot into the tryboot configuration. This boots the SD root **once**; the next reboot goes back to the NVMe root.

   ```sh
   ssh cedi@timepi
   sudo reboot '0 tryboot'
   ```

2. Once it's back, check which root it's on:

   ```sh
   findmnt -n -o SOURCE /
   ```

   `/dev/mmcblk0p2` is the SD root. (`/dev/nvme0n1p2` means tryboot didn't take.)
3. To return to the NVMe root, reboot normally: `sudo reboot`.

## If timepi doesn't boot: switch the card to the SD root

1. Power timepi off (unplug it) and take out the SD card.
2. Put the card in the Mac. Its boot partition mounts as `bootfs` (the root partition is ext4 and won't mount; you don't need it).
3. Keep the NVMe command line and switch to the SD one:

   ```sh
   cd /Volumes/bootfs
   cp cmdline.txt cmdline-nvme.txt
   cp cmdline-sd.txt cmdline.txt
   grep -o 'root=[^ ]*' cmdline.txt
   ```

   You should see `root=PARTUUID=5c8ad903-02`.
4. Eject the card (`diskutil eject /Volumes/bootfs`), put it back and power timepi on. If you suspect the NVMe itself, disconnect it first; the SD root doesn't need it.
5. Check, as above, that `findmnt -n -o SOURCE /` says `/dev/mmcblk0p2`.

!!! warning "The SD root is old"
    Its packages and files are as of 2026-11-19. ntpsec, gpsd and ptp4l were set up by then, but the Buckle agent and everything changed since are older. Buckle brings the configuration up to date on the agent's next drift pass or rollout; packages follow with the nightly upgrades. Watch the first run on the Buckle UI.

## Check it worked

```sh
ntpq -pn
sudo pmc -u -b 0 'GET PORT_DATA_SET'
```

`*SHM(1) .PPS.` (or `*` on a PTB server while the GPS gets its fix) and `portState MASTER`. On a client, `sudo chronyc -n sources` shows `^* 192.168.0.109` or `#* PTP` again within a minute or two.

## Going back to the NVMe root

When the NVMe works again: put `cmdline-nvme.txt` back as `cmdline.txt` (the root token must read `root=PARTUUID=2ec0a0c9-02`), reconnect the drive and boot. Everything written while on the SD root stays on the SD root; nothing syncs it to the NVMe.

!!! warning "Unverified"
    Not tested: whether the SD root's state (Buckle agent identity, ntpsec drift file) causes trouble after switching back to the NVMe. The 2026-11-19 recovery went the other way.

## If it didn't

- No boot from the SD root either: the boot files on `mmcblk0p1` or the card are the problem. Connect HDMI and watch where it stops; the Pi 5's bootloader shows its diagnostics screen there.
- It boots but has no time: [Handle a GPS without a fix](handle-a-gps-without-a-fix.md) and `systemctl status ntpsec gpsd ptp4l@eth0 phc2sys-eth0 --no-pager`.

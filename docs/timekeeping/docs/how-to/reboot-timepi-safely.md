# Reboot timepi safely

Use this when you have to reboot timepi by hand (a kernel update outside the nightly run, a firmware change, a hung daemon). timepi is the LAN's only stratum 1 and PTP grandmaster, so a reboot costs every host its best source for a few minutes.

**Before you start:** decide it's worth it. Buckle reboots timepi on its own where a module needs it (`pi-firmware`'s reboot handler, and [`schedules/nightly-kernel-reboots.yaml`](https://github.com/SpechtLabs/homelab/blob/main/schedules/nightly-kernel-reboots.yaml) at 05:30 for a pending kernel), so most of the time you don't have to. SSH to `cedi@timepi`.

During the reboot the NTP clients and the PTP clients' chrony fall back to `2.debian.pool.ntp.org`, a few ms off instead of ns to µs. The first alert, `timepi — time metrics missing`, comes after 15 minutes without metrics.

1. Note the state before:

   ```sh
   ntpq -pn
   findmnt -n -o SOURCE /
   ```

   `/dev/nvme0n1p2` is the normal root.
2. Reboot:

   ```sh
   sudo reboot
   ```

3. Wait for SSH to come back. The kernel takes about 7 s to bring up the NVMe on a clean start, so allow a minute or two.

## Check it worked

```sh
findmnt -n -o SOURCE /
systemctl is-active gpsd ntpsec ptp4l@eth0 phc2sys-eth0
ntpq -pn
sudo pmc -u -b 0 'GET PORT_DATA_SET'
```

Root on `/dev/nvme0n1p2`, four times `active`, `*SHM(1) .PPS.` once the GPS has a fix (it can take a few minutes after a cold start; meanwhile `*` on a PTB server is fine) and `portState MASTER`. Then on one PTP and one NTP client, `sudo chronyc -n sources` should show `#* PTP` and `^* 192.168.0.109`.

## If it didn't

- No SSH after 5 minutes: [Recover timepi when it doesn't boot](recover-timepi-when-it-doesnt-boot.md).
- ptp4l `FAULTY` or not running: `sudo systemctl restart ptp4l@eth0`. Its drop-in waits for eth0's link first, because a ptp4l started before the link stays FAULTY.

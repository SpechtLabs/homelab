# Configuration

Change any of this in the repo and let Buckle roll it out; files on the hosts carry a "Managed by Buckle" header and get overwritten.

## Vars

| Var | Value | Set in | Used by |
|-----|-------|--------|---------|
| `ntp_server` | `192.168.0.109` | [`vars/defaults.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/defaults.yaml) | chrony, `ptp-facts` (the route test) |
| `ntp_pool` | `2.debian.pool.ntp.org` | `vars/defaults.yaml` | chrony's fallback |
| `time_tai_utc_offset` | `37` | `vars/defaults.yaml` | chrony's PHC `offset`, the grandmaster's `currentUtcOffset` |
| `o11y_textfile_dir` | `/var/lib/prometheus/node-exporter` | `vars/defaults.yaml` | both metrics scripts; empty turns them off |
| `rpi_gps_pps` | `true` on timepi (default `false`) | [`vars/host-timepi.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/host-timepi.yaml) | `pi-firmware`: the GPS/PPS `config.txt` lines |
| `rpi_sd_fallback_root` | `PARTUUID=5c8ad903-02` on timepi (default empty: off) | `vars/host-timepi.yaml` | `pi-firmware`: `tryboot.txt`, `cmdline-sd.txt`, the `sd-boot-only` check |
| `rpi_pps_gpio` | `18` | [`modules/pi-firmware`](https://github.com/SpechtLabs/homelab/blob/main/modules/pi-firmware/module.yaml) | the `pps-gpio` overlay's pin |
| `ptp_enabled` | `true` | [`modules/ptp-server`](https://github.com/SpechtLabs/homelab/blob/main/modules/ptp-server/module.yaml) | ptp4l, phc2sys, `ptp-gm-quality` on timepi |
| `ptp_interface` | `eth0` | `modules/ptp-server` | the grandmaster's port |
| `ptp_gps_device` / `ptp_pps_device` | `/dev/ttyAMA0` / `/dev/pps0` | `modules/ptp-server` | gpsd, `ubxtool`, `time-metrics` |
| `ptp_gpsd_options` | `-n` (no `-s`: gpsd detects the 9600 baud) | `modules/ptp-server` | `/etc/default/gpsd` |
| `ptp_gps_protver` | `18` | `modules/ptp-server` | `ubxtool -P` |
| `ntp_gps_offset` | `0.600` | `modules/ptp-server` | `fudge` for the NMEA refclock |

## Groups

From [`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml):

| Group | Expression | Module |
|-------|-----------|--------|
| `ptp-grandmaster` | `host.facts.script.rpi.pps_gpio == true` (a `pps-gpio` node in the device tree, from `pi-facts`) | `ptp-server` |
| `ntp-client` | `host.facts.script.ptp.lan == true` | `time-sync` |
| `ptp-client` | `... lan == true && host.facts.script.ptp.hardware == true` | `time-sync`'s PTP tasks |

`ptp-facts` runs on every host in `debian`. timepi is in the `core` rollout phase with isa, the NUC and jumphost, two at a time.

## Files and units on timepi

| Path / unit | What |
|-------------|------|
| `/etc/default/gpsd` | `DEVICES="/dev/ttyAMA0 /dev/pps0"` |
| `/etc/ntpsec/ntp.conf` | sources and restrictions |
| `/etc/linuxptp/ptp4l.conf` | grandmaster config (logs to syslog) |
| `ptp4l@eth0.service` + Buckle drop-in | waits for eth0's link; `ExecStartPost` sets the grandmaster settings |
| `/etc/systemd/system/phc2sys-eth0.service` | `phc2sys -w -c eth0 -s CLOCK_REALTIME` |
| `ptp-gm-quality.timer` (15 s) | `/usr/local/sbin/ptp-gm-quality 37` |
| `time-metrics.timer` (30 s) | `/usr/local/sbin/time-metrics --dir ... --pps-device /dev/pps0 --ptp-interface eth0` |
| `/boot/firmware/config.txt` | `dtoverlay=pps-gpio,gpiopin=18`, `dtparam=uart0=on`, `enable_uart=1`, i2c/i2s/spi on |
| `/boot/firmware/cmdline.txt` | `root=PARTUUID=2ec0a0c9-02`; no `console=serial0` (it would fight gpsd for the UART) |
| `/boot/firmware/tryboot.txt`, `cmdline-sd.txt` | the SD-root fallback, derived from `config.txt` and `cmdline.txt` by `/usr/local/sbin/rpi-sd-fallback` (`pi-firmware`) |

## Files and units on the clients

| Path / unit | Hosts | What |
|-------------|-------|------|
| `/etc/chrony/chrony.conf` | all | sources, `makestep 1 3`, `rtcsync`, `port 0`, `cmdport 0` |
| `/etc/linuxptp/ptp4l.conf` | PTP | slave config, logs to stdout (journal) |
| `ptp4l@<interface>.service` + drop-in | PTP | waits for the link, `Restart=on-failure` |
| `chrony.service.d/ptp.conf` | PTP | chrony starts after ptp4l, waits up to 90 s for SLAVE |
| `/etc/apparmor.d/disable/usr.sbin.ptp4l` | PTP with AppArmor (isa) | keeps linuxptp's profile unloaded |
| `time-client-metrics.timer` (30 s) | all | `/usr/local/sbin/time-client-metrics <dir> [<interface>]` |
| `/var/lib/buckle/facts.d/ptp` | all Debian | the fact script |

## Buckle health checks

| Module: check | Required | Passes when |
|---------------|----------|-------------|
| `ptp-server: gpsd`, `ntpsec` | yes | unit active (ntpsec 30 s uptime) |
| `ptp-server: ntp-synced` | yes | `ntpq -pn` has a `*` line |
| `ptp-server: gps-pps-selected` | no | `*SHM(1) .PPS.` |
| `ptp-server: ptp4l-master` | yes | `portState MASTER` |
| `ptp-server: phc2sys` | yes | `phc2sys-eth0` active 30 s |
| `ptp-server: metrics` | no | `ntpsec.prom` younger than 3 min with `time_metrics_up{source="ntpsec"} 1` |
| `pi-firmware: sd-boot-only` | yes | where `rpi_sd_fallback_root` is set: EEPROM `BOOT_ORDER` has no 6 (NVMe) and no `PCIE_PROBE=1` |
| `time-sync: synchronized` | yes | `Leap status : Normal` |
| `time-sync: source` | no | `#* PTP` on PTP clients, `^* 192.168.0.109` elsewhere |

A failing required check pauses a rollout (`on_failure: pause`).

# Hosts and sources

## Hosts

Taken from each host's `host.facts.script.ptp` fact (snapshots in [`fixtures/facts/`](https://github.com/SpechtLabs/homelab/tree/main/fixtures/facts); the live value is `sudo /var/lib/buckle/facts.d/ptp` on the host).

| Host | Hardware | Syncs by | Interface / PHC | SSH |
|------|----------|----------|-----------------|-----|
| timepi | Pi 5 + u-blox M8 GPS HAT | GPS + PPS (grandmaster) | eth0, `/dev/ptp0` | `cedi@timepi` |
| isa | HP EliteDesk 800 G6 Mini, Intel I219 | PTP | eno1, PHC 0 | `cedi@isa` |
| jumphost | Pi 5 | PTP | eth0, PHC 0 | `pi@jumphost` |
| clusterpi-leader | Pi 5 | PTP | eth0, PHC 0 | `pi@clusterpi-leader` |
| storagepi-ceph1..3 | Pi 5 | PTP | eth0, PHC 0 | `pi@storagepi-cephN` |
| blade-pi1..4 | CM4 on a compute blade | PTP | eth0, PHC 0 | `pi@blade-piN` |
| clusterpi-worker1..4 | Pi 4 | NTP | eth0, no PHC | `pi@clusterpi-workerN` |
| nuc | Intel NUC | NTP | enp3s0, no PHC | `cedi@nuc` |
| meet | Hetzner vServer | not managed (`lan: false`) | | |

Measured: PTP clients ~10-70 ns system offset (RMS 20-60 ns; isa 35-90 ns with rare ~10 µs outliers, since Intel AMT shares its NIC), NTP clients a few µs (9 µs on clusterpi-worker1, 2026-11-26).

## Sources on timepi (ntpsec)

From [`ntp.conf.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/ptp-server/files/ntp.conf.j2). timepi is stratum 1 while it follows the PPS.

| `ntpq -pn` name | refid | What | Role |
|-----------------|-------|------|------|
| `SHM(1)` (127.127.28.1) | `.PPS.` | gpsd's PPS edges, numbered by the NMEA second | `prefer`; what ntpsec follows with a fix |
| `SHM(0)` (127.127.28.0) | `.GPS.` | gpsd's NMEA time, `time1 0.600` | `noselect`: arrives 150-600 ms late at 9600 baud |
| ptbtime1/2/3.ptb.de | `.PTB.` | PTB Braunschweig, stratum 1, ~20 ms away | fallback without a fix |
| 0/1/2.pool.ntp.org | `.POOL.` | public pool | fallback behind PTB |

## Sources on the clients (chrony)

From [`chrony.conf.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/time-sync/files/chrony.conf.j2).

| Source | PTP clients | NTP clients |
|--------|-------------|-------------|
| `refclock PHC /dev/ptp<phc>`, refid `PTP`, `offset -37` (TAI to UTC), `poll 0 dpoll -2` | `prefer` | |
| `server 192.168.0.109 iburst minpoll 1 maxpoll 3` (2-8 s) | fallback | `prefer` |
| `pool 2.debian.pool.ntp.org iburst maxsources 3` | fallback | fallback |
| `hwtimestamp eth0 rxfilter all` | | Pi 5s only (none today: every Pi 5 is a PTP client) |

A PTP client shows stratum 1 in `chronyc tracking` (the PHC is a stratum 0 refclock), an NTP client stratum 2.

## What the grandmaster announces

[`ptp-gm-quality`](https://github.com/SpechtLabs/homelab/blob/main/modules/ptp-server/files/ptp-gm-quality.sh) sets these every 15 s from ntpsec's selection. `ptp4l.conf` starts at clockClass 6, and the unit's `ExecStartPost` sets currentUtcOffset 37, currentUtcOffsetValid 1 and ptpTimescale 1.

| ntpsec follows | clockClass | clockAccuracy | timeSource | timeTraceable |
|----------------|-----------|---------------|------------|---------------|
| PPS (`*SHM(1)` or `oSHM(1)`) | 6 | 0x21 (100 ns) | 0x20 GPS | 1 |
| a network server | 52 | 0x31 (meant as 10 ms, see [Known issues](known-issues.md#the-fallback-clockaccuracy-says-more-than-10-s)) | 0x50 NTP | 1 |
| nothing | 248 | 0xfe (unknown) | 0xa0 oscillator | 0 |

# Ports and protocols

All of it runs on the home LAN, 192.168.0.0/24, by timepi's LAN address `192.168.0.109` (a fixed DHCP lease), never its tailnet name: time mustn't wait for Tailscale to come up.

| Port | Proto | On | Daemon | Who talks to it |
|------|-------|----|--------|-----------------|
| 123 | UDP | timepi, every address | ntpd (ntpsec) | NTP clients and the PTP clients' fallback, every 2-8 s |
| 319 | UDP | timepi `0.0.0.0` | ptp4l | PTP event messages (Sync, Delay_Req) |
| 320 | UDP | timepi `0.0.0.0` | ptp4l | PTP general messages (Announce, Follow_Up, Delay_Resp) |
| 2947 | TCP | timepi, localhost only | gpsd | ntpsec's SHM link doesn't use it; `gpspipe`, `ubxtool`, `time-metrics` do |
| 319, 320 | UDP | each PTP client | ptp4l | timepi's multicast and replies |

chrony on the clients serves nobody (`port 0`) and takes commands only on its local socket (`cmdport 0`), which is why `chronyc` needs `sudo`.

## NTP

- Served by ntpsec on timepi. `restrict default kod nomodify nopeer noquery limited` for everyone; `192.168.0.0/24` has no `limited`, so the LAN's fast polls never get kiss-o'-death replies.
- Upstream fallback: ptbtime1..3.ptb.de, then 0..2.pool.ntp.org.
- Client fallback: `2.debian.pool.ntp.org` (`ntp_pool`).
- Catalog: API `ntp` in [`modules/ptp-server/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/ptp-server/catalog-info.yaml).

## PTP

| Parameter | Grandmaster (timepi) | Clients |
|-----------|---------------------|---------|
| Version, profile | PTPv2, default (IEEE 1588) | same |
| Transport | UDPv4 | UDPv4 |
| Domain | 0 | 0 |
| `transportSpecific` | 0x0 | |
| Delay mechanism | E2E, `hybrid_e2e 0` | E2E, `hybrid_e2e 1` (Delay_Req by unicast to the grandmaster) |
| Sync / Delay_Req rate | `logSyncInterval -3`, `logMinDelayReqInterval -3` (8 a second) | |
| Announce | `logAnnounceInterval 1` (every 2 s), timeout 3 | |
| Role | `masterOnly 1`, `priority1 127` | `slaveOnly 1` |
| Timestamps | hardware, `hwts_filter full` (Pi 5 Ethernet) | hardware; `hwts_filter full` on Pi 5s; `tx_timestamp_timeout 50` |
| Timescale | TAI (UTC + 37 s) | chrony subtracts 37 s (`time_tai_utc_offset`) |

Files: [`ptp-server/files/ptp4l.conf`](https://github.com/SpechtLabs/homelab/blob/main/modules/ptp-server/files/ptp4l.conf) and [`time-sync/files/ptp4l-client.conf.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/time-sync/files/ptp4l-client.conf.j2). Catalog: API `ptp`.

Management: `pmc -u -b 0 '<GET ...>'` talks to the local ptp4l over its Unix socket `/var/run/ptp4l` (root only). Useful GETs: `PORT_DATA_SET`, `TIME_STATUS_NP`, `CURRENT_DATA_SET`, `PARENT_DATA_SET`, `GRANDMASTER_SETTINGS_NP` (grandmaster only).

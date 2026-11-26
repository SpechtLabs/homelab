# Check a host's time sync

Use this when you want to know whether a host keeps time, which source it follows (PTP or NTP) and how far off it is: after an alert, after adding a host, or after a reboot.

**Before you start:** SSH to the host. The user is `pi` on the Pis, `cedi` on isa, the NUC and timepi. For the whole fleet at once, skip to [In Grafana](#in-grafana).

## On a client (any host but timepi)

1. Ask chrony what it follows. chrony only listens on its local socket (`cmdport 0`), which is root's, so use `sudo`; without it you get `506 Cannot talk to daemon`.

   ```sh
   sudo chronyc -n sources
   ```

   The selected source carries a `*`:

    | You see | Meaning |
    |---------|---------|
    | `#* PTP` | PTP client, following the NIC's hardware clock that ptp4l keeps on timepi. Error bound tens of ns. |
    | `^* 192.168.0.109` | NTP from timepi. Normal on the Pi 4 workers and the NUC. On a PTP client it means ptp4l isn't locked. |
    | `^*` on any other address | timepi doesn't answer; chrony fell back to `2.debian.pool.ntp.org`. |
    | no `*` | not synchronised. |

2. Check the offset and the leap status:

   ```sh
   sudo chronyc -n tracking
   ```

   `System time` is the current offset. Expect well under 1 µs on PTP clients (`0.000000052 seconds` on isa, 2026-11-26) and under ~3 µs on NTP clients (median 0.2-0.3 µs over a week; a single `0.000009368` on clusterpi-worker1 the same day is still fine). `Leap status : Normal` means synchronised; that's what Buckle's `time-sync: synchronized` health check looks for.

3. On a PTP client, ask ptp4l directly:

   ```sh
   sudo pmc -u -b 0 'GET PORT_DATA_SET' 'GET TIME_STATUS_NP'
   ```

   You should see `portState SLAVE`, `gmPresent true` and a `master_offset` of a few ns to a few hundred ns. `LISTENING` or `FAULTY` means it isn't following timepi.

4. If you're not sure whether the host should be on PTP at all, read its fact:

   ```sh
   sudo /var/lib/buckle/facts.d/ptp
   ```

   `"lan":true,"hardware":true` puts it in the `ptp-client` group, `"lan":true,"hardware":false` in `ntp-client` only. See [Add a host as a PTP client](add-a-host-as-a-ptp-client.md).

The ptp4l unit is named after the interface from that fact: `ptp4l@eth0` on the Pis, `ptp4l@eno1` on isa. Its log has a summary line every 64 s:

```sh
journalctl -u ptp4l@eth0 -n 20 --no-pager
```

## On timepi

timepi runs ntpsec, not chrony.

```sh
ssh cedi@timepi
ntpq -pn
ntpq -c rv
sudo pmc -u -b 0 'GET PORT_DATA_SET' 'GET GRANDMASTER_SETTINGS_NP'
```

Healthy is `*SHM(1) .PPS.` in `ntpq -pn`, `stratum=1, ... refid=PPS` in `ntpq -c rv`, and `portState MASTER` with `clockClass 6` from pmc. A `*` on a `.PTB.` line instead means the GPS has no fix: see [Handle a GPS without a fix](handle-a-gps-without-a-fix.md).

## In Grafana

The [Time Server dashboard](https://spechtlabs.grafana.net/d/stratum1) (folder Infrastructure), row **Fleet clients**: worst client offset, offsets split into via PTP and via NTP, RMS offset by host and **Source per host**. The **Now** row covers timepi itself. The numbers come from `time-client-metrics`, which runs every 30 s; see [Metrics](../reference/metrics.md).

## If it doesn't look right

Go to the matching section of [Respond to a time-sync alert](respond-to-a-time-sync-alert.md), even if nothing has fired yet: [Host clock unsynchronised](respond-to-a-time-sync-alert.md#host-clock-unsynchronised), [PTP client lost the grandmaster](respond-to-a-time-sync-alert.md#ptp-client-lost-the-grandmaster) or [Host clock off by more than 1 ms](respond-to-a-time-sync-alert.md#host-clock-off-by-more-than-1-ms).

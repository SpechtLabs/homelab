# Add a host as a PTP client

Use this when a new host joins the home LAN and should follow timepi by PTP, or when an existing host stays on NTP and you want to know why.

**Before you start:** the host must be enrolled in Buckle (see the [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/)) and run Debian or Ubuntu. There's no host list to edit: `buckle.yaml` derives the groups from the `host.facts.script.ptp` fact that [`modules/ptp-facts`](https://github.com/SpechtLabs/homelab/blob/main/modules/ptp-facts/files/ptp-facts.sh.j2) reports.

| Fact | Group | What the host gets |
|------|-------|--------------------|
| `lan: true` | `ntp-client` | chrony from timepi over NTP |
| `lan: true` and `hardware: true` | `ptp-client` too | ptp4l on the fact's `interface`, chrony reading its hardware clock |
| `lan: false` | neither | nothing from `time-sync` |

## Check the host can do PTP

1. Is timepi on-link (no router between)?

   ```sh
   ip -o route get 192.168.0.109
   ```

   You want `192.168.0.109 dev eth0 src ...` with no `via`. A `via` means the host isn't on 192.168.0.0/24.
2. Can that NIC timestamp in hardware? Use the `dev` from step 1:

   ```sh
   sudo ethtool -T eth0
   ```

   It needs all three of `hardware-transmit`, `hardware-receive` and `hardware-raw-clock`, plus a clock: `PTP Hardware Clock: 0` (ethtool 6.1, Debian 12) or `Hardware timestamp provider index: 0` (newer). `none` or `-1` means no clock.
3. On a Raspberry Pi, the kernel must be newer than 6.12.34, whose PHCs refuse every adjustment:

   ```sh
   uname -r
   ```

   Every Pi has run 6.12.115 since 2026-11-19.

If all of that holds, the host becomes a PTP client by itself.

## Let Buckle set it up

1. Wait for the agent to report its facts and plan again. `ptp-facts` installs `ethtool` and the fact script on the first run; the agent reports changed facts and re-plans on its drift pass every 15 minutes (`drift.correct: true` in `/etc/buckle/agent.yaml`). Any rollout does it too.
2. Check the fact:

   ```sh
   sudo /var/lib/buckle/facts.d/ptp
   ```

   `{"lan":true,"interface":"eth0","phc":0,"hardware":true}`, for example.
3. Once `time-sync` has run, check ptp4l and chrony:

   ```sh
   systemctl status ptp4l@eth0 --no-pager
   sudo pmc -u -b 0 'GET PORT_DATA_SET'
   sudo chronyc -n sources
   ```

   `portState SLAVE` and `#* PTP` selected. chrony waits up to 90 s for ptp4l to be SLAVE when it starts.

On Ubuntu (AppArmor active) `time-sync` also disables linuxptp's AppArmor profile; see [Known issues](../reference/known-issues.md#apparmor-blocks-pmc-on-ubuntu). Nothing to do by hand.

## Check it worked

Within a few minutes the host appears under **via PTP** in the **Fleet clients** row of the [Time Server dashboard](https://spechtlabs.grafana.net/d/stratum1), with an offset in the tens of ns. Buckle's `time-sync: source` check (informational) expects `#* PTP`.

## When ptp-facts says no

- **`hardware: false`**: the NIC can't do PTP in hardware. The Pi 4 workers and the NUC are like that. The host stays an NTP client, a few µs off timepi, which the NTP SLO (within 100 µs) covers. There's no var to force PTP; the only way onto it is a NIC that passes step 2.
- **`lan: false`**: the route to `192.168.0.109` goes through a gateway (a VPS like meet, or a host on another subnet), or the host is timepi itself. `time-sync` doesn't touch it, so it keeps its distribution's own time sync.
- **`interface` is the wrong NIC**: the fact takes the interface the route to timepi leaves by. Fix the routing (or the cabling) rather than the fact.
- **The fact looks right but no ptp4l**: the agent hasn't re-planned yet, or the run failed. Check the host's last run in the Buckle UI.

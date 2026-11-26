# Respond to a time-sync alert

Use this when a Grafana alert from the rule group `time-sync` (folder Infrastructure, label `service=time-sync`) fires, or an SLO burn alert for one of the time SLOs. Each section below is one rule, titled exactly as the alert. The rules live in [`grafanaalertrules-time-sync.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanaalertrules-time-sync.yaml); thresholds and queries are in [Alerts, SLOs and dashboards](../reference/alerts-slos-and-dashboards.md).

**Before you start:** SSH to timepi (`cedi@timepi`) and to the host the alert names (`instance` label, e.g. `blade-pi2:9100`; log in as `pi` on the Pis, `cedi` on isa and the NUC). Keep the [Time Server dashboard](https://spechtlabs.grafana.net/d/stratum1) open.

## timepi — GPS PPS lost {#timepi-gps-pps-lost}

**Warning, after 30 min.** ntpsec on timepi hasn't selected the PPS for half an hour, so the receiver has no fix. timepi keeps serving, from PTB's stratum 1 servers over the internet: ~1 ms instead of ~1 µs, and PTP announces clockClass 52.

This happens several times a day because of the antenna's sky view, and usually clears on its own. Follow [Handle a GPS without a fix](handle-a-gps-without-a-fix.md).

## timepi — not synchronised {#timepi-not-synchronised}

**Critical, after 5 min.** ntpsec reports stratum 16: it has no usable source at all, neither the PPS nor PTB nor the pool. Every client follows a free-running clock (PTP announces clockClass 248).

1. Look at what ntpsec sees:

   ```sh
   ntpq -pn
   ```

   No line starts with `*`. If `SHM(1)` has `reach 0` the GPS has no fix too; if every `.PTB.` and pool line has `reach 0`, timepi can't reach the internet.
2. Check the daemons:

   ```sh
   systemctl status ntpsec gpsd --no-pager
   ```

3. If the network is the problem (the LAN or the uplink), fix that first; ntpsec picks the servers up again within a few polls (64 s each). If ntpsec itself is wedged:

   ```sh
   sudo systemctl restart ntpsec
   ```

   ntpsec reselects within a few minutes. Once the GPS has a fix it goes back to `*SHM(1)`.

**Check it worked:** `ntpq -c rv` shows `stratum=1` (PPS) or `stratum=2` (PTB), and the alert resolves 5 min later. On a client, `sudo chronyc -n tracking` shows `Leap status : Normal`.

## timepi — time metrics missing {#timepi-time-metrics-missing}

**Warning, after 15 min, also fires on no data.** Mimir has had no `ntpsec_stratum` from timepi for 15 min, so the two alerts above can't fire. Either timepi is down or the metrics path is broken.

1. Is timepi up? `ssh cedi@timepi`. If it doesn't answer, go to [Recover timepi when it doesn't boot](recover-timepi-when-it-doesnt-boot.md).
2. Check the timer, the last run and the textfile:

   ```sh
   systemctl status time-metrics.timer alloy --no-pager
   journalctl -u time-metrics -n 30 --no-pager
   grep time_metrics_up /var/lib/prometheus/node-exporter/ntpsec.prom
   ```

   You want `time_metrics_up{source="ntpsec"} 1` and a file younger than a minute. Buckle's `ptp-server: metrics` health check tests exactly that (max age 3 min).
3. If the file is fresh but Grafana has nothing, Alloy isn't shipping it: that's the o11y pipeline, see the [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/).

## Host clock off by more than 1 ms {#host-clock-off-by-more-than-1-ms}

**Warning, after 15 min.** chrony on the named host estimates its clock more than 1 ms off its source. Normal is nanoseconds (PTP) to microseconds (NTP).

1. On the host:

   ```sh
   sudo chronyc -n sources
   sudo chronyc -n tracking
   ```

2. Read the `*` line:
    - `^*` on a pool address: the host lost timepi. Check the `192.168.0.109` line's `Reach` column (`377` is every poll answered, `0` none) and whether `ntpq -pn` on timepi looks healthy. Once timepi answers again, chrony goes back to it by itself.
    - `^* 192.168.0.109` or `#* PTP` with a large offset: the host is converging after a jump. chrony steps the clock only in its first three updates (`makestep 1 3`) and slews after that, so a big offset late in life takes a while to shrink. Restart chrony to let it step again:

      ```sh
      sudo systemctl restart chrony
      ```

      On a PTP client the restart waits up to 90 s for ptp4l to be SLAVE before chrony starts.
3. If several hosts fire at once, suspect timepi: check it as in [Check a host's time sync](check-a-hosts-time-sync.md#on-timepi).

**Check it worked:** `System time` in `chronyc tracking` back under 1 ms (and, on PTP, under 1 µs).

## Host clock unsynchronised {#host-clock-unsynchronised}

**Warning, after 10 min.** chrony on the named host has reported a leap status other than Normal for 10 min: it follows nothing.

1. On the host:

   ```sh
   systemctl status chrony --no-pager
   sudo chronyc -n sources
   ```

   Every source has `Reach 0`, or chrony isn't running.
2. If no source answers, the host has no network to timepi or the internet: check `ping 192.168.0.109`.
3. If chrony is stuck, restart it:

   ```sh
   sudo systemctl restart chrony
   ```

**Check it worked:** `sudo chronyc -n tracking` says `Leap status : Normal`. Buckle's `time-sync: synchronized` health check, which gates rollouts, passes again.

## PTP client lost the grandmaster {#ptp-client-lost-the-grandmaster}

**Warning, after 10 min.** ptp4l on the named host hasn't been SLAVE for 10 min, or isn't running at all: `time-client-metrics` writes `ptp4l_port_slave 0` and `ptp4l_service_active 0` then. chrony meanwhile follows timepi over NTP, so the host is µs off instead of ns: not urgent.

1. On the host (unit name from the `interface` in its fact: `eth0` on the Pis, `eno1` on isa):

   ```sh
   systemctl status ptp4l@eth0 --no-pager
   sudo pmc -u -b 0 'GET PORT_DATA_SET'
   journalctl -u ptp4l@eth0 -n 40 --no-pager
   ```

2. On timepi, check the grandmaster: `sudo pmc -u -b 0 'GET PORT_DATA_SET'` must say `portState MASTER`, and `systemctl status ptp4l@eth0 phc2sys-eth0 --no-pager` both active. If every PTP client fired at once, it's timepi.
3. Match what you see:
    - ptp4l isn't running (`inactive` or `failed`; `ptp4l_service_active 0` on the dashboard's host): read the journal from step 1 for the reason, then start it. Its drop-in already restarts it 5 s after a failure, so one that stays down fails at start every time, and the journal says why:

      ```sh
      sudo systemctl restart ptp4l@eth0 && sudo systemctl restart chrony
      ```

    - `pmc` prints nothing, but ptp4l runs (isa, or any host with AppArmor): ptp4l is still confined by linuxptp's AppArmor profile and can't answer. The metrics script then reports `ptp4l_port_slave 0`, which fires this alert even if ptp4l is locked. See [Known issues](../reference/known-issues.md#apparmor-blocks-pmc-on-ubuntu). Check:

      ```sh
      cat /proc/$(pgrep -x ptp4l)/attr/current
      ```

      Output starting with `ptp4l ` means confined. The usual trigger is a linuxptp package upgrade, whose postinst loads the profile again. Buckle's `ptp4l-unconfined` task unloads it and restarts a confined ptp4l on its next run (within 15 min); by hand, do what it does:

      ```sh
      sudo apparmor_parser -R /etc/apparmor.d/usr.sbin.ptp4l
      sudo systemctl restart ptp4l@eno1 && sudo systemctl restart chrony
      ```

    - `portState FAULTY`, or the log says the PTP clock is missing: ptp4l started before the link came up. The unit's drop-in waits for the link, so a restart fixes it:

      ```sh
      sudo systemctl restart ptp4l@eth0 && sudo systemctl restart chrony
      ```

    - `received SYNC without timestamp` repeating: the NIC missed receive timestamps. `hybrid_e2e 1` in `/etc/linuxptp/ptp4l.conf` prevents the usual cause; check it's there (Buckle owns the file).
    - `LISTENING` with no grandmaster: the host doesn't see timepi's announcements. Check the host is on 192.168.0.0/24 (`ip -4 addr`), and timepi's ptp4l.

**Check it worked:** `pmc` shows `SLAVE`, and within a minute `sudo chronyc -n sources` shows `#* PTP` again. If chrony stays on NTP while ptp4l is SLAVE, Buckle's `chrony-follow-ptp` task restarts chrony on its next run; `sudo systemctl restart chrony` does the same now.

## SLO burn alerts {#slo-burn-alerts}

Grafana generates fast- and slow-burn alerts for the three time SLOs (labels `service=time-sync`); see [Alerts, SLOs and dashboards](../reference/alerts-slos-and-dashboards.md#slos).

| SLO | Fast burn | What to do |
|-----|-----------|------------|
| Homelab — clock accuracy (PTP clients) | critical | PTP clients spend minutes more than 10 µs off. Run [Host clock off by more than 1 ms](respond-to-a-time-sync-alert.md#host-clock-off-by-more-than-1-ms) on the worst host (dashboard: **Fleet clients > RMS offset by host**). |
| Homelab — clock accuracy (NTP clients) | critical | Same, for hosts on NTP (threshold 100 µs). |
| Homelab — timepi on GPS time (stratum 1) | warning, never pages | The GPS keeps losing its fix. [Handle a GPS without a fix](handle-a-gps-without-a-fix.md); the long-term fix is the antenna. |

# Respond to a UPS alert

Use this when one of the `UPS — ...` alerts fires. They're in SpechtLabs/k8s-deployment,
`apps/grafana-operator/cluster/specht-labs/grafanaalertrules-ups.yaml` (group `ups`, folder
Infrastructure), and read the metrics `ups-metrics` writes on isa every 30 s
([UPS and NUT](../reference/ups-and-nut.md#metrics)).

**Before you start:** `ssh cedi@isa`, over the tailnet or on the LAN (`ssh cedi@192.168.0.118`)
if the internet went with the power. Every command below only reads, except
`sudo upsmon -c fsd`, which shuts the fleet down.

The power-loss shutdown runs by itself. Most of these alerts tell you it's happening; act only
where a section says so.

## UPS — on battery {#ups-on-battery}

The house lost mains power a minute ago.

1. Confirm it:

    ```sh
    ssh cedi@isa "bash -c 'upsc ups@localhost | grep -E \"^(ups.status|battery.charge|battery.runtime|ups.load):\"'"
    ```

    `ups.status: OB DISCHRG`.

2. Expect the early hosts (labk3s, Ceph, the blades, the NUC) to power off now, 60 s into the
   outage. jumphost, timepi and isa stay up until the UPS reports low battery.
3. Follow [Respond to a power cut](respond-to-a-power-cut.md).

It resolves when `ups_status{flag="OB"}` drops back to 0. A blip that ends within 60 s fires
nothing: the rule waits a minute.

## UPS — less than 10 minutes of battery left {#ups-runtime-low}

The UPS is on battery and estimates under 600 s of runtime. When it sets LB, isa takes the rest
down by itself. If you'd rather not wait (you know the outage will last), do it now:

```sh
ssh cedi@isa "sudo upsmon -c fsd"
```

That sets FSD on isa's upsd: every NUT host powers off, isa last. It can't be undone; the hosts
come back only once their power is cycled or the UPS runs flat and the mains return.

## UPS — battery low {#ups-battery-low}

The UPS Tower set LB. isa's upsmon, the primary, sets FSD within one poll (5 s), and
the alert `UPS — forced shutdown (FSD) set` follows. Nothing to do. If FSD doesn't
follow within a minute, isa's primary isn't working: the secondaries then shut down on their own
after 15 s (`HOSTSYNC`), but isa itself won't, and goes down hard when the battery runs out.

## UPS — forced shutdown (FSD) set {#ups-forced-shutdown}

FSD is set on isa's upsd: on low battery, or because someone ran `upsmon -c fsd`. Every NUT host
powers off; isa waits up to 30 s for them to log out, then shuts down itself. The NAS doesn't
see FSD and follows DSM's own UPS settings.

Once the power is back, see [Respond to a power cut](respond-to-a-power-cut.md#once-power-is-back).
FSD clears when upsd starts again with isa.

## UPS — metrics stale {#ups-metrics-stale}

isa hasn't read the UPS through its own upsd for over 5 minutes. If isa shut down in a power
cut, that's expected; the alert resolves once isa is back. Otherwise the chain is broken, and
with it the power-loss shutdown.

1. Read the UPS the way `ups-metrics` does:

    ```sh
    ssh cedi@isa "bash -c 'upsc ups@localhost ups.status; systemctl is-active nut-driver@ups nut-server nut-monitor ups-metrics.timer'"
    ```

    `OL` and four times `active`.

2. If `upsc` fails, walk the chain: [Check the UPS and the NUT chain](check-the-ups-and-the-nut-chain.md).
3. If `upsc` works but the metrics are old, the script fails:

    ```sh
    ssh cedi@isa "bash -c 'journalctl -u ups-metrics -n 20 --no-pager; ls -l /var/lib/prometheus/node-exporter/ups.prom'"
    ```

## UPS — no metrics recorded {#ups-metrics-missing}

Grafana has no `ups_metrics_last_success_timestamp_seconds` at all for 15 minutes: `ups-metrics`
never ran, its timer is off, or isa's Alloy isn't shipping.

```sh
ssh cedi@isa "bash -c 'systemctl list-timers ups-metrics.timer --no-pager; systemctl is-active alloy; cat /var/lib/prometheus/node-exporter/ups.prom | head'"
```

The timer should list a next run within 30 s, Alloy `active`, and the file start with
`# HELP ups_status`. No timer: the `nut-server` module hasn't been applied to isa yet (its
host page in Buckle). Alloy down: [Observability docs](https://backstage.k8s.specht-labs.de/docs/default/system/observability/).

## UPS — replace the battery {#ups-replace-battery}

The UPS reports `RB`, or its last weekly self-test failed or warned (`ups_test_failed`).

```sh
ssh cedi@isa "bash -c 'upsc ups@localhost | grep -E \"^(ups.status|ups.test.result|ups.test.date|battery.charge|battery.runtime):\"'"
```

Until the battery is replaced, the runtime numbers and the time to LB are shorter than they
look. Replacing it means taking the UPS off line; do that with the fleet shut down, or the
outlets go dark under everything.

!!! warning "Unverified"
    Whether this UPS reports `RB` at all, and which `ups.test.result` texts it uses besides
    `done and passed`, hasn't been seen. The rule also fires on any result that mentions fail,
    error or warn.

## Check it worked

The alert resolves on its own once the condition is gone, and
`upsc ups@localhost ups.status` on isa prints `OL` (or `OL CHRG` while it recharges).

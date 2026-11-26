# Respond to a power cut

Use this when the house loses mains power (alert `UPS — on battery`), or when it's just come
back.

**Before you start:** if the internet went with the power, the tailnet won't reach home
either; these steps assume you can get to isa, over the tailnet or on the LAN
(`ssh cedi@192.168.0.118`). What happens without you is in
[How power-loss shutdown is ordered](../explanation/power-loss-shutdown.md).

## While it's out

1. See what the UPS says:

    ```sh
    ssh cedi@isa "bash -c 'upsc ups@localhost | grep -E \"^(ups.status|battery.charge|battery.runtime|ups.load):\"'"
    ```

    `ups.status: OB DISCHRG` while on battery; `OB LB` once it's low.

2. Expect the early hosts (labk3s's Pis, the Ceph Pis, the blades, the NUC) to power off about
    60 s after the cut. They log
    `UPS on battery for 60s - shutting down system` first. Don't fight it: there's nothing
    to save by keeping them up.

3. isa, jumphost, timepi and the NAS keep running until the UPS reports battery low. Then isa,
    the NUT primary, sets FSD: jumphost and timepi power off at once, isa within about 35 s
    after them. The NAS follows DSM's own UPS settings. If you'd rather have the fleet down
    sooner (a long outage, a known repair), set FSD by hand:

    ```sh
    ssh cedi@isa "sudo upsmon -c fsd"
    ```

## Once power is back

1. Check the UPS is on line power and charging:

    ```sh
    ssh cedi@isa "bash -c 'upsc ups@localhost ups.status'"
    ```

    `OL CHRG`, later `OL`.

2. Find hosts that didn't come back. Buckle's host list shows each host's agent as connected
    or not; from your machine, `tailscale status` shows the same per device.

    Hosts that powered off stay off if the mains came back before the battery ran flat:
    nothing tells this UPS to cut its outlets after a shutdown (no kill-power, see
    [the explanation](../explanation/power-loss-shutdown.md#why-theres-no-kill-power)). Cycle
    their power by hand: pull and re-plug the supply, or the PoE port for a blade.

3. Check the NAS: `https://nas.sphinx-map.ts.net` loads DSM, and

    ```sh
    curl -s https://stream.sphinx-map.ts.net/health
    ```

    prints `Healthy`.

4. Check the NUT chain end to end:
    [Check the UPS and the NUT chain](check-the-ups-and-the-nut-chain.md), steps 1 and 5. The
    client count from `upsc -c ups@localhost` tells you how many are back: 16 with all 15 secondaries and isa's own primary.

5. Let the other Systems recover and check them in their own docs:
    [Ceph](https://backstage.k8s.specht-labs.de/docs/default/system/ceph/),
    [labk3s](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/),
    [Timekeeping](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/) (timepi
    needs a GPS fix again before it's a stratum 1).

## Check it worked

In Grafana, the availability SLOs for the NAS, Jellyfin and Home Assistant show
`probe_success` back at 1 (see [Monitoring](../reference/monitoring.md)), and every Buckle host
is connected and healthy.

## If it didn't

A host that's on but not in Buckle: [Fleet docs](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/).
A host that's on but unreachable on the tailnet:
[Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/).

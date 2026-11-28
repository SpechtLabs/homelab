# Check the UPS and the NUT chain

Use this when you want the UPS's state, when a Buckle host shows `nut-client: ups-reachable`,
`nut-server: proxied-ups` or `nut-server: primary` failing, when `UPS — metrics stale` fires,
or before you trust the chain for a power cut.

**Before you start:** SSH to isa (`ssh cedi@isa`) and to any Pi (`ssh pi@<host>`). Every
command here only reads.

The Grafana dashboard `UPS & NUT` (folder Infrastructure) shows most of this at a glance: the
UPS's state, isa's primary upsmon and, in the Clients table, each host whose upsmon is stopped
or can't read the UPS through `svc:nut`. The steps below confirm on the hosts what it shows.

1. Read the UPS through isa's proxy:

    ```sh
    ssh cedi@isa "bash -c 'upsc ups@localhost | grep -E \"^(ups.status|battery.charge|battery.runtime|ups.load|input.voltage):\"'"
    ```

    You should see `ups.status: OL`, `battery.charge: 100` and a `battery.runtime` in seconds
    (about 1160 at 22 % load). `OB` means on battery, `LB` battery low.

2. Ask the UPS Tower directly, from isa, even if step 1 looked fine: when `dummy-ups` loses the
    UPS Tower it keeps serving the last values it had, so step 1 can show `OL` during an outage.

    ```sh
    ssh cedi@isa "bash -c 'upsc ups@192.168.0.154 ups.status'"
    ```

    A different status here than in step 1: the proxy on isa is the problem; go to step 3. No
    answer here: the UPS or its network is the problem. Check that the UPS Tower still has
    192.168.0.154 (`ping UPSTower.local` from the Mac shows its current address; its DHCP lease
    has to stay fixed) and open its web UI. A new address goes into `nut_upstream_host`
    (modules/nut-server) and DSM's UPS settings.

3. Check the services on isa:

    ```sh
    ssh cedi@isa "bash -c 'systemctl is-active nut-driver@ups nut-server nut-monitor; journalctl -u nut-driver@ups -u nut-server -n 20 --no-pager'"
    ```

    All three should be `active`. The log shows `Connected to UPS [ups]: dummy-ups-ups` after
    each start of upsd, `User admin@127.0.0.1 logged into UPS [ups]` when isa's own upsmon
    logs in as the primary, and `User monuser@127.0.0.1 logged into UPS [ups]` as the
    secondaries connect.

4. Check that isa is the primary, as Buckle's `primary` check does:

    ```sh
    ssh cedi@isa "bash -c 'sudo grep ^MONITOR /etc/nut/upsmon.conf | cut -d" " -f1-4,6; journalctl -b -u nut-server -o cat --no-pager -q | grep -E "User admin@" | tail -n 1'"
    ```

    `MONITOR ups@localhost 1 admin primary` and, last, `User admin@127.0.0.1 logged into UPS
    [ups]`. A `logged out from` line last means isa's upsmon isn't the primary any more:
    `sudo systemctl status nut-monitor`.

5. Check `svc:nut` the way the clients use it, from any Pi:

    ```sh
    ssh pi@jumphost "bash -c 'upsc ups@nut.sphinx-map.ts.net ups.status'"
    ```

    `OL` (after an `Init SSL without certificate database` line). If it fails while step 1
    works, isa isn't serving the Service:

    ```sh
    ssh cedi@isa "bash -c 'sudo tailscale serve get-config --all'"
    ```

    It should contain `"tcp:3493": "tcp://localhost:3493"` under `svc:nut`. The `nut-server`
    module adds it on its next run; the host needs `tag:nut-server` for the Service to approve it.

6. See which clients are logged in:

    ```sh
    ssh cedi@isa "bash -c 'upsc -c ups@localhost'"
    ```

    One `127.0.0.1` line per logged-in upsmon: 16 with every Pi, the NUC and isa's primary up.
    The same number is `ups_clients` in Grafana.

7. On a client, check upsmon itself:

    ```sh
    ssh pi@clusterpi-worker1 "bash -c 'systemctl is-active nut-monitor; sudo cat /etc/nut/upssched.conf'"
    ```

    `active`, and `# Shutdown affinity: early` with `START-TIMER onbatt_shutdown 60` (or
    `late` with only `AT FSD` on jumphost and timepi).

## Check it worked

Buckle's host pages show `ups-reachable` passing on every client, and `proxied-ups` and
`primary` on isa.

## If it didn't

- Values and expected settings: [UPS and NUT](../reference/ups-and-nut.md).
- isa down altogether: [isa, and why so much runs on it](../explanation/isa.md) says what else
  that breaks.
- Grants for `svc:nut` and Services in general:
  [Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/).

# Check the UPS and the NUT chain

Use this when you want the UPS's state, when a Buckle host shows `nut-client: ups-reachable`
or `nut-server: proxied-ups` failing, or before you trust the chain for a power cut.

**Before you start:** SSH to isa (`ssh cedi@isa`) and to any Pi (`ssh pi@<host>`). Every
command here only reads.

1. Read the UPS through isa's proxy:

    ```sh
    ssh cedi@isa "bash -c 'upsc ups@localhost | grep -E \"^(ups.status|battery.charge|battery.runtime|ups.load|input.voltage):\"'"
    ```

    You should see `ups.status: OL`, `battery.charge: 100` and a `battery.runtime` in seconds
    (about 1160 at 22 % load). `OB` means on battery, `LB` battery low.

2. If step 1 fails, ask the UPS Tower directly, from isa:

    ```sh
    ssh cedi@isa "bash -c 'upsc ups@192.168.0.156 ups.status'"
    ```

    `OL` here but not in step 1: the proxy on isa is the problem; go to step 3. No answer here:
    the UPS or its network is the problem. Check that 192.168.0.156 still has its address (its
    DHCP lease has to stay fixed) and open its web UI.

3. Check the services on isa:

    ```sh
    ssh cedi@isa "bash -c 'systemctl is-active nut-driver@ups nut-server nut-monitor; journalctl -u nut-driver@ups -u nut-server -n 20 --no-pager'"
    ```

    All three should be `active`. The log shows `Connected to UPS [ups]: dummy-ups-ups` after
    each start of upsd, and `User monuser@127.0.0.1 logged into UPS [ups]` as clients connect.

4. Check `svc:nut` the way the clients use it, from any Pi:

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

5. See which clients are logged in:

    ```sh
    ssh cedi@isa "bash -c 'upsc -c ups@localhost'"
    ```

    One `127.0.0.1` line per client that came through `svc:nut`: 15 with every Pi and the NUC
    up.

6. On a client, check upsmon itself:

    ```sh
    ssh pi@clusterpi-worker1 "bash -c 'systemctl is-active nut-monitor; sudo cat /etc/nut/upssched.conf'"
    ```

    `active`, and `# Shutdown affinity: early` with `START-TIMER onbatt_shutdown 60` (or
    `late` with only `AT FSD` on jumphost and timepi).

## Check it worked

Buckle's host pages show `ups-reachable` passing on every client and `proxied-ups` on isa.

## If it didn't

- Values and expected settings: [UPS and NUT](../reference/ups-and-nut.md).
- isa down altogether: [isa, and why so much runs on it](../explanation/isa.md) says what else
  that breaks.
- Grants for `svc:nut` and Services in general:
  [Tailnet docs](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/).

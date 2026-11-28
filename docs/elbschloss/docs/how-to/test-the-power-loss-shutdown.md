# Test the power-loss shutdown

Use this after a change to `nut-server`, `nut-client` or the NUT groups, after replacing isa,
or when you simply want to know the chain would work. The repo has no simulation mode, so the
safe test checks each link and the rendered config; it doesn't cut power.

**Before you start:** SSH to isa and to one early and one late host. Nothing here changes state.

!!! danger "Don't run these"
    `upsmon -c fsd` on any host, `/etc/nut/upssched-cmd <anything>`, or setting `FSD` with
    upsd's `admin` user. Each of them powers hosts off for real: on isa, the primary, an `FSD`
    reaches every client at once and then shuts isa down too.

1. Walk the chain from the UPS to a client, as in
    [Check the UPS and the NUT chain](check-the-ups-and-the-nut-chain.md), steps 1 to 6. Every
    link must answer `OL`, isa's upsmon must be logged in as the primary, and
    `upsc -c ups@localhost` on isa must list one line per upsmon (16).

2. Check an early host's rendered config:

    ```sh
    ssh pi@clusterpi-worker1 "bash -c 'sudo cat /etc/nut/upssched.conf; sudo grep -E \"^(MONITOR|FINALDELAY|NOTIFYCMD|NOTIFYFLAG)\" /etc/nut/upsmon.conf | sed \"s/monuser .*/monuser .../\"'"
    ```

    After the header and the `CMDSCRIPT`, `PIPEFN`, `LOCKFN` lines you should see:

    ```text
    AT ONBATT * START-TIMER onbatt_shutdown 60
    AT ONLINE * CANCEL-TIMER onbatt_shutdown
    AT FSD * EXECUTE immediate_shutdown
    MONITOR ups@nut.sphinx-map.ts.net 1 monuser ...
    FINALDELAY 5
    NOTIFYCMD /sbin/upssched
    NOTIFYFLAG ONLINE SYSLOG+EXEC
    NOTIFYFLAG ONBATT SYSLOG+EXEC
    NOTIFYFLAG FSD SYSLOG+EXEC
    ```

3. Check a late host's:

    ```sh
    ssh pi@jumphost "bash -c 'sudo cat /etc/nut/upssched.conf; sudo grep FINALDELAY /etc/nut/upsmon.conf'"
    ```

    Only `AT FSD * EXECUTE delayed_shutdown`, and `FINALDELAY 180`. Same on timepi
    (`ssh cedi@timepi`).

4. Check isa's upsmon is the primary of its own upsd, without a kill-power flag:

    ```sh
    ssh cedi@isa "bash -c 'sudo grep -E \"^(MONITOR|HOSTSYNC|FINALDELAY|POWERDOWNFLAG)\" /etc/nut/upsmon.conf | sed \"s/admin .*primary/admin ... primary/\"; sudo upsmon -K; echo killpower=\$?'"
    ```

    `MONITOR ups@localhost 1 admin ... primary`, `HOSTSYNC 30`, `FINALDELAY 5`, no
    `POWERDOWNFLAG` line, and `upsmon -K` complaining `No POWERDOWNFLAG value was configured`
    with a non-zero `killpower=`.

5. Check that the right hosts are in the right group: Buckle's fleet view should show
    `nut-client` on every Pi and the NUC, and `nut-late` only on jumphost and timepi. The groups
    are in [buckle.yaml](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml).

6. Check the NAS's own UPS client still points at the UPS Tower:

    ```sh
    ssh -J cedi@nyx king@nas.local 'sudo grep -E "^(ups_mode|upsslave_server|upsslave_enabled)" /usr/syno/etc/ups/synoups.conf'
    ```

    `ups_mode="slave"`, `upsslave_server="192.168.0.154"`, `upsslave_enabled="yes"`.

## Check it worked

All six steps match. That proves every host would hear about a power cut, isa would set FSD,
and the timers are the intended ones. It doesn't prove the UPS sets `LB` in time, or that hosts
come back afterwards.

## A real test

!!! warning "Unverified: never done under this config"
    The only end-to-end test is taking mains away from the UPS Tower. If it stays off for more
    than about 60 s, every early host powers off: labk3s, Ceph, the blades and the NUC. Back
    within 60 s, `ONLINE` cancels their timers and nothing should go down; leave a margin for
    the 2 s proxy poll and the 5 s client poll. Watch `journalctl -f` on an early host while you
    do it: upsmon logs the change to battery, and `upssched-cmd` logs
    `UPS on battery for 60s - shutting down system` just before it powers off. The alert
    `UPS — on battery` fires after a minute. Pick a time when a Ceph and labk3s restart
    wouldn't hurt.

## If it didn't

The reasons for the order, why FSD waits for low battery, and why there's no kill-power are in
[How power-loss shutdown is ordered](../explanation/power-loss-shutdown.md).

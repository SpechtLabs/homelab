# Restart a daemon

Use this when a Ceph daemon (mon, mgr, OSD, RGW, crash, ceph-exporter) isn't running, or when every daemon on one host stopped at once.

**Before you start:** SSH to the host that runs the daemon (`ssh pi@storagepi-cephN`). Restarting one OSD or one mon is safe while the other two hosts are healthy; check `sudo cephadm shell -- ceph -s` first, and don't restart daemons on two hosts at the same time.

Every daemon is a systemd unit `ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@<daemon>.service` that runs a Docker container. `<daemon>` is the name `ceph orch ps` prints.

## One daemon

1. Find its name and state:

   ```sh
   sudo cephadm shell -- ceph orch ps storagepi-ceph1
   ```

   The `STATUS` column says `running`, `stopped` or `error`.
2. Restart it through the orchestrator (works from any of the three hosts):

   ```sh
   sudo cephadm shell -- ceph orch daemon restart <daemon>
   ```

   Or, on the host itself, start the unit directly:

   ```sh
   sudo systemctl start ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@<daemon>
   ```

3. If it won't stay up, read its log:

   ```sh
   sudo cephadm logs --name <daemon> -- --since -1h
   ```

## All daemons on a host stopped

This is what a Docker restart does: Docker sends every container SIGTERM, the daemons exit 0, and cephadm's own unit (`Restart=on-failure`) treats that as a clean stop. On 2026-11-25 the nightly `base/upgrade` installed a new docker-ce on storagepi-ceph1 and its mon, mgr and OSD stayed down for 7 hours, although Docker itself was back after 8 seconds.

Since then Buckle installs a drop-in with `Restart=always`, so the daemons come back on their own within about 20 seconds. If they didn't:

1. Confirm the drop-in is there:

   ```sh
   systemctl cat ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@osd.0 | grep -E 'buckle-restart|^Restart='
   ```

   (Use the host's own OSD or mon.) You should see cephadm's `Restart=on-failure`, then the path `/etc/systemd/system/ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@.service.d/buckle-restart.conf` and `Restart=always`, which wins. Missing: the host hasn't had a Buckle run since the module change, or `ceph_fsid` isn't set for it.
2. List the units, stopped ones included:

   ```sh
   systemctl list-units --all 'ceph-*'
   ```

3. Find out why they stopped:

   ```sh
   journalctl -u docker --since -12h
   journalctl -u ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@mon.storagepi-ceph1 --since -12h
   ```

4. Start each one that's `inactive` or `failed`:

   ```sh
   sudo systemctl start ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@mon.storagepi-ceph1
   sudo systemctl start ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@osd.0
   # ...and the mgr, crash and ceph-exporter units from the list
   ```

`systemctl stop` (which `ceph orch daemon stop` uses) still stops a daemon for good: `Restart=always` doesn't fight a deliberate stop.

## Check it worked

```sh
sudo cephadm shell -- ceph -s
sudo cephadm shell -- ceph orch ps storagepi-ceph1
```

All three mons in quorum, 3 OSDs up, the daemon `running`. Degraded PGs after an OSD returns recover on their own; wait for `active+clean`. On the *Ceph - Status* dashboard, the host's row goes green; the *Ceph — daemon not running* alert clears only after cephadm's next inventory refresh (a few minutes).

## If it didn't

- Docker itself won't start: `systemctl status docker`. Everything Ceph runs depends on it.
- The OSD starts but stays down: [Respond to a Ceph alert: OSD down](respond-to-a-ceph-alert.md#ceph-osd-down).
- The mon starts but stays out of quorum: [Respond to a Ceph alert: monitor out of quorum](respond-to-a-ceph-alert.md#ceph-monitor-out-of-quorum).
- Background on the restart behaviour: [Failure modes seen so far](../explanation/failure-modes.md).

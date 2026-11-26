# Respond to a backup alert

Use this when Grafana fires **Buckle — database backup on the NAS is stale** (no NAS copy for over
26 h) or **Buckle — no database backup on the NAS recorded** (the metric is missing for 26 h). Both
are `severity: warning` rules in the `homelab-platform` group, folder Infrastructure.

The backup itself: `buckle-backup.timer` on isa runs `/usr/local/sbin/buckle-backup` every night at
01:30 (isa's clock is UTC), takes a `sqlite3 .backup` of `/var/lib/buckle-server/buckle.db` into
`/var/backups/buckle/` (kept 3 days), then copies it to the NAS share mounted at
`/mnt/nas/backups` (kept 14 days). The NAS share is NFS v4.1 through the Tailscale Service
`svc:nfs`. Each step writes a timestamp to
`/var/lib/prometheus/node-exporter/buckle_backup.prom`, which Alloy exports.

**Before you start:** SSH to isa as `cedi`. Nothing here is urgent: the fleet keeps running
without backups.

1. See what the last run did:

    ```sh
    ssh cedi@isa "bash -c 'systemctl list-timers buckle-backup.timer --no-pager; sudo journalctl -u buckle-backup -n 30 --no-pager'"
    ```

    A good run ends with `backed up to /var/backups/buckle/... and /mnt/nas/backups/...`.
2. Check the metric file and both copies:

    ```sh
    ssh cedi@isa "bash -c 'cat /var/lib/prometheus/node-exporter/buckle_backup.prom; sudo ls -lt /var/backups/buckle | head -4; sudo ls -lt /mnt/nas/backups | head -4'"
    ```

3. If the log says `the NAS isn't mounted at /mnt/nas/backups: kept the local copy only`, the
   mount failed. Check it:

    ```sh
    ssh cedi@isa "bash -c 'systemctl status mnt-nas-backups.mount --no-pager; findmnt /mnt/nas/backups'"
    ```

    The usual causes are outside isa: the NAS is down, `svc:nfs` isn't served, the tailnet policy
    no longer grants `tag:buckle-server` access to `svc:nfs` on `tcp:2049`, or DSM's NFS rule for
    `127.0.0.1` changed. Those belong to the
    [elbschloss](https://backstage.k8s.specht-labs.de/docs/default/system/elbschloss/) and
    [tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/) docs.
4. Once the cause is fixed, run the backup now:

    ```sh
    ssh cedi@isa "bash -c 'sudo systemctl start buckle-backup.service && sudo journalctl -u buckle-backup -n 5 --no-pager'"
    ```

## Check it worked

`buckle_backup.prom` shows a fresh `target="nas"` timestamp, and the alert resolves within the
rule's 5-minute evaluation. On the host, `sudo buckle health` lists `buckle-server/backup-recent`
as passing.

## If it didn't

- The timer isn't listed at all: the `buckle-server` module didn't apply on isa. Check isa's last
  run (`sudo buckle status`).
- The alert is "missing" right after a move of the server: the new host has no metric until its
  first run. Start the service by hand as in step 4.
- Restoring from these copies: [Restore the server database](restore-the-server-database.md).

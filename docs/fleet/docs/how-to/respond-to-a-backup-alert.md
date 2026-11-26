# Respond to a backup alert

Use this when Grafana fires **NAS backup is stale** or **NAS backup never recorded**. Both are
`severity: warning` rules in the `homelab-platform` group (folder Infrastructure), and each fires
once per backup and host: the `backup` label names it (`buckle`, `buckle-secrets`, `tsidp`, `k3s`),
`instance` the host (`isa:9100`, `clusterpi-leader:9100`). The backups, their folders and metrics
are listed in [Backups](../reference/backups.md).

Nothing here is urgent: the services run without their backups. The local copies in
`/var/backups/<backup>/` are usually still fresh, so a lost NAS copy costs history, not data.

**Before you start:** SSH to the host the alert names (`cedi@isa`, `pi@clusterpi-leader`).

## NAS backup is stale {#nas-backup-stale}

The backup's last NAS copy is more than 26 h old: it ran, but the NAS step has failed since.

1. Read the last run:

    ```sh
    ssh cedi@isa "bash -c 'systemctl list-timers nas-backup.timer --no-pager; sudo journalctl -u nas-backup -n 40 --no-pager'"
    ```

    Each backup prints one line. A good one reads
    `buckle: backed up to /var/backups/buckle/buckle-nightly-<date>.db and nfs.sphinx-map.ts.net:/volume1/homelab/buckle/...`.
2. Match the failure:
    - `<backup>: can't mount nfs.sphinx-map.ts.net:/volume1/homelab/<folder>: kept the local copy only`:
      the NFS mount failed. Usual causes, none of them on this host: the NAS is down, `svc:nfs`
      isn't served, the tailnet policy no longer grants this host's tag (`tag:buckle-server` on
      isa, `tag:k3s-server` on clusterpi-leader) `svc:nfs` on `tcp:2049`, or the folder doesn't
      exist on the NAS. Try the mount by hand:

        ```sh
        ssh cedi@isa "bash -c 'sudo mkdir -p /run/nas-backup/test && sudo mount -t nfs -o nfsvers=4.1,soft nfs.sphinx-map.ts.net:/volume1/homelab/buckle /run/nas-backup/test && sudo ls /run/nas-backup/test | tail -3; sudo umount /run/nas-backup/test'"
        ```

      The NAS side belongs to the
      [elbschloss](https://backstage.k8s.specht-labs.de/docs/default/system/elbschloss/) docs, the
      grant to the [tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/) docs.
    - `<backup>: copying to the NAS failed`: mounted, but the write failed (NAS volume full, the
      folder's permissions changed).
    - `VACUUM INTO failed`, `fails quick_check`, `tar failed`: the source itself. Check the
      database or directory named in [Backups](../reference/backups.md); for a database, `sudo
      sqlite3 <source> 'PRAGMA quick_check;'`.
3. Once the cause is fixed, run the backups now:

    ```sh
    ssh cedi@isa "bash -c 'sudo systemctl start nas-backup.service; sudo journalctl -u nas-backup -n 10 --no-pager'"
    ```

## NAS backup never recorded {#nas-backup-missing}

The host is meant to run the backup (Buckle wrote it into `nas_backup_configured`) but has no NAS
timestamp for it at all, for 26 h: the timer never ran, the backup is new and failed every night,
or the metric file was lost.

1. Check that the timer exists and when it last fired:

    ```sh
    ssh pi@clusterpi-leader "bash -c 'systemctl list-timers nas-backup.timer --no-pager; cat /etc/nas-backup/backups'"
    ```

    No timer: the `nas-backup` module didn't apply on the host. Read its last run with
    `sudo buckle status | grep -A12 nas-backup`.
2. Look at the metric file the alerts read:

    ```sh
    ssh pi@clusterpi-leader "bash -c 'cat /var/lib/prometheus/node-exporter/nas_backup.prom'"
    ```

    No `target="nas"` line for the backup: it never reached the NAS. Continue as for a stale
    backup (the section above), from its step 1.
3. A brand-new backup whose NAS folder doesn't exist yet fails at the mount every night until
   someone creates the folder on the NAS (DSM, File Station, under `homelab`).

## Check it worked

```sh
ssh cedi@isa "bash -c 'sudo /usr/local/sbin/nas-backup check /var/lib/prometheus/node-exporter'"
```

prints `ok: every backup reached the NAS in the last 26 h`. It's the same test as the
informational health check `nas-backup/recent`. The alert resolves within its 5-minute evaluation.

## If it didn't

- The NAS copy exists but the file on the NAS is readable by everyone (`ls -l` on the NAS shows
  `-rwxrwxrwx`): DSM's ACLs on the folder override the 0600 the script sets. These backups hold
  secrets; restrict the folder in DSM (Shared Folder `homelab`, the backup's folder, permissions:
  no access for everyone but the admin account) and check the next night's copy.
- Restoring from these copies: [Restore the server database](restore-the-server-database.md),
  [Restore the Buckle secrets](restore-the-buckle-secrets.md), [Restore tsidp](restore-tsidp.md),
  [Restore the k3s datastore](restore-the-k3s-datastore.md).

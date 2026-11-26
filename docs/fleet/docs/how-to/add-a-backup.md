# Add a backup

Use this when another database or directory should go to the NAS every night, the way the Buckle
database, its secrets, tsidp and the k3s datastore do. A backup is an entry in
[`vars/backups.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/backups.yaml); the
`nas-backup` module does the rest, and the existing alerts cover it without a change.

**Before you start:** the repo; DSM access on the NAS (or someone who has it) to create the folder;
a tailnet policy change if the host's tag can't reach `svc:nfs` yet.

1. Create the backup's folder on the NAS: DSM, File Station, Shared Folder `homelab`, a new folder
   named after the backup. Give it the same permissions as `buckle`: no access for anyone but the
   admin account (NFS writes as root through the `127.0.0.1` rule).
2. Add the entry:

    ```yaml
    nas_backups:
      - name: my-db              # /var/backups/my-db, files my-db-nightly-<date>.*, metric label
        group: my-group          # hosts in this group run it
        kind: sqlite             # sqlite: a consistent copy of a live database; dir: a tarball
        source: /var/lib/my-app/state.db
        folder: my-db            # the folder from step 1, under /volume1/homelab
        keep_local: 3
        keep_nas: 14
    ```

    A path with spaces won't work: the module writes one line per backup, split on spaces.
3. If `group` is new to backups, add it to the module's `when` in
   [`modules/nas-backup/module.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/nas-backup/module.yaml).
4. If the host's tag isn't `tag:buckle-server` or `tag:k3s-server`, add it to the `tailnet-src`
   of the `nas-backup` Component in
   [`modules/nas-backup/catalog-info.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/nas-backup/catalog-info.yaml):
   Backstage renders the `svc:nfs` grant from it into a policy PR.
5. `mise run validate`, PR, merge. Write a restore page for it next to the others.

## Check it worked

After the rollout, on the host:

```sh
cat /etc/nas-backup/backups
sudo systemctl start nas-backup.service; sudo journalctl -u nas-backup -n 10 --no-pager
```

The new line is in the list, and the run prints `my-db: backed up to /var/backups/my-db/... and
nfs.sphinx-map.ts.net:/volume1/homelab/my-db/...`. In Grafana,
`nas_backup_last_success_timestamp_seconds{backup="my-db"}` has a `local` and a `nas` series.

## If it didn't

- `can't mount ...`: the folder doesn't exist on the NAS or the host can't reach `svc:nfs`
  ([Respond to a backup alert](respond-to-a-backup-alert.md#nas-backup-stale)).
- Nothing ran on the host: its groups don't include `group`, or the module's `when` doesn't.

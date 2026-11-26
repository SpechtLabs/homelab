# Restore the server database

Use this when the Buckle server's database on isa is lost or broken (the server won't start, or
an upgrade went wrong more than seven days ago), or when you rebuild the server on new hardware.

What's in the database: hosts and their per-host state, facts, runs, rollouts, schedules' history,
the audit log, sessions, every host's token: as sensitive as the secrets, root-only wherever it
lies. What isn't: the config (`/etc/buckle/*.yaml`, in `bootstrap/`), the secrets (their own
backup, [Restore the Buckle secrets](restore-the-buckle-secrets.md)) and the revisions (rebuilt
from git).
Losing a night of database only loses history; agents keep enforcing their last applied revision
while the server is down and report their state again when it's back.

**Before you start:** SSH to isa as `cedi`. Pick the copy: `/var/backups/buckle/` on isa (last 3
nights, plus any `buckle-pre-*.db` taken before an upgrade) or the NAS folder `buckle` (last 14
nights). The nightly copies are made by `nas-backup` ([Backups](../reference/backups.md)).

!!! warning "Unverified"
    The procedure is the one the old `buckle-backup.sh` documented (stop, put the copy back as
    `buckle.db`, start), plus setting the WAL files aside. Nobody has restored a backup in this
    homelab yet.

1. List the copies:

    ```sh
    ssh cedi@isa "bash -c 'sudo ls -lt /var/backups/buckle/'"
    ```

    For an older one, mount the NAS folder (and unmount it when you're done):

    ```sh
    ssh cedi@isa "bash -c 'sudo install -d -m 0700 /run/nas-backup/restore && sudo mount -t nfs -o nfsvers=4.1,soft nfs.sphinx-map.ts.net:/volume1/homelab/buckle /run/nas-backup/restore && sudo ls -lt /run/nas-backup/restore | head'"
    ```

2. Stop the server and set the current database aside, with its WAL files (a leftover
   `buckle.db-wal` would be replayed onto the restored file):

    ```sh
    ssh cedi@isa
    bash
    sudo systemctl stop buckle-server
    cd /var/lib/buckle-server
    ts=$(date +%Y%m%d%H%M%S)
    for f in buckle.db buckle.db-wal buckle.db-shm; do sudo test -e "$f" && sudo mv "$f" "$f.broken-$ts"; done
    ```

3. Put the copy in place, root-owned:

    ```sh
    sudo install -m 0644 -o root -g root /var/backups/buckle/buckle-nightly-<date>.db /var/lib/buckle-server/buckle.db
    sudo sqlite3 /var/lib/buckle-server/buckle.db 'PRAGMA integrity_check;'
    ```

    You should see `ok`.
4. Start the server:

    ```sh
    sudo systemctl start buckle-server
    sudo journalctl -u buckle-server -n 50 --no-pager
    ```

5. Sign in again: sessions in the old file belong to the old server run.

## Check it worked

```sh
curl -s https://buckle.sphinx-map.ts.net/readyz
```

answers 200, and within a minute every host is `online` on the Hosts page (or
`curl -s -b "$J" "$B/api/v1/hosts"`). The newest rollout in **Rollouts** is the one from the
backup's night or later; the server picks up commits it missed on its next poll of `main`.

## If it didn't

- The server refuses to start, naming the schema: the copy is from an older Buckle than the one
  installed. Newer versions migrate older schemas on start; a copy from a newer version than the
  binary needs the binary upgraded first ([Upgrade Buckle](upgrade-buckle.md)).
- Hosts stay offline: that's not the database. Check `svc:buckle`
  (`tailscale serve status` on isa) and `journalctl -u buckle-server` for agent errors.
- Rebuilding on another host: [Move the server to another host](move-the-server-to-another-host.md)
  covers the binary, config and Service; restore the database there with steps 2 to 4.

# Restore the Buckle secrets

Use this when files in `/etc/buckle/secrets/` on isa are lost, overwritten or broken (a rollout
fails naming a secret the file provider can't find), or when you rebuild the server. The
`buckle-secrets` backup is a nightly tarball of that directory
([Backups](../reference/backups.md)).

!!! danger "Every secret in one file"
    A `buckle-secrets-nightly-*.tar.gz` holds the K3S token, the NUT passwords, the Argo CD age key
    and Jitsi's secrets in plain text. Keep it root-only: extract it as root into a 0700
    directory, never into your home or `/tmp` with default permissions, never onto your Mac, and
    delete the extract when you're done. The password manager holds the same values.

**Before you start:** SSH to isa as `cedi`. Copies: `/var/backups/buckle-secrets/` (3 nights) or
the NAS folder `buckle-secrets` (14 nights).

1. Pick the copy. The local ones:

    ```sh
    ssh cedi@isa
    bash
    sudo ls -lt /var/backups/buckle-secrets/
    ```

    For an older one, mount the NAS folder:

    ```sh
    sudo install -d -m 0700 /run/nas-backup/restore
    sudo mount -t nfs -o nfsvers=4.1,soft nfs.sphinx-map.ts.net:/volume1/homelab/buckle-secrets /run/nas-backup/restore
    sudo ls -lt /run/nas-backup/restore/
    ```

2. Extract it into a root-only directory:

    ```sh
    sudo install -d -m 0700 /root/secrets-restore
    sudo tar -C /root/secrets-restore -xzf /var/backups/buckle-secrets/buckle-secrets-nightly-<date>.tar.gz
    sudo ls -l /root/secrets-restore/secrets/
    ```

3. Compare with what's there, then put back the files you need (one, or all):

    ```sh
    sudo diff -rq /root/secrets-restore/secrets /etc/buckle/secrets
    sudo install -m 0600 -o root -g root /root/secrets-restore/secrets/<NAME> /etc/buckle/secrets/<NAME>
    ```

4. Clean up:

    ```sh
    sudo rm -rf /root/secrets-restore
    sudo umount /run/nas-backup/restore 2>/dev/null; true
    ```

5. The server reads a secret file on every use, so nothing restarts. Hosts get a restored value
   with the next rollout that plans them; **Rollouts**, **Re-apply…** on the stable revision
   pushes it now.

## Check it worked

```sh
sudo ls -l /etc/buckle/secrets/
```

lists every secret declared under `secrets:` in `buckle.yaml`, each `-rw------- root root`. A
re-apply finishes without a secret error, and the modules that use them (`k3s-*`, `nut-*`,
`argocd-seed`, `jitsi`) stay healthy.

## If it didn't

- A restored value doesn't match the other end any more (a NUT password rotated after the
  backup): take the value from the password manager instead, or rotate both ends
  ([Add or change a secret](add-or-change-a-secret.md)).
- `K3S_TOKEN` must stay the cluster's token: a different one breaks node joins and the
  datastore's encrypted bootstrap data.

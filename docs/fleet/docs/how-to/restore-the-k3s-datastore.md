# Restore the k3s datastore

Use this when labk3s's datastore on clusterpi-leader is lost or corrupt (k3s won't start, the API
answers errors from kine), or when the k3s server's disk is replaced. labk3s runs one k3s server
with SQLite through kine; the `k3s` backup is a nightly consistent copy of
`/var/lib/rancher/k3s/server/db/state.db` ([Backups](../reference/backups.md)).

What comes back: every Kubernetes object as of the backup, and the cluster's bootstrap data (CA
and service-account keys), which k3s keeps in the datastore encrypted with its token. The token
is `K3S_TOKEN` in Buckle's secrets, written into `/etc/rancher/k3s/config.yaml` by
`modules/k3s-server`, so a restored datastore opens with the config Buckle already wrote.

!!! danger "Root-only"
    The datastore holds the cluster's CA keys and every Secret in the cluster.

!!! warning "Unverified"
    Nobody has restored labk3s from this backup yet. The steps are k3s's SQLite restore (stop the
    server, replace `state.db`, start it) adapted to Buckle running the unit.

**Before you start:** SSH to clusterpi-leader as `pi`; the Buckle API or UI. Decide what you lose:
everything created after the backup's time (Argo CD puts git's state back; volumes ceph-csi
provisioned since then lose their PersistentVolume objects while their RBD images stay in Ceph).
The workers keep their pods running while the server is down.

1. Pause clusterpi-leader in Buckle so drift correction doesn't start `k3s` again mid-restore
   (`bpost hosts/clusterpi-leader/pause '{}'`, see
   [Pause a host for manual work](pause-a-host-for-manual-work.md)).
2. Pick the copy: `sudo ls -lt /var/backups/k3s/`, or mount the NAS folder `k3s` as in
   [Restore the Buckle secrets](restore-the-buckle-secrets.md), step 1 (folder `k3s`).
3. Stop the server and set the database aside with its WAL files:

    ```sh
    ssh pi@clusterpi-leader
    bash
    sudo systemctl stop k3s
    cd /var/lib/rancher/k3s/server/db
    ts=$(date +%Y%m%d%H%M%S)
    for f in state.db state.db-wal state.db-shm; do sudo test -e "$f" && sudo mv "$f" "$f.broken-$ts"; done
    ```

4. Put the copy in place and check it:

    ```sh
    sudo install -m 0644 -o root -g root /var/backups/k3s/k3s-nightly-<date>.db /var/lib/rancher/k3s/server/db/state.db
    sudo sqlite3 /var/lib/rancher/k3s/server/db/state.db 'PRAGMA quick_check;'
    ```

    You should see `ok`.
5. Start k3s and resume the host in Buckle:

    ```sh
    sudo systemctl start k3s
    sudo journalctl -u k3s -n 50 --no-pager
    ```

    `bpost hosts/clusterpi-leader/resume '{}'`.

## Check it worked

```sh
KUBECONFIG=~/.kube/configs/labk3s kubectl --context labk3s get nodes
ssh pi@clusterpi-leader "bash -c 'sudo buckle health | grep k3s-server'"
```

All five nodes are `Ready`; `k3s-server/unit`, `kubelet` and `apiserver` pass. Argo CD on labk3s
syncs its apps back to git within minutes.

## If it didn't

- k3s logs that it can't decrypt the bootstrap data: the token differs from the one the backup
  was made with. Restore `K3S_TOKEN` from the same night's `buckle-secrets`
  ([Restore the Buckle secrets](restore-the-buckle-secrets.md)) and let Buckle rewrite
  `config.yaml`.
- Workloads and the cluster itself belong to the
  [labk3s docs](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/).

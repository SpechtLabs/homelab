# Check cluster health

Use this before and after any change to the storage Pis, or when you only want to know whether Ceph is fine.

**Before you start:** SSH to any storage Pi; all three have the admin keyring. Nothing here changes state.

1. The summary:

   ```sh
   ssh pi@storagepi-ceph1
   sudo cephadm shell -- ceph -s
   ```

   A healthy cluster looks like this (2026-11-26):

   ```text
   health: HEALTH_OK
           (muted: AUTH_INSECURE_CLIENT_KEY_TYPE AUTH_INSECURE_KEYS_ALLOWED AUTH_INSECURE_KEYS_CREATABLE)
   mon: 3 daemons, quorum storagepi-ceph1,storagepi-ceph3,storagepi-ceph2
   mgr: storagepi-ceph2.ulrfqs(active, ...), standbys: storagepi-ceph1.qgmutb, storagepi-ceph3.eahkgv
   osd: 3 osds: 3 up, 3 in
   rgw: 1 daemon active (1 hosts, 1 zones)
   pgs: 8 active+clean
   ```

   The three muted checks are deliberate ([Keys and ciphers](../explanation/keys-and-ciphers.md)). Which mgr is active changes over time.
2. Anything that isn't `HEALTH_OK`:

   ```sh
   sudo cephadm shell -- ceph health detail
   ```

3. Every daemon and where it runs:

   ```sh
   sudo cephadm shell -- ceph orch ps
   ```

   16 daemons, all `running`: per host a mon, mgr, OSD, crash and ceph-exporter, plus `rgw.s3.storagepi-ceph2.*`.
4. OSDs and how full they are:

   ```sh
   sudo cephadm shell -- ceph osd tree
   sudo cephadm shell -- ceph osd df
   ```

5. Buckle's view: the `cluster` health check on each Ceph host runs `/usr/local/sbin/ceph-buckle-health` and prints `ok HEALTH_OK` when a rollout may continue. You can run it yourself:

   ```sh
   sudo /usr/local/sbin/ceph-buckle-health
   ```

   It fails on HEALTH_ERR or any of `OSD_DOWN`, `OSD_HOST_DOWN`, `OSD_ROOT_DOWN`, `MON_DOWN`, `PG_DEGRADED`, `PG_AVAILABILITY`, `PG_DAMAGED`, `OSD_FULL`, `POOL_FULL`, `SLOW_OPS`.

From the browser: Grafana's *Ceph - Status* dashboard ([spechtlabs.grafana.net/d/ceph-status](https://spechtlabs.grafana.net/d/ceph-status)) shows the same per host, with timelines of when something stopped.

For labk3s's side:

```sh
kubectl --context labk3s -n ceph-csi-rbd get pods -o wide
```

Two provisioner pods and one node plugin per node (5), all `Running`.

## Running several commands

`cephadm shell` reads stdin. In a script piped over SSH (`ssh host bash -s <<EOF`), it swallows the rest of the heredoc; give each call `</dev/null`. For longer sequences, run them inside one shell:

```sh
sudo cephadm shell -- sh -c 'ceph -s; ceph osd df; ceph orch ps' </dev/null
```

## If something's off

[Respond to a Ceph alert](respond-to-a-ceph-alert.md) has a section per symptom.

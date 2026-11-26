# Upgrade Ceph

Use this to move the cluster to a newer Ceph release (today 20.2.5, Tentacle).

**Before you start:** cephadm upgrades the running cluster, one daemon at a time, from any storage Pi; Buckle doesn't. The version in [`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml) (`ceph_version`, `ceph_cephadm_sha256`) only decides which `cephadm` binary Buckle installs on the hosts and which image a fresh bootstrap would use. Each OSD restart briefly pauses I/O to its PGs; labk3s rides through it. Start outside the nightly window (03:00 to about 07:30, Europe/Berlin): Buckle's `cluster` health check fails while OSDs restart, and a nightly rollout would pause on it.

1. Check the cluster is `HEALTH_OK` ([Check cluster health](check-cluster-health.md)).
2. Read the release notes for the target version, then check it:

   ```sh
   sudo cephadm shell -- ceph orch upgrade check --image quay.io/ceph/ceph:vX.Y.Z
   ```

3. Start it:

   ```sh
   sudo cephadm shell -- ceph orch upgrade start --image quay.io/ceph/ceph:vX.Y.Z
   ```

4. Follow it until it's done:

   ```sh
   sudo cephadm shell -- ceph orch upgrade status
   sudo cephadm shell -- ceph -s
   ```

   To hold it: `ceph orch upgrade pause` and `ceph orch upgrade resume`; to give up, `ceph orch upgrade stop`.
5. Bump the repo to match. Set `ceph_version` and compute the checksum of the matching cephadm (download.ceph.com publishes none):

   ```sh
   curl -sL https://download.ceph.com/rpm-X.Y.Z/el9/noarch/cephadm | shasum -a 256
   ```

   ```yaml
   ceph_version: X.Y.Z
   ceph_cephadm_sha256: <sha256>
   ```

   Push to `main`. The rollout downloads the new `/usr/local/sbin/cephadm` to each Ceph host, one host at a time.

## Check it worked

```sh
sudo cephadm shell -- ceph versions
```

Every daemon (`mon`, `mgr`, `osd`, `rgw`, `overall`) reports the new version, and `ceph -s` is back to `HEALTH_OK`.

## If it didn't

- `ceph orch upgrade status` shows an error, or the upgrade stalls: `ceph health detail` usually names the daemon it waits for (`UPGRADE_*` checks). Fix that daemon ([Restart a daemon](restart-a-daemon.md)), then `ceph orch upgrade resume`.
- The ceph-mixin dashboards in k8s-deployment (`components/grafana-dashboards/ceph`) come from the mixin at v20.2.5. Metric names rarely change within a release line, but after a major upgrade compare them with the new version's `monitoring/ceph-mixin/dashboards_out`.

!!! warning "Unverified"
    No upgrade has run on this cluster yet; it was bootstrapped on 20.2.5. The commands above exist in this release's CLI. ceph-csi (3.18.2) upgrades separately, in k8s-deployment `apps/ceph-csi-rbd/cluster/labk3s/kustomization.yaml` (`helmCharts[].version`, with the chart vendored under `charts/`); check ceph-csi's support matrix before a major Ceph upgrade.

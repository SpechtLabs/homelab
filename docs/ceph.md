# Ceph on the storage Pis

Status: running since 2026-11-19 · Ceph 20.2.5 (Tentacle) · ceph-csi 3.18.2

Three Raspberry Pi 5 (8 GB) with a 1 TB WD SN770 each: `storagepi-ceph1..3`. One OSD per host,
three monitors, three mgrs (one active), one S3 gateway. Pools are replicated three times, so
usable space is about 860 GB. labk3s uses it for volumes (StorageClass `ceph-rbd`), and there is
an S3 endpoint for experiments.

## Who owns what

| Layer | Owner | Where |
|---|---|---|
| Disk split (root 64 GiB, `nvme0n1p3` for the OSD) | Buckle, once | `modules/ceph-disk` |
| Host: lvm2, Docker, cephadm, sshd :2222, LV `ceph/osd`, tailnet route | Buckle | `modules/ceph` |
| Cluster bootstrap | Buckle action `bootstrap` on `ceph_admin_host`, once | `modules/ceph/files/ceph-bootstrap.j2` |
| Desired state: hosts, mon, mgr, OSD, ceph-exporter, RGW | Buckle applies, cephadm reconciles | `modules/ceph/files/cluster.yaml.j2`, `vars/group-ceph.yaml` |
| Mon settings, health mutes, mgr modules, config, pools, client keys, S3 users | Buckle | `modules/ceph/files/resources.sh.j2`, `vars/group-ceph.yaml` |
| Daemons, containers, placement, restarts, upgrades | cephadm | `ceph orch …` |
| ceph-csi, StorageClass, client secret | Argo CD | SpechtLabs/k8s-deployment `apps/ceph-csi-rbd` |
| Dashboards and alerts | grafana-operator | k8s-deployment `components/grafana-dashboards/ceph`, `grafanaalertrules-ceph.yaml` |

The cluster spec and the resources script are applied whenever their rendered file changes,
through `/usr/local/sbin/ceph-buckle-apply`. Removing something from either removes nothing from
the cluster; `ceph orch rm` or `ceph … rm` do.

## Decisions worth knowing

- **Everything is on the tailnet.** `public_network = 100.64.0.0/10`; the mons sit at the hosts'
  tailnet addresses, which stay fixed while the Tailscale node exists. A mon whose address changes
  won't start, so re-enrolling a host in Tailscale means re-adding its mon. Measured cost of
  WireGuard: 878 vs 933 Mbit/s on the LAN.
- **cephadm can't see tailnet addresses.** `cephadm list-networks` reads only the main routing
  table; Tailscale's routes live in table 52. `ceph-tailnet-route.service` adds a main-table route
  for each host's own tailnet address (it never carries a packet; the local table answers first).
  Without it, mons can't be placed. After a change, `ceph orch device ls --refresh` makes cephadm
  look again.
- **cephadm uses sshd on port 2222.** Tailscale SSH answers port 22 on the tailnet address.
  root accepts only cephadm's key (`ceph_cephadm_pubkey`), and only from tailnet addresses.
- **4K-page kernel (`kernel8.img`).** On the Pi 5's default 16K-page kernel, BlueStore asserts
  while creating an OSD (`BlueFS::append_try_flush`). `rpi_kernel` in `vars/group-ceph.yaml`.
- **The OSD sits on an LV.** ceph-volume refuses partitions, so Buckle puts LV `ceph/osd` on
  `nvme0n1p3`. A failed OSD creation makes ceph-volume wipe that LV; Buckle recreates it.
- **`client.k3s` has an AES-128 key.** Tentacle issues `aes256k` keys; the k3s nodes' kernel rbd
  (6.6 and 6.12) can't parse them (`libceph: Failed to parse secret: -524`). `aes` is allowed in
  the monmap next to `aes256k` (still preferred), and the three warnings about it are muted
  (`ceph_health_mutes`). A second `aes` client would go unnoticed. Buckle creates a client's key
  with its `key_type` but never rotates one: a key of the wrong type fails the `resources` step,
  which prints the `ceph auth rotate` command to run by hand once ceph-csi's secret can follow.
- **ceph-csi lists the mons by IP.** labk3s's CoreDNS sends `*.ts.net` to the Tailscale
  operator's nameserver, which doesn't know the storage Pis. Pods reach the tailnet through the
  node.

## Monitoring

- **Metrics**, all in the homelab Mimir tenant: each storage Pi's Alloy scrapes the mgr (`:9283`,
  job `ceph_mgr`) and `ceph-exporter` (`:9926`, job `ceph_exporter`), labelled
  `cluster=homelab-ceph` (the mgr's prometheus module is on through `ceph_mgr_modules`, since
  `--skip-monitoring-stack` leaves it off; standby mgrs answer `/metrics` with an empty body). On labk3s, k8s-monitoring scrapes ceph-csi through pod annotations (jobs
  `ceph-csi-rbd/nodeplugin` and `ceph-csi-rbd/provisioner`), plus kubelet volume stats.
- **Dashboards** in Grafana under Infrastructure › Ceph: the ceph-mixin set (cluster, hosts, OSDs,
  pools, RBD, RGW) and *Ceph CSI (RBD)*, which k8s-deployment generates with
  `hack/gen-ceph-csi-dashboard.py`.
- **Alerts** (group `ceph-health`, same folder): HEALTH_ERR, long HEALTH_WARN, no cluster
  metrics, OSD down, PGs inactive, mon out of quorum, OSD over 75% full, no CSI provisioner, a
  node without a CSI node plugin, failing CSI operations, and a PVC over 85% full.

## Day to day

Run the Ceph CLI on any of the three hosts (each has the admin keyring):

```sh
sudo cephadm shell -- ceph -s
sudo cephadm shell -- ceph health detail
```

- **S3:** `http://storagepi-ceph2.sphinx-map.ts.net:7480`, user `experiments`. To get its keys:
  `sudo cephadm shell -- radosgw-admin user info --uid=experiments`. To add more users, add them
  to `ceph_rgw_users`.
- **Mgr dashboard:** `https://100.105.212.35:8443` (the active mgr), user `admin`. The bootstrap
  action's output has the initial password. To set a new one:
  `sudo cephadm shell -- ceph dashboard ac-user-set-password admin -i <file>`.
- **A volume for labk3s:** use a PVC with `storageClassName: ceph-rbd`. It expands online.
- **Upgrade Ceph:** `sudo cephadm shell -- ceph orch upgrade start --image quay.io/ceph/ceph:vX.Y.Z`.
  Then bump `ceph_version` and `ceph_cephadm_sha256` in `vars/versions.yaml`; they only matter for
  bootstrap and `cephadm shell`.
- **Add a host:** split its disk (`ceph-disk`, action *Split the NVMe for Ceph*), match it with
  the `ceph` group, add it with its tailnet IPv4 to `ceph_hosts`. Buckle installs cephadm's key,
  the route and the LV. The spec change adds it, and cephadm puts a mon, mgr and OSD on it.

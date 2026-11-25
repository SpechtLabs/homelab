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
- **cephadm's daemons restart always, not only on failure.** A Docker restart (the nightly
  `base/upgrade` installing a new docker-ce) stops every container with SIGTERM; the daemons exit
  0 and cephadm's `Restart=on-failure` left them down: storagepi-ceph1 lost mon, mgr and OSD for
  7 h on 2026-11-25. Buckle adds a drop-in, `ceph-<fsid>@.service.d/buckle-restart.conf`, with
  `Restart=always`; `systemctl stop` (what `ceph orch daemon stop` uses) still stops for good.
- **ceph-csi lists the mons by IP.** labk3s's CoreDNS sends `*.ts.net` to the Tailscale
  operator's nameserver, which doesn't know the storage Pis. Pods reach the tailnet through the
  node.

## Monitoring

- **Metrics**, all in the homelab Mimir tenant: each storage Pi's Alloy scrapes the mgr (`:9283`,
  job `ceph_mgr`) and `ceph-exporter` (`:9926`, job `ceph_exporter`), labelled
  `cluster=homelab-ceph` (the mgr's prometheus module is on through `ceph_mgr_modules`, since
  `--skip-monitoring-stack` leaves it off; standby mgrs answer `/metrics` with an empty body). On labk3s, k8s-monitoring scrapes ceph-csi through pod annotations (jobs
  `ceph-csi-rbd/nodeplugin` and `ceph-csi-rbd/provisioner`), plus kubelet volume stats.
- **Dashboards** in Grafana under Infrastructure › Ceph. Start at *Ceph - Status*: one row per
  host (daemons running, OSD up, mon in quorum, exporters scraped), the active health checks, every
  daemon by host, and timelines of when each stopped. Then the ceph-mixin set (cluster, hosts,
  OSDs, pools, RBD, RGW) and *Ceph CSI (RBD)*. k8s-deployment generates the two non-mixin ones
  (`hack/gen-ceph-status-dashboard.py`, `hack/gen-ceph-csi-dashboard.py`).
- **Alerts** (group `ceph-health`, same folder), one instance per daemon, OSD, mon or health check,
  with its host in the title: a health check at HEALTH_ERR, or at HEALTH_WARN for 30 min (muted
  checks left out by name, so a new `ceph_health_mutes` entry goes there too), no cluster metrics,
  an OSD down, a mon out of quorum, a cephadm daemon not running, PGs inactive, an OSD over 75%
  full; for ceph-csi: no provisioner, a node without a node plugin, failing operations, a PVC over
  85% full. Each links to *Ceph - Status* and to the section below.

## When an alert fires

Open *Ceph - Status*. The Hosts table says where; the alerts say it too.

- **Several daemons on one host not running**, mon and OSD with them: that host's daemons
  stopped together, almost always Docker restarting (an upgrade) or the host rebooting.
  `ssh <host> systemctl list-units 'ceph-*'` shows them; since 2026-11-25 systemd restarts them
  by itself (`buckle-restart.conf`), so look at `journalctl -u docker` and the units' journals
  for why they didn't come back. To start them:
  `sudo systemctl start ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@<daemon>` on the host, or
  `sudo cephadm shell -- ceph orch daemon start <daemon>` from any of them.
- **The host's exporters aren't scraped and nothing else from it changes**: the host is down or
  off the tailnet. Its OSD and mon alerts come from the other hosts' view.
- **An OSD is down but its daemon runs**: it can't reach the others. Its log:
  `sudo cephadm logs --name osd.<n>` on the host.
- **A health check** without a daemon or host behind it: `sudo cephadm shell -- ceph health
  detail` names the PGs or daemons. PG_DEGRADED and undersized PGs after an OSD came back
  recover by themselves; watch `ceph -s`.

Buckle won't touch the next Ceph host while the `cluster` health check fails, so a stuck host
also stops the nightly upgrades and reboots there.

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

# Hosts and daemons

Cluster `homelab-ceph`, fsid `85412c6c-e39c-11f1-ba59-2ccf678b0944`, Ceph 20.2.5 (Tentacle). Bootstrapped 2026-11-18 on storagepi-ceph1.

## Hosts

| Host | Tailnet IPv4 | OSD | Also runs |
|---|---|---|---|
| storagepi-ceph1 | 100.105.212.35 | osd.0 | cephadm admin host (`ceph_admin_host`): bootstrap, specs, resources |
| storagepi-ceph2 | 100.107.71.68 | osd.2 | RGW `rgw.s3.storagepi-ceph2.eyscmw` |
| storagepi-ceph3 | 100.118.224.54 | osd.1 | |

Hardware: Raspberry Pi 5 (8 GB), 1 TB WD SN770 NVMe on PCIe Gen 2 (`rpi_pciex1_gen`). MagicDNS names: `storagepi-cephN.sphinx-map.ts.net`. Tailnet tag `tag:ceph`.

Sources of truth: addresses in `ceph_hosts` ([`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml)); OSD ids from `ceph osd tree`; Backstage resources in [`catalog/hardware.yaml`](https://github.com/SpechtLabs/homelab/blob/main/catalog/hardware.yaml). Buckle puts a host in group `ceph` when its id matches `storagepi-ceph*` ([`buckle.yaml`](https://github.com/SpechtLabs/homelab/blob/main/buckle.yaml)).

All three hosts carry the cephadm labels `_admin, mon, mgr, osd`, so each has `/etc/ceph/ceph.conf` and the admin keyring and can run the Ceph CLI.

## Daemons per host

| Daemon | Name pattern | Placement (spec) | Notes |
|---|---|---|---|
| mon | `mon.<host>` | every host in `ceph_hosts`, at its tailnet IP | quorum needs 2 of 3 |
| mgr | `mgr.<host>.<random>` | label `mgr` | one active, two standby |
| osd | `osd.<id>` | label `osd`, service `osd.nvme`, device `/dev/ceph/osd` | one per host, 867 GiB |
| crash | `crash.<host>` | every host (cephadm default) | |
| ceph-exporter | `ceph-exporter.<host>` | `host_pattern: '*'` | per-daemon perf counters |
| rgw | `rgw.s3.<host>.<random>` | `ceph_rgw_hosts`: storagepi-ceph2 | port 7480 |

`ceph orch ps` lists them; 16 in total. The mgr suffixes on 2026-11-26: `storagepi-ceph1.qgmutb`, `storagepi-ceph2.ulrfqs`, `storagepi-ceph3.eahkgv`.

## Systemd units and containers

| Unit | What |
|---|---|
| `ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@<daemon>.service` | one per daemon, runs its Docker container (cephadm-generated, `Restart=on-failure`) |
| `ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944@.service.d/buckle-restart.conf` | Buckle's drop-in: `Restart=always` |
| `ceph-85412c6c-e39c-11f1-ba59-2ccf678b0944.target` | the cluster's target |
| `ceph-tailnet-route.service` | main-table route for the host's own tailnet address (Buckle) |
| `docker.service` | runs every daemon's container |

Logs: `sudo cephadm logs --name <daemon>` (journalctl underneath; extra journalctl args after `--`).

## Disk layout

```text
nvme0n1        931.5G
├─nvme0n1p1      512M  /boot/firmware
├─nvme0n1p2       64G  /          (ext4: OS, container images, mon store)
└─nvme0n1p3      867G
  └─ceph-osd     867G  LV ceph/osd -> the OSD (BlueStore)
```

Raw capacity 2.5 TiB; three copies, so roughly 860 GB usable.

## Cluster settings

What the cluster reported on 2026-11-26. The first three come from bootstrap ([`bootstrap.conf.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/files/bootstrap.conf.j2)) and live in the config database since; changing that file changes nothing now.

| Setting | Value |
|---|---|
| `public_network` | `100.64.0.0/10` |
| `osd_pool_default_size` | 3 |
| `osd_pool_default_min_size` | 2 |
| `ms_bind_port_max` | 7568 |
| `mon_osd_down_out_interval` | 600 s |
| full ratios | nearfull 0.85, backfillfull 0.90, full 0.95 |
| `mon_allow_pool_delete` | false |

Set by Buckle from `ceph_config`: `osd_memory_target_autotune false`, `osd_memory_target 2147483648` (2 GiB), `mgr/prometheus/standby_behaviour error`, `mgr/prometheus/rbd_stats_pools k3s`.

Bootstrap ran with `--skip-monitoring-stack` (no cephadm Prometheus, Grafana or Alertmanager), `--skip-mon-network`, `--ssh-user root` and cephadm's SSH config on port 2222.

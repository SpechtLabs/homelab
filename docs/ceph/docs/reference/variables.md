# Variables

Where each Ceph setting comes from. Group values live in [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml) (loaded for hosts in group `ceph`), versions in [`vars/versions.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/versions.yaml), module defaults in [`modules/ceph/module.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/module.yaml). The file is the source of truth; the values below are from 2026-11-26.

## vars/group-ceph.yaml

| Var | Value | Effect |
|---|---|---|
| `rpi_kernel` | `kernel8.img` | the Pi 5 boots the 4K-page kernel (module `pi-firmware`); BlueStore breaks on 16K pages |
| `ceph_admin_host` | `storagepi-ceph1` | where bootstrap ran and where Buckle applies specs and resources |
| `ceph_fsid` | `85412c6c-e39c-11f1-ba59-2ccf678b0944` | names the systemd units; gates the restart drop-in |
| `ceph_hosts` | host: tailnet IPv4, for all three | host specs, mon placement (`host:ip`), `ceph-tailnet-route`, bootstrap's `--mon-ip`. Every host in group `ceph` must be listed |
| `ceph_rgw_hosts` | `[storagepi-ceph2]` | RGW placement; empty list drops the RGW spec |
| `ceph_mon_settings` | `auth_allowed_ciphers: aes,aes256k` | `ceph mon set <key> <value>` |
| `ceph_health_mutes` | `AUTH_INSECURE_CLIENT_KEY_TYPE`, `AUTH_INSECURE_KEYS_ALLOWED`, `AUTH_INSECURE_KEYS_CREATABLE` | `ceph health mute <code> --sticky`; keep in step with the HEALTH_WARN rule and the status dashboard |
| `ceph_mgr_modules` | `[prometheus]` | `ceph mgr module enable` |
| `ceph_config` | mgr: `mgr/prometheus/standby_behaviour: error`, `mgr/prometheus/rbd_stats_pools: k3s`; osd: `osd_memory_target_autotune: 'false'`, `osd_memory_target: '2147483648'` | `ceph config set <who> <key> <value>` |
| `o11y_local_scrapes` | `rpi_exporter` :9243; `ceph_mgr` :9283 (`cluster: homelab-ceph`, `honor_labels`); `ceph_exporter` :9926 (`cluster: homelab-ceph`) | what Alloy scrapes on each host (module `alloy`) |
| `ceph_rbd_pools` | `[k3s]` | `ceph osd pool create`, `rbd pool init` |
| `ceph_clients` | `k3s`: `key_type: aes`, caps mon/osd/mgr `profile rbd` (pool `k3s`) | `ceph auth get-or-create --key_type`, `ceph auth caps`; never rotates |
| `ceph_rgw_users` | `experiments: S3 experiments` | `radosgw-admin user create` |
| `ceph_cephadm_pubkey` | cephadm's ed25519 key (`ceph cephadm get-pub-key`) | root's `authorized_keys` on every Ceph host, with `from="100.64.0.0/10"` |

## vars/versions.yaml

| Var | Value | Effect |
|---|---|---|
| `ceph_version` | `20.2.5` | `cephadm` download URL (`download.ceph.com/rpm-<version>/el9/noarch/cephadm`) and `ceph_image` |
| `ceph_cephadm_sha256` | checksum of that cephadm | the download's checksum; bump with the version |

A running cluster upgrades through `ceph orch upgrade`, not through these ([Upgrade Ceph](../how-to/upgrade-ceph.md)).

## Module defaults (modules/ceph)

| Var | Value |
|---|---|
| `ceph_image` | `quay.io/ceph/ceph:v{{ ceph_version }}` |
| `ceph_public_network` | `100.64.0.0/10` |
| `ceph_osd_partition` | `/dev/nvme0n1p3` |
| `ceph_osd_vg` / `ceph_osd_lv` | `ceph` / `osd` |
| `ceph_rgw_port` | `7480` |

## Module defaults (modules/ceph-disk)

| Var | Value |
|---|---|
| `ceph_root_size` | `64G`: root after the split; the rest becomes `nvme0n1p3`. 10-15 GB were in use when the Pis were split |

Also read by the module: `tailnet` (`sphinx-map.ts.net`, [`vars/defaults.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/defaults.yaml)) for the hosts' addresses in the spec.

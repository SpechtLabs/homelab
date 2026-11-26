# Buckle module

Two modules, both for hosts in group `ceph` (`host.id like "storagepi-ceph*"`).

## modules/ceph

[`modules/ceph/module.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/module.yaml). Needs `base` and `tailscale`. `parallel: 1`: the limit counts any change on a Ceph host, whichever module causes it, so rollouts and the nightly runs touch one Ceph host at a time.

### Tasks, in order

| What | Where it ends up |
|---|---|
| lvm2 | package |
| Docker enabled and running | `docker.service` |
| Restart drop-in (when `ceph_fsid` is set) | `/etc/systemd/system/ceph-<fsid>@.service.d/buckle-restart.conf` (`Restart=always`) |
| cephadm, checksum-verified | `/usr/local/sbin/cephadm` |
| LV over the OSD partition, only on a blank partition, never undone | VG `ceph`, LV `osd` on `/dev/nvme0n1p3` |
| sshd also on 2222, root only there | `/etc/ssh/sshd_config.d/cephadm.conf` |
| cephadm's key for root, from tailnet addresses only | root's `authorized_keys` |
| Main-table route for the host's own tailnet IP | `/etc/systemd/system/ceph-tailnet-route.service` |
| Health script (every host) | `/usr/local/sbin/ceph-buckle-health` |
| Admin host only: bootstrap config, cephadm SSH config, bootstrap script | `/etc/ceph/buckle/bootstrap.conf`, `/etc/ceph/buckle/ssh_config`, `/usr/local/sbin/ceph-bootstrap` |
| Admin host only: apply script | `/usr/local/sbin/ceph-buckle-apply` |
| Admin host only: orchestrator specs | `/etc/ceph/buckle/cluster.yaml`, applied with `ceph orch apply -i`, copy in `cluster.applied.yaml` |
| Admin host only: resources script | `/etc/ceph/buckle/resources.sh`, run in `cephadm shell`, copy in `resources.applied.sh` |

`ceph-buckle-apply cluster|resources` applies the file only if it differs from its `.applied` copy and the admin keyring exists, then records it. Handlers run specs before resources. Neither step ever removes anything: dropping a service from the spec needs `ceph orch rm <service>`, dropping a pool or client needs `ceph ... rm`.

### Action

| Action | Name in the UI | What it does |
|---|---|---|
| `bootstrap` | Bootstrap the Ceph cluster | runs `/usr/local/sbin/ceph-bootstrap` once (skipped if `/etc/ceph/ceph.conf` exists; asks for confirmation); prints cephadm's public key for `ceph_cephadm_pubkey` |

The cluster exists; you'd only run this for a new cluster on an empty admin host.

### Health checks

| Check | Passes when |
|---|---|
| `tailnet-route` | `ip route show table main dev tailscale0` has a `scope link src 100.` route |
| `cluster` | `ceph-buckle-health` prints `ok`: not HEALTH_ERR, and none of `OSD_DOWN`, `OSD_HOST_DOWN`, `OSD_ROOT_DOWN`, `MON_DOWN`, `PG_DEGRADED`, `PG_AVAILABILITY`, `PG_DAMAGED`, `OSD_FULL`, `POOL_FULL`, `SLOW_OPS`. Passes with "ok (no cluster yet)" before bootstrap |

`cluster` is the gate between Ceph hosts in a rollout: a reboot of one host doesn't count as done until the cluster has recovered. If recovery outlasts the rollout's 2-minute `settle`, the rollout pauses (`on_failure: pause`).

## modules/ceph-disk

[`modules/ceph-disk/module.yaml`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph-disk/module.yaml). Installs an initramfs hook and a local-premount script that split the NVMe, but they do nothing unless `shrinkroot=<N>G` is on the kernel command line.

| Action | Name in the UI | What it does |
|---|---|---|
| `shrink-root` | Split the NVMe for Ceph | `shrinkroot-arm 64G`: checks the initramfs carries the script and tools and that root fits in half of 64G, adds `shrinkroot=64G` to `cmdline.txt`, reboots (asks for confirmation; skipped if `nvme0n1p3` exists) |

On the next boot the premount script takes the token off `cmdline.txt` first (so it runs at most once), shrinks the ext4, shrinks partition 2 to 64 GiB, appends partition 3 and grows the ext4 back. Any surprise stops it and the host boots normally. Log: `/boot/firmware/shrinkroot.log`.

| File on the host | |
|---|---|
| `/etc/initramfs-tools/hooks/shrinkroot` | copies e2fsck, resize2fs, dumpe2fs, sfdisk into the initramfs |
| `/etc/initramfs-tools/scripts/local-premount/shrinkroot` | the split |
| `/usr/local/sbin/shrinkroot-arm` | arms it; `--done` exits 0 once split |

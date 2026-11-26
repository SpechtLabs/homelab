# Ceph

`homelab-ceph` is a three-node Ceph cluster on the storage Pis, `storagepi-ceph1..3`: Raspberry Pi 5 (8 GB) boards with a 1 TB WD SN770 NVMe each. Ceph 20 (Tentacle) runs in containers under cephadm, and every byte of Ceph traffic goes over the tailnet. Running since 2026-11-19.

Each host runs one mon, one mgr (one active, two standby), one OSD on the NVMe's third partition, a crash collector and ceph-exporter. storagepi-ceph2 also runs the S3 gateway (RGW). Pools keep three copies with `min_size` 2, so the raw 2.5 TiB gives about 860 GB usable, and the cluster keeps serving I/O with one host down.

Two things use it:

- **labk3s volumes.** ceph-csi (RBD) on labk3s maps images from pool `k3s` as `client.k3s`, through StorageClass `ceph-rbd`.
- **S3 for experiments** at `http://storagepi-ceph2.sphinx-map.ts.net:7480`, user `experiments`.

## Who owns what

| Layer | Owner | Where |
|---|---|---|
| Disk split (root 64 GiB, `nvme0n1p3` for the OSD) | Buckle, once per host | [`modules/ceph-disk`](https://github.com/SpechtLabs/homelab/tree/main/modules/ceph-disk) |
| Host prep: lvm2, Docker, cephadm, sshd on 2222, LV `ceph/osd`, tailnet route, restart drop-in | Buckle | [`modules/ceph`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/module.yaml) |
| Cluster bootstrap | Buckle action `bootstrap`, once, on `storagepi-ceph1` | [`ceph-bootstrap.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/files/ceph-bootstrap.j2) |
| Desired state: hosts, mon, mgr, OSD, ceph-exporter, RGW | Buckle applies the spec, cephadm reconciles | [`cluster.yaml.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/files/cluster.yaml.j2), [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml) |
| Mon settings, health mutes, mgr modules, config, pools, client keys, S3 users | Buckle | [`resources.sh.j2`](https://github.com/SpechtLabs/homelab/blob/main/modules/ceph/files/resources.sh.j2), [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml) |
| Daemons, containers, placement, upgrades | cephadm | `ceph orch ...` |
| ceph-csi, StorageClass, client secret | Argo CD on labk3s | SpechtLabs/k8s-deployment [`apps/ceph-csi-rbd/cluster/labk3s`](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/ceph-csi-rbd/cluster/labk3s) |
| Dashboards and alerts | grafana-operator | k8s-deployment [`components/grafana-dashboards/ceph`](https://github.com/SpechtLabs/k8s-deployment/tree/main/components/grafana-dashboards/ceph), [`grafanaalertrules-ceph.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/grafana-operator/cluster/specht-labs/grafanaalertrules-ceph.yaml) |

## Where to start

- An alert fired: [Respond to a Ceph alert](how-to/respond-to-a-ceph-alert.md), with Grafana's *Ceph - Status* dashboard open (Infrastructure > Ceph).
- You want to know if the cluster is fine: [Check cluster health](how-to/check-cluster-health.md).
- A host needs a reboot or hardware work: [Take a host down for maintenance](how-to/take-a-host-down-for-maintenance.md).
- You need a fact (an address, a port, a var): [Reference](reference/index.md).
- You want to know why it's built like this: [Explanation](explanation/index.md).

All task recipes are in [How-to guides](how-to/index.md).

## Related systems

- [Fleet](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/): Buckle, rollouts, actions, the nightly upgrades that reboot the storage Pis.
- [Tailnet](https://backstage.k8s.specht-labs.de/docs/default/system/tailnet/): the policy that carries `tag:ceph` and `tag:ceph-client`.
- [labk3s](https://backstage.k8s.specht-labs.de/docs/default/system/labk3s/): the cluster that consumes the RBD pool.
- [Timekeeping](https://backstage.k8s.specht-labs.de/docs/default/system/timekeeping/): the mons refuse quorum on clock skew.

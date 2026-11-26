# Pools, clients and S3 users

What Buckle creates comes from [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml); the rest Ceph made itself. Live list: `sudo cephadm shell -- ceph osd pool ls detail`.

## Pools

Every pool: replicated, size 3, `min_size` 2, CRUSH rule 0, PG autoscaler on (1 PG each on 2026-11-26).

| Pool | Application | Made by |
|---|---|---|
| `k3s` | rbd | Buckle (`ceph_rbd_pools`): labk3s's volumes |
| `.mgr` | mgr | Ceph |
| `.rgw.root`, `default.rgw.log`, `default.rgw.control`, `default.rgw.meta`, `default.rgw.buckets.index`, `default.rgw.buckets.data` | rgw | RGW, on first use |

## Clients

| Entity | Key type | Caps | Used by |
|---|---|---|---|
| `client.k3s` | `aes` (AES-128, key starts `AQ`) | mon `profile rbd`; osd `profile rbd pool=k3s`; mgr `profile rbd pool=k3s` | ceph-csi on labk3s, secret `csi-rbd-secret` in namespace `ceph-csi-rbd` (SOPS: k8s-deployment [`csi-rbd.secret.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/ceph-csi-rbd/cluster/labk3s/csi-rbd.secret.yaml)) |
| `client.admin` | `aes256k` | all | the Ceph CLI on the three hosts (`/etc/ceph/ceph.client.admin.keyring`) |

cephadm made the rest itself: `client.bootstrap-*`, `client.crash.<host>`, `client.ceph-exporter.<host>`, `client.rgw.s3.<daemon>`. `ceph auth ls` lists them.

Mon cipher settings (`ceph mon dump`): `auth_allowed_ciphers aes, aes256k`, `auth_preferred_cipher aes256k`, `auth_service_cipher aes256k`. The first comes from `ceph_mon_settings`.

## RBD on labk3s

| Thing | Value |
|---|---|
| StorageClass | `ceph-rbd` (provisioner `rbd.csi.ceph.com`, not the default class) |
| Pool | `k3s` |
| clusterID | `85412c6c-e39c-11f1-ba59-2ccf678b0944` |
| Image features | `layering,exclusive-lock,object-map,fast-diff` |
| Filesystem | ext4, mounted with `discard` |
| Reclaim policy | Delete |
| Volume expansion | allowed, online |
| Volume binding | Immediate |
| ceph-csi | 3.18.2, namespace `ceph-csi-rbd`, Argo CD app `ceph-csi-rbd` on labk3s; 2 provisioner replicas, a node plugin per node; no snapshotter (labk3s has no VolumeSnapshot CRDs) |

Config: k8s-deployment [`apps/ceph-csi-rbd/cluster/labk3s/helm-values.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/ceph-csi-rbd/cluster/labk3s/helm-values.yaml).

## S3 (RGW)

| Thing | Value |
|---|---|
| Endpoint | `http://storagepi-ceph2.sphinx-map.ts.net:7480` |
| Service | `rgw.s3`, on `ceph_rgw_hosts` (storagepi-ceph2) |
| Users | `experiments` (Buckle, `ceph_rgw_users`); `dashboard` (made by the mgr dashboard) |
| Keys | `sudo cephadm shell -- radosgw-admin user info --uid=<uid>` |
| Backstage | API `ceph-s3`, lifecycle `experimental` |

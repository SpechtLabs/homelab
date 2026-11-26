# Give a Kubernetes cluster RBD access

Use this when a Kubernetes cluster other than labk3s should get persistent volumes from Ceph. labk3s's setup is the template: SpechtLabs/k8s-deployment [`apps/ceph-csi-rbd/cluster/labk3s`](https://github.com/SpechtLabs/k8s-deployment/tree/main/apps/ceph-csi-rbd/cluster/labk3s).

**Before you start:** the cluster's nodes must be on the tailnet: Ceph listens only on the storage Pis' 100.x addresses, and clients talk to every OSD directly, so there's no Tailscale Service to point at. You need admin rights in the Tailscale console and both repos checked out.

1. **Pool and client.** Give the cluster its own pool and client in [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml), following [Add a pool and a client key](add-a-pool-and-a-client-key.md). If the nodes map images with the kernel (ceph-csi's default) and run a kernel like the Pis' 6.6 or 6.12, use `key_type: aes`.
2. **Tailnet.** Tag every node `tag:ceph-client` in the Tailscale admin console. That tag already reaches `tag:ceph` on the mon and OSD ports (tcp 3300, 6789, 6800-7479, 7481-7568), so the policy needs no new grant. For Backstage's picture, add the nodes to `appliesTo` of `tag-ceph-client` in [`tailscale/policy/tags.yaml`](https://github.com/SpechtLabs/homelab/blob/main/tailscale/policy/tags.yaml).
3. **ceph-csi.** In k8s-deployment, copy `apps/ceph-csi-rbd/cluster/labk3s` to `apps/ceph-csi-rbd/cluster/<cluster>` and add an Argo CD Application like [`argo-apps/labk3s/ceph-csi-rbd.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/argo-apps/labk3s/ceph-csi-rbd.yaml). In `helm-values.yaml`:
    - `csiConfig`: keep `clusterID: 85412c6c-e39c-11f1-ba59-2ccf678b0944` and the three monitors **by IP** (`100.105.212.35:6789`, `100.107.71.68:6789`, `100.118.224.54:6789`). labk3s's CoreDNS sends `*.ts.net` to the Tailscale operator's nameserver, which doesn't know the storage Pis; check your cluster's DNS before you switch to names.
    - `storageClass.pool`: the new pool. Keep `imageFeatures: layering,exclusive-lock,object-map,fast-diff` unless the nodes' kernel supports more.
    - Drop the `podAnnotations` or change them to match the cluster's monitoring.
4. **Secret.** Write `csi-rbd.secret.yaml` with `userID` (the client name without `client.`) and `userKey` (`ceph auth get-key client.<name>`), and encrypt it with SOPS; k8s-deployment's `.sops.yaml` covers `apps/*/*secret.yaml`.
5. **Snapshots.** Keep `no-snapshotter.patch.yaml` unless the cluster has the VolumeSnapshot CRDs and a snapshot-controller.
6. **Catalog.** Give the new app's `catalog-info.yaml` `consumesApis: [api:ceph-rbd]` and `specht-labs.de/tailnet-src: tag:ceph-client`, like labk3s's.

## Check it worked

Create a small test PVC with `storageClassName: <the new class>` and a pod that mounts it.

```sh
kubectl -n ceph-csi-rbd get pods
kubectl get pvc <test-pvc>
```

The PVC is `Bound`, the pod `Running`. On a storage Pi, `sudo cephadm shell -- rbd ls <pool>` lists the new image.

## If it didn't

- PVC stays Pending: the provisioner's log (`kubectl -n ceph-csi-rbd logs deploy/ceph-csi-rbd-provisioner -c csi-rbdplugin`). Timeouts mean the tailnet doesn't let the node through: check the node's tags and `tailscale ping` a storage Pi from it.
- Pod stuck in ContainerCreating with `libceph: Failed to parse secret: -524` in the node's `dmesg`: the key is `aes256k`; see [Rotate a client key](rotate-a-client-key.md) and [Keys and ciphers](../explanation/keys-and-ciphers.md).

!!! warning "Unverified"
    labk3s is the only cluster that has done this. The steps above are labk3s's configuration generalised. Two points are untested: running a second ceph-csi release against the same Ceph cluster, and nodes with a kernel other than the Pis'.

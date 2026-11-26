# Rotate a client key

Use this when Buckle's `resources` step fails with `client.<name> has a key of another type than <type>`, or when a client key has leaked.

**Before you start:** the moment you rotate, every holder of the old key loses access. For `client.k3s` that's ceph-csi on labk3s: new mounts and PVCs fail until its secret carries the new key; images that are already mapped stay mapped. Have the k8s-deployment checkout ready and SOPS working.

1. Rotate the key with the type the vars ask for (`key_type` in `ceph_clients`, [`vars/group-ceph.yaml`](https://github.com/SpechtLabs/homelab/blob/main/vars/group-ceph.yaml)). The `resources` step prints this exact command:

   ```sh
   sudo cephadm shell -- ceph auth rotate client.<name> --key_type <aes|aes256k>
   ```

2. Read the new key:

   ```sh
   sudo cephadm shell -- ceph auth get-key client.<name>
   ```

   `AQ...` is `aes`, `Ag...` is `aes256k`.
3. Update every client's copy. For ceph-csi on labk3s that's `userKey` in k8s-deployment [`apps/ceph-csi-rbd/cluster/labk3s/csi-rbd.secret.yaml`](https://github.com/SpechtLabs/k8s-deployment/blob/main/apps/ceph-csi-rbd/cluster/labk3s/csi-rbd.secret.yaml), SOPS-encrypted:

   ```sh
   cd ~/src/gh/SpechtLabs/k8s-deployment
   sops apps/ceph-csi-rbd/cluster/labk3s/csi-rbd.secret.yaml
   ```

   Push; Argo CD (`ceph-csi-rbd` on labk3s) syncs the Secret.
4. Let Buckle retry. The `resources` task's guard compares `/etc/ceph/buckle/resources.sh` with `resources.applied.sh`, which a failed run doesn't write, so the next Buckle run on `storagepi-ceph1` runs the script again.

!!! warning "Unverified"
    No key has been rotated on this cluster yet. Whether ceph-csi picks up a changed `csi-rbd-secret` without restarting its pods is untested.

## Check it worked

```sh
kubectl --context labk3s -n ceph-csi-rbd logs deploy/ceph-csi-rbd-provisioner -c csi-rbdplugin --tail=50
```

No auth errors; a test PVC on `ceph-rbd` binds. On `storagepi-ceph1`, `sudo cmp /etc/ceph/buckle/resources.sh /etc/ceph/buckle/resources.applied.sh` exits 0 once the step has succeeded.
